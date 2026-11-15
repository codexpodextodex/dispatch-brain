"""Climbs from the current version by itself, one small change at a time, in exact mode.

    python -m lab.climb            # runs until the file data/queue/STOP_CLIMB appears, or the list is done

For each candidate (one setting changed against the best so far) it plays the 30-week panel (the 16 hardest weeks
and 14 ordinary ones). A candidate that gains nothing there, or takes a week under 90% on time, stops there. The
others are played on the other 30 weeks too, and a candidate is kept only if on all 60 weeks

    - its mean gain is at least MIN_GAIN euros a week and at least two standard errors,
    - at least two of the three seed families gain,
    - no week is under 90% on time, and the eight hardest weeks are on time no less than before, less 0.3 points.

A kept change becomes the base for the candidates after it. Everything goes into data/climb_log.md, kept or not;
the changes kept so far are in data/climb_state.json, as changes against the defaults of dispatch/policy.py.
The weeks are played by the worker; a week that is saved is not played again. What it keeps is a proposal: the
stack is confirmed on a seed family used for nothing else before it becomes a version."""
from __future__ import annotations

import json
import statistics as st
import time
from dataclasses import asdict

from dispatch.policy import Params
from lab.runs import DATA, load, name_of
from lab.sweep import enqueue
from lab.worker import FAILED, QUEUE

LEVEL = 8
HARD = "fresh-9,fresh-12,hold-10,hold-17,hold-2,hold-9,fresh-20,lab-11".split(",")
PANEL = HARD + ("lab-19,fresh-2,lab-18,lab-10,hold-14,hold-13,hold-12,fresh-5,lab-1,lab-3,lab-5,lab-7,hold-1,hold-3,hold-5,hold-7,"
                "fresh-1,fresh-3,fresh-7,fresh-11,lab-13,hold-15").split(",")
ALL = [f"{family}-{i}" for family in ("lab", "hold", "fresh") for i in range(1, 21)]
REST = [seed for seed in ALL if seed not in PANEL]
MIN_GAIN, BATCH = 60, 3
STATE, LOG = DATA / "climb_state.json", DATA / "climb_log.md"
DEFAULTS = asdict(Params())

# One change each, in the order of what today's results make most likely to pay.
CANDIDATES: list[dict] = [
    {"cap_monday": 1.5}, {"cap_monday": 2.0}, {"guard": 0.1}, {"steady_private": 1}, {"guard_once": 1, "guard": 0.06}, {"home_open": 0.8}, {"home_open": 0.7}, {"cap_monday": 1.25}, {"home_hours": 4.0}, {"home_drivers": 50}, {"home_drivers": 20}, {"home_min_fee": 1500},
    {"guard": 0.06}, {"evening_hour": 19.0}, {"pair_fee": 0.75}, {"menu": 2}, {"easy_drive_hours": 3.0},
    {"cost_private_pickup": 0.1}, {"evening_hour": 20.0}, {"pair_fee": 0.7}, {"easy_find_hours": 3.0}, {"min_find_hours": 12.0},
    {"start_level": 1.0}, {"cost": 0.97}, {"cost": 1.03}, {"top_fee": 1.15}, {"top_fee": 1.25}, {"late_fee": 1.6}, {"late_fee": 2.0},
    {"hold": 0.2}, {"hold": 0.4}, {"lead_hours": 5.0}, {"lead_hours": 7.0}, {"cost_drive": 0.06}, {"cost_drive": 0.1},
    {"day_cap": 0.115}, {"day_cap": 0.105}, {"spread": 0.13}, {"spread": 0.15}, {"min_margin": 0.03}, {"min_margin": 0.08},
    {"late_open": 0.9}, {"late_open": 1.1}, {"late_top": 1.2}, {"late_top": 1.4}, {"pair_hop": 75}, {"pair_back": 105}, {"pair_split_hours": 8.0},
    {"pair_split_hours": 12.0}, {"private_find_hours": 2.0}, {"private_find_hours": 5.0}, {"private_drive_hours": 1.5}, {"private_drive_hours": 2.5},
    {"guard_cost": 0.35}, {"guard_cost": 0.7}, {"guard_lead": 4.0}, {"guard_lead": 8.0}, {"urgent_top": 2.2}, {"urgent_top": 2.8},
    {"urgent_step": 0.15}, {"urgent_step": 0.3}, {"weekend_hold": 1}, {"same_day_premium": 0.03}, {"premium": 1, "cost_premium": 0.3},
    {"easy_find_hours": 5.0}, {"easy_drivers": 150}, {"cost_private_pickup": 0.3}, {"cost_private": 0.1}, {"lane_rate": 0.03}, {"lane_rate": 0.05},
    {"dealer_rate": 0.02}, {"dealer_rate": 0.04}, {"market_rate": 0.02}, {"market_rate": 0.04}, {"easy_cost": 0.05}, {"cap_power": 3.0}, {"cap_power": 5.0},
    {"open_fee": 0.83}, {"open_fee": 0.87}, {"min_find_hours": 16.0}, {"late_lead": 4.0}, {"schedule": "plan"},
]


def label(changed: dict, against: dict) -> str:
    return " ".join(f"{k}={v}" for k, v in sorted(changed.items()) if against.get(k, DEFAULTS[k]) != v) or "no change"


def play(settings: list[dict], seeds: list[str]) -> None:
    """Queues the weeks that are missing and waits for them."""
    for changed in settings:
        for seed in seeds:
            if load(LEVEL, seed, changed) is None:
                enqueue(LEVEL, seed, changed, priority=-1)
    while True:
        waiting = [(changed, seed) for changed in settings for seed in seeds if load(LEVEL, seed, changed) is None]
        if not waiting:
            return
        for changed, seed in waiting:  # a week that failed (a network break) goes back in the queue
            if list(FAILED.glob(f"*{name_of(LEVEL, seed, changed)}.json")):
                enqueue(LEVEL, seed, changed, priority=-1)
        if (QUEUE / "STOP_CLIMB").exists():
            raise SystemExit("stopped")
        time.sleep(10)


def compare(changed: dict, base: dict, seeds: list[str]) -> dict:
    a, b = {s: load(LEVEL, s, base) for s in seeds}, {s: load(LEVEL, s, changed) for s in seeds}
    gains = {s: (b[s]["score"]["marginCents"] - a[s]["score"]["marginCents"]) / 100 for s in seeds}
    shares = {s: b[s]["score"]["onTimeShare"] for s in seeds}
    families = {f: st.mean([g for s, g in gains.items() if s.startswith(f)] or [0.0]) for f in ("lab", "hold", "fresh")}
    return {"gain": st.mean(gains.values()), "err": st.stdev(gains.values()) / len(gains) ** 0.5, "families": families, "better": sum(g > 0 for g in gains.values()), "weeks": len(seeds),
            "cars": st.mean(b[s]["score"]["wonOrders"] - a[s]["score"]["wonOrders"] for s in seeds), "lowest": min(shares.values()), "under": sum(v < 0.9 for v in shares.values()),
            "hard": st.mean(shares[s] for s in HARD if s in shares), "hard_base": st.mean(a[s]["score"]["onTimeShare"] for s in HARD if s in a)}


def line(name: str, c: dict, verdict: str) -> str:
    f = c["families"]
    return (f"| {name} | {c['weeks']} | {c['gain']:+.0f} ± {c['err']:.0f} | {f['lab']:+.0f} / {f['hold']:+.0f} / {f['fresh']:+.0f} | {c['better']}/{c['weeks']} | {c['cars']:+.1f} | "
            f"{c['hard']:.1%} ({c['hard_base']:.1%}) | {c['lowest']:.1%} | {c['under']} | {verdict} |")


def main() -> None:
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {"best": {}, "done": []}
    if not LOG.exists():
        LOG.write_text("# The climb from the current version, one change at a time (exact mode; lab/climb.py)\n\n"
                       "| Change against the best so far | Weeks | Gain | lab / hold / fresh | Better | Cars | Eight hardest (before) | Lowest week | Under 90% | Verdict |\n|---|---|---|---|---|---|---|---|---|---|\n",
                       encoding="utf-8")
    play([state["best"]], ALL)  # the base itself, if it is new
    todo = [c for c in CANDIDATES if json.dumps(c, sort_keys=True) not in state["done"]]
    while todo and not (QUEUE / "STOP_CLIMB").exists():
        batch, todo = todo[:BATCH], todo[BATCH:]
        best = state["best"]
        trials = [(c, {**best, **c}) for c in batch if any(best.get(k, DEFAULTS[k]) != v for k, v in c.items())]
        play([changed for _, changed in trials], PANEL)
        second = []
        for c, changed in trials:
            first = compare(changed, best, PANEL)
            if first["gain"] >= MIN_GAIN / 2 and first["under"] == 0:
                second.append((c, changed))
            else:
                with open(LOG, "a", encoding="utf-8") as log:
                    log.write(line(label(changed, best), first, "stopped at the panel") + "\n")
        play([changed for _, changed in second], REST)
        kept = []
        for c, changed in second:
            result = compare(changed, best, ALL)
            keep = (result["gain"] >= MIN_GAIN and result["gain"] >= 2 * result["err"] and sum(v > 0 for v in result["families"].values()) >= 2
                    and result["under"] == 0 and result["hard"] >= result["hard_base"] - 0.003)
            if keep:
                kept.append((result["gain"], c, changed, result))
            else:
                with open(LOG, "a", encoding="utf-8") as log:
                    log.write(line(label(changed, best), result, "no") + "\n")
        kept.sort(key=lambda k: -k[0])
        for rank, (_, c, changed, result) in enumerate(kept):  # the best of a batch becomes the base; the others are tried again from it
            with open(LOG, "a", encoding="utf-8") as log:
                log.write(line(label(changed, best), result, "**kept**" if rank == 0 else "good; tried again from the new base") + "\n")
            if rank == 0:
                state["best"] = changed
            else:
                todo.insert(0, c)
        state["done"] += [json.dumps(c, sort_keys=True) for c in batch if c not in todo]
        STATE.write_text(json.dumps(state, indent=1), encoding="utf-8")
    with open(LOG, "a", encoding="utf-8") as log:
        log.write(f"\nbest so far against the defaults: `{label(state['best'], {})}`\n")


if __name__ == "__main__":
    main()
