"""Which cars make money and which lose it: the won orders of saved weeks, grouped by one or two columns.

    python -m lab.patterns --by weekday                       # the default policy on the tuning seeds
    python -m lab.patterns --both --set notes=ours --by note  # a setting, on both seed families
    python -m lab.patterns --by pickup option --min 30        # two columns; only groups of 30 orders or more

Columns to group by: weekday hour option pickup delivery dealer note drive find last_pickup_weekday
last_pickup_hour drops failed warned km seed electric near_pickup near_delivery (drivers living within 30 km)."""
from __future__ import annotations

import argparse
from collections import defaultdict

from lab.orders import rows
from lab.runs import EVENTS, KINDS, load
from lab.sweep import seeds

BANDS = {
    "drive": [(60, "under 1 h"), (120, "1-2 h"), (240, "2-4 h"), (360, "4-6 h"), (1e9, "over 6 h")],
    "km": [(50, "under 50 km"), (150, "50-150 km"), (300, "150-300 km"), (1e9, "over 300 km")],
    "near_pickup": [(10, "under 10 drivers"), (30, "10-29"), (100, "30-99"), (300, "100-299"), (1e9, "300 or more")],
    "near_delivery": [(10, "under 10 drivers"), (30, "10-29"), (100, "30-99"), (300, "100-299"), (1e9, "300 or more")],
    "find": [(18, "under 18 h"), (24, "18-24 h"), (30, "24-30 h"), (54, "30-54 h"), (1e9, "over 54 h")],
}


def key_of(row: dict, column: str) -> str:
    if column in BANDS:
        value = row["find_hours" if column == "find" else column]
        return next(f"{i} {label}" for i, (limit, label) in enumerate(BANDS[column]) if value < limit)
    if column == "failed":
        return ",".join(sorted(set(row["failed"]))) or "-"
    if column in ("hour", "last_pickup_hour"):
        return f"{row[column]:02d}"
    return str(row[column])


def table(all_rows: list[dict], columns: list[str], smallest: int) -> None:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in all_rows:
        if not row["cancelled"]:
            groups[tuple(key_of(row, c) for c in columns)].append(row)
    weeks = len({row["seed"] for row in all_rows})
    print(f"{' / '.join(columns):<34} {'orders':>6} {'on time':>7} {'margin':>8} {'per week':>8} {'price':>6} {'fee':>5} {'refund':>7} {'warned':>6} {'in 1 h':>6} {'drops':>5} {'failed':>6}")
    print(f"{'':<34} {'':>6} {'':>7} {'/order':>8} {'':>8} {'x list':>6} {'x typ':>5} {'/order':>7}")
    for key, group in sorted(groups.items()):
        if len(group) < smallest:
            continue
        n = len(group)
        booked = [r for r in group if r["book_wait"] is not None]
        print(f"{' / '.join(key):<34} {n:>6} {sum(r['on_time'] for r in group) / n:>7.1%} {sum(r['margin'] for r in group) / n / 100:>8.1f} {sum(r['margin'] for r in group) / weeks / 100:>8,.0f}"
              f" {sum(r['price'] for r in group) / sum(r['list'] for r in group):>6.2f} {sum(r['fees'] for r in group) / sum(r['typical'] for r in group):>5.2f}"
              f" {sum(r['refunds'] for r in group) / n / 100:>7.1f} {sum(r['warned'] for r in group) / n:>6.0%} {sum(1 for r in booked if r['book_wait'] <= 1) / n:>6.0%}"
              f" {sum(r['drops'] for r in group) / n:>5.2f} {sum(1 for r in group if r['failed']) / n:>6.1%}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--level", type=int, default=8)
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--both", action="store_true")
    parser.add_argument("--prefix", default="lab")
    parser.add_argument("--set", nargs="*", default=[], metavar="NAME=VALUE")
    parser.add_argument("--by", nargs="+", default=["weekday"])
    parser.add_argument("--min", type=int, default=1)
    args = parser.parse_args()
    changed = {k: KINDS[k](v) for k, v in (item.split("=", 1) for item in args.set)}
    all_rows: list[dict] = []
    for family in (["lab", "hold"] if args.both else [args.prefix]):
        for seed in seeds(args.seeds, family):
            run = load(args.level, seed, changed)
            if run and (EVENTS / f"{run['worldId']}.json.gz").exists():
                all_rows += rows(run)
    print(f"{len({r['seed'] for r in all_rows})} weeks, {len(all_rows)} orders won\n")
    table(all_rows, args.by, args.min)


if __name__ == "__main__":
    main()
