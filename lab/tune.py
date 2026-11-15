"""Improves the policy's settings by itself, one change at a time, while nobody watches.

    python -m lab.tune            # runs until the file data/queue/STOP_TUNE appears

It goes round the settings in SPACE. For each it tries a step up and a step down (or each other choice), on
the ten tuning weeks. The best change of a batch is then played on the ten holdout weeks, and is kept only if

    - it raises the mean margin on the tuning weeks by at least MIN_GAIN, and on the holdout weeks at all;
    - every week of either family stays ranked with room to spare: at least 91% on time, where the rule asks 90%.

Every candidate, kept or not, goes into data/tune_log.md with its numbers. The weeks are played by the worker
(python -m lab.worker); a week that is already saved is not played again. The settings kept so far are in
data/tune_state.json, as changes against the defaults in dispatch/policy.py."""
from __future__ import annotations

import json
import time
from dataclasses import asdict

from dispatch.policy import Params
from lab.runs import DATA, load, name_of
from lab.sweep import enqueue, seeds
from lab.worker import FAILED, QUEUE

LEVEL, WEEKS = 8, 20  # twenty weeks a family: with ten, a difference under about 400 euros is noise
MIN_GAIN = 150  # euros a week on the tuning weeks; and the gain must be at least 1.5 times its own standard error
MIN_ON_TIME = 0.91  # a week under 90% is not ranked; we keep a point of room
BATCH = 5  # candidates played side by side: 100 weeks, about fifteen minutes
STATE, LOG = DATA / "tune_state.json", DATA / "tune_log.md"

# Each setting: steps to add to its current value, or the other choices to try.
SPACE: dict[str, dict] = {
    "cost_thin": {"steps": [-0.1, 0.1, 0.2]},
    "cap_thin": {"choices": [0, 1]},
    "fee_floor": {"choices": [0, 1600]},
    "trust": {"choices": [0, 1]},
    "same_day_premium": {"choices": [0.0, 0.05, 0.1]},
    "trade_in": {"choices": [0, 1]},
    "easy_find_hours": {"choices": [0.0, 6.0, 9.0]},
    "private_delivery": {"choices": [0, 1]},
    "private_pickup": {"choices": [0, 1]},
    "premium": {"choices": [0, 1]},
    "pairs": {"choices": [0, 1]},
    "option_rate": {"choices": [0.0, 0.01]},
    "day_cap": {"steps": [-0.01, 0.015, 0.03]},
    "cost": {"steps": [-0.1, -0.05, 0.05]},
    "cost_drive": {"steps": [-0.03, 0.04]},
    "cost_private_pickup": {"steps": [0.3, 0.6]},
    "cost_trade_in": {"steps": [0.2]},
    "cost_private": {"steps": [0.2]},
    "cost_premium": {"steps": [0.3]},
    "spread": {"steps": [-0.03, 0.03]},
    "min_margin": {"choices": [0.02, 0.05, 0.1]},
    "open_fee": {"steps": [-0.04, 0.04]},
    "top_fee": {"steps": [-0.1, 0.1]},
    "late_fee": {"steps": [-0.3, 0.3]},
    "hold": {"choices": [0.0, 0.3, 0.6]},
    "lead_hours": {"steps": [-2, 3]},
    "early_hour": {"steps": [-2, 2]},
    "min_find_hours": {"steps": [-4, -2, 3]},
    "cost_short": {"steps": [0.05]},
    "min_last_hour": {"choices": [0, 12, 13]},
    "cap_power": {"choices": [2.0, 4.0, 8.0]},
    "open_easy": {"choices": [0.0, 0.8]},
    "open_hard": {"choices": [0.0, 0.9]},
    "night_hold": {"choices": [0, 1]},
    "weekend_hold": {"choices": [0, 1]},
    "relane": {"choices": [0, 1]},
    "lane_rate": {"steps": [-0.015, 0.02]},
    "dealer_rate": {"steps": [-0.012, 0.02]},
    "market_rate": {"steps": [-0.012, 0.02]},
    "start_level": {"steps": [-0.07, 0.1]},
    "teaser_fee": {"choices": [0.0, 0.75]},
    "schedule": {"choices": ["ramp", "plan"]},
    "urgent_top": {"steps": [-0.4, 0.4]},
    "pair_fee": {"steps": [-0.1, 0.1]},
}
SPACE.update({"snow_cost": {"choices": [0.0, 0.6]}, "evening_hour": {"steps": [-2, 2]}, "urgent_step": {"steps": [-0.1, 0.1]}})
# The order of the round. Since the fees are free of the typical fee's noise (EXPERIMENTS.md 25), the fee
# schedule is worth tuning again, so it goes first; then what guards the on-time share; then the rest.
FIRST = ["open_fee", "top_fee", "hold", "late_fee", "lead_hours", "early_hour", "evening_hour", "urgent_top", "teaser_fee", "open_easy", "open_hard",
         "night_hold", "weekend_hold", "relane", "fee_floor", "snow_cost", "min_margin", "spread", "day_cap", "cap_power", "cost_drive", "min_find_hours",
         "easy_find_hours", "trust", "pairs", "cost"]
DEFAULTS = asdict(Params())


def value(best: dict, name: str):
    return best.get(name, DEFAULTS[name])


NEEDS = {"cost_private": ("private_delivery", 1), "cost_premium": ("premium", 1), "pair_fee": ("pairs", 1), "cost_private_pickup": ("private_pickup", 1), "cost_trade_in": ("trade_in", 1)}  # a setting that does nothing unless another is on


def candidates(best: dict, name: str) -> list[dict]:
    """The settings one step away from `best` in one setting."""
    current, space = value(best, name), SPACE[name]
    if name in NEEDS and value(best, NEEDS[name][0]) != NEEDS[name][1]:
        return []
    if name == "cost_short" and value(best, "min_find_hours") >= 14:
        return []
    if "choices" in space:
        new = [choice for choice in space["choices"] if choice != current]
    else:
        new = [round(current + step, 4) for step in space["steps"] if current + step > 0]
    return [{**best, name: v} for v in new]


def results(changed: dict, family: str) -> list[dict] | None:
    """The saved weeks of a setting on one seed family; None while a week is missing."""
    runs = [load(LEVEL, seed, changed) for seed in seeds(WEEKS, family)]
    return None if any(r is None for r in runs) else runs


def play(settings: list[dict], family: str) -> list[list[dict] | None]:
    """Queues the weeks that are missing, waits for them, and returns the weeks of each setting."""
    for changed in settings:
        for seed in seeds(WEEKS, family):
            if load(LEVEL, seed, changed) is None:
                enqueue(LEVEL, seed, changed, priority=0)
    while True:
        waiting = [(changed, seed) for changed in settings for seed in seeds(WEEKS, family) if load(LEVEL, seed, changed) is None]
        if not waiting:
            return [results(changed, family) for changed in settings]
        for changed, seed in waiting:  # a week that failed (a network break) goes back in the queue
            failed = list(FAILED.glob(f"*{name_of(LEVEL, seed, changed)}.json"))
            if failed:
                enqueue(LEVEL, seed, changed, priority=0)
        if (QUEUE / "STOP_TUNE").exists():
            raise SystemExit("stopped")
        time.sleep(5)


def summary(runs: list[dict]) -> dict:
    margins = [r["score"]["marginCents"] / 100 for r in runs]
    return {"mean": sum(margins) / len(margins), "worst": min(margins), "on_time": min(r["score"]["onTimeShare"] for r in runs),
            "won": sum(r["score"]["wonOrders"] for r in runs) / len(runs), "margins": margins}


def label(changed: dict, against: dict) -> str:
    return ", ".join(f"{k}={v}" for k, v in changed.items() if against.get(k, DEFAULTS[k]) != v) or "no change"


def note(line: str) -> None:
    with open(LOG, "a", encoding="utf-8") as file:
        file.write(line + "\n")
    print(line, flush=True)


def main() -> None:
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {"best": {}, "tried": []}
    best = state["best"]
    base = {family: summary(play([best], family)[0]) for family in ("lab", "hold")}
    note(f"\n## Tuning from: {label(best, {}) if best else 'the defaults'} ({time.strftime('%a %H:%M')})\n")
    note(f"Start: tuning weeks {base['lab']['mean']:,.0f} (lowest on time {base['lab']['on_time']:.1%}), holdout weeks {base['hold']['mean']:,.0f} (lowest on time {base['hold']['on_time']:.1%})\n")
    note("| Change | Tuning mean | Gain | Weeks better | Lowest on time | Orders | Holdout mean | Gain | Lowest on time | Verdict |")
    note("|---|---|---|---|---|---|---|---|---|---|")
    names = FIRST + [name for name in SPACE if name not in FIRST]
    position = 0
    while True:
        batch: list[dict] = []
        ideas = DATA / "tune_ideas.json"  # changes of several settings at once that we want tried first, written by hand
        if ideas.exists():
            batch = [{**best, **idea} for idea in json.loads(ideas.read_text(encoding="utf-8"))]
            ideas.unlink()
        while len(batch) < BATCH:  # the next settings in the round, skipping what was tried from this very state
            for candidate in candidates(best, names[position % len(names)]):
                key = json.dumps([sorted(best.items()), sorted(candidate.items())], sort_keys=True)
                if key not in state["tried"]:
                    batch.append(candidate)
                    state["tried"].append(key)
            position += 1
            if position > 4 * len(names) and not batch:
                note("\nEvery change one step away has been tried: nothing left to gain here.")
                return
        played = play(batch, "lab")
        scored = []
        for candidate, runs in zip(batch, played):
            s = summary(runs)
            gains = [a - b for a, b in zip(s["margins"], base["lab"]["margins"])]
            mean_gain = sum(gains) / len(gains)
            error = (sum((g - mean_gain) ** 2 for g in gains) / (len(gains) - 1) / len(gains)) ** 0.5  # of the mean gain, week by week
            better = sum(1 for g in gains if g > 0)
            scored.append((mean_gain if mean_gain >= 1.5 * error else min(mean_gain, MIN_GAIN - 1), candidate, s, better, mean_gain, error))
        scored.sort(key=lambda item: -item[0])
        adopted, before = False, dict(best)
        for gain, candidate, s, better, mean_gain, error in scored:
            verdict, hold_text = "no gain", "| | |"
            if gain >= MIN_GAIN and s["on_time"] < MIN_ON_TIME:
                verdict = "a tuning week too close to 90% on time"
            elif gain >= MIN_GAIN and not adopted:  # the best of the batch: confirm it on the weeks we never tune on
                h = summary(play([candidate], "hold")[0])
                hold_gain = h["mean"] - base["hold"]["mean"]
                hold_text = f"{h['mean']:,.0f} | {hold_gain:+,.0f} | {h['on_time']:.1%} |"
                if hold_gain > 0 and h["on_time"] >= MIN_ON_TIME:
                    verdict, adopted = "**kept**", True
                    best, base = candidate, {"lab": s, "hold": h}
                    state["best"] = best
                else:
                    verdict = "not confirmed on the holdout weeks"
            elif gain >= MIN_GAIN:
                verdict = "gain, but another change of this batch was kept first: it comes round again"
            note(f"| {label(candidate, before)} | {s['mean']:,.0f} | {mean_gain:+,.0f} ± {error:,.0f} | {better}/{WEEKS} | {s['on_time']:.1%} | {s['won']:.0f} | {hold_text} {verdict} |")
        STATE.write_text(json.dumps(state), encoding="utf-8")
        if adopted:
            note(f"\nNow: {label(best, {})}: tuning weeks {base['lab']['mean']:,.0f}, holdout weeks {base['hold']['mean']:,.0f}\n")
            note("| Change | Tuning mean | Gain | Weeks better | Lowest on time | Orders | Holdout mean | Gain | Lowest on time | Verdict |")
            note("|---|---|---|---|---|---|---|---|---|---|")


if __name__ == "__main__":
    main()
