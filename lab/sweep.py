"""Compares settings of the policy on the same practice weeks.

    python -m lab.sweep --grid markup=1.4,1.5            # one row per setting, on the tuning seeds lab-1..10
    python -m lab.sweep --both --grid open_fee=0.8,0.9   # also on the holdout seeds hold-1..10
    python -m lab.sweep --starter --both                 # the starter of the kit, for comparison
    python -m lab.sweep ... --wait --weeks               # wait for the weeks to be played; show every week

Weeks that are not saved yet go to the queue of the worker (python -m lab.worker plays them, 7 at a time).
Without --wait the table shows what is saved so far. A change is kept only if it raises the mean margin on
the tuning seeds and on the holdout seeds, and no week falls under 93% on time."""
from __future__ import annotations

import argparse
import itertools
import json
import time

from lab.runs import KINDS, load, name_of, setting_of
from lab.worker import FAILED, QUEUE, RUNNING


def seeds(count: int, prefix: str) -> list[str]:
    return [f"{prefix}-{i}" for i in range(1, count + 1)]


def enqueue(level: int, seed: str, changed: dict | None, priority: int) -> bool:
    name = name_of(level, seed, changed)
    for folder in (QUEUE, RUNNING):
        folder.mkdir(parents=True, exist_ok=True)
        if any(folder.glob(f"*{name}.json")):
            return False
    FAILED.mkdir(parents=True, exist_ok=True)
    for old in FAILED.glob(f"*{name}.json"):
        old.unlink()
    (QUEUE / f"p{priority}-{time.time_ns()}-{name}.json").write_text(json.dumps({"level": level, "seed": seed, "params": changed}), encoding="utf-8")
    return True


HEAD = f"{'setting':<44} {'weeks':>6} {'mean':>9} {'worst':>9} {'min on-t':>8} {'mean ot':>7} {'<93%':>5} {'ranked':>7} {'won':>5} {'price':>6} {'fees':>5} {'refunds':>7}"


def row(label: str, results: list[dict], wanted: int) -> str:
    if not results:
        return f"{label:<44} {'0/' + str(wanted):>6}"
    margins = [r["score"]["marginCents"] / 100 for r in results]
    on_time = [r["score"]["onTimeShare"] for r in results]
    won = sum(r["score"]["wonOrders"] for r in results) / len(results)
    price = sum(r["stats"].get("won_price", 0) for r in results) / max(1, sum(r["stats"].get("won_list", 0) for r in results))
    fee = -sum(r["ledger"].get("driver_fee", 0) for r in results) / max(1, sum(r["stats"].get("won_typical", 0) for r in results))
    refunds = -sum(r["ledger"].get("late_refund", 0) + r["ledger"].get("undelivered_penalty", 0) for r in results) / 100 / len(results)
    under = sum(1 for share in on_time if share < 0.93)
    ranked = f"{sum(r['score']['ranked'] for r in results)}/{len(results)}"
    return (f"{label:<44} {str(len(results)) + '/' + str(wanted):>6} {sum(margins) / len(margins):>9,.0f} {min(margins):>9,.0f} {min(on_time):>8.1%} {sum(on_time) / len(on_time):>7.1%}"
            f" {under:>5} {ranked:>7} {won:>5.0f} {price:>6.2f} {fee:>5.2f} {refunds:>7,.0f}")


def week_lines(results: list[dict]) -> list[str]:
    lines = []
    for r in sorted(results, key=lambda r: int(r["seed"].split("-")[-1])):
        s, st = r["score"], r["stats"]
        days = " | ".join(f"{st.get(f'won_day{d}', 0) / max(1, st.get(f'quoted_day{d}', 0)):.0%}@{st.get(f'price_day{d}', 0) / max(1, st.get(f'list_day{d}', 0)):.2f}" for d in range(5))
        lines.append(f"    {r['seed']:<8} {s['marginCents'] / 100:>9,.0f}  won {s['wonOrders']:>4}  on time {s['onTimeShare']:6.1%}  {days}  {r['seconds']}s")
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--level", type=int, default=8)
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--prefix", default="lab", help="the seed family: lab is for tuning, hold is never tuned on")
    parser.add_argument("--both", action="store_true", help="the tuning seeds and the holdout seeds")
    parser.add_argument("--only", default="", help="exactly these seeds, comma-separated, instead of a family")
    parser.add_argument("--set", nargs="*", default=[], metavar="NAME=VALUE", help="policy settings for every row")
    parser.add_argument("--grid", nargs="*", default=[], metavar="NAME=V1,V2", help="one row for each combination; separate values that hold commas with /")
    parser.add_argument("--starter", action="store_true", help="also the starter of the kit")
    parser.add_argument("--wait", action="store_true", help="wait until every week is played")
    parser.add_argument("--weeks", action="store_true", help="show every week")
    parser.add_argument("--priority", type=int, default=5, help="1 is played first")
    parser.add_argument("--no-queue", action="store_true", help="only show what is saved")
    args = parser.parse_args()

    base = {k: KINDS[k](v) for k, v in (item.split("=", 1) for item in args.set)}
    names = [item.split("=", 1)[0] for item in args.grid]
    values = [[KINDS[n](v) for v in item.split("=", 1)[1].split("/" if "/" in item else ",")] for n, item in zip(names, args.grid)]
    columns: list[tuple[str, dict | None]] = [("starter", None)] if args.starter else []
    for combo in itertools.product(*values):
        changed = {**base, **dict(zip(names, combo))}
        columns.append((", ".join(f"{k}={v}" for k, v in json.loads(setting_of(changed)).items() if k != "version") or "defaults", changed))
    families = ["lab", "hold"] if args.both else [args.prefix]
    weeks = [(changed, seed) for _, changed in columns for family in families for seed in seeds(args.seeds, family)]
    if args.only:
        weeks = [(changed, seed) for _, changed in columns for seed in args.only.split(",")]

    if not args.no_queue:
        queued = sum(enqueue(args.level, seed, changed, args.priority) for changed, seed in weeks if load(args.level, seed, changed) is None)
        if queued:
            print(f"queued {queued} weeks")
    while args.wait and any(load(args.level, seed, changed) is None and not any(FAILED.glob(f"*{name_of(args.level, seed, changed)}.json")) for changed, seed in weeks):
        time.sleep(5)
    for family in families:
        print(f"\n{family}-1..{args.seeds}, level {args.level}\n{HEAD}")
        for label, changed in columns:
            results = [r for r in (load(args.level, seed, changed) for seed in seeds(args.seeds, family)) if r]
            print(row(label, results, args.seeds))
            if args.weeks:
                print("\n".join(week_lines(results)))


if __name__ == "__main__":
    main()
