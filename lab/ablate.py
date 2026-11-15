"""What each part of the current version is worth: the same weeks with that one part switched off.

    python -m lab.ablate              # the table, from the weeks that are saved
    python -m lab.ablate --queue      # queue the weeks that are missing (60 weeks for each row), then show the table

Every row is the current version with one part left out, on lab, hold and fresh 1..20 in exact mode. "Costs" is
what leaving it out loses a week (mean, with its standard error); the last columns say what it does to the hard
weeks. This is the table the jury asks for: leave this out and the system does this much worse."""
from __future__ import annotations

import statistics as st
import sys

from lab.runs import load
from lab.sweep import enqueue

LEVEL = 8
SEEDS = [f"{family}-{i}" for family in ("lab", "hold", "fresh") for i in range(1, 21)]
PARTS: list[tuple[str, dict]] = [
    ("the price book does not learn from the dealers' answers", {"market_rate": 0.0, "dealer_rate": 0.0, "lane_rate": 0.0}),
    ("takes any car with 4 hours to find a driver (not 14)", {"min_find_hours": 4.0}),
    ("no cap on the cars due on one day", {"day_cap": 0.0}),
    ("no brake on risky cars when warnings rise", {"guard": 0.0}),
    ("no private addresses", {"private_delivery": 0, "private_pickup": 0}),
    ("no round trips", {"pairs": 0}),
    ("round trips, but no waiting for a partner (version 8)", {"pair_hold": 0.0}),
    ("the day cap also for cars due after Friday (version 9)", {"cap_week_only": 0}),
    ("no trade-ins and no premium cars (version 10)", {"trade_hour": 0, "premium_after": 0}),
    ("fees keep rising at night, when nobody books", {"night_hold": 0}),
    ("no lower opening fee for home-bound cars, no ramp at short notice", {"home_open": 0.0, "short_ramp": 0}),
    ("no pickup window, so a late driver says nothing", {"windows": 0}),
    ("the two leaks open again (a returned pair's car; late counted at delivery)", {"pair_safe": 0, "late_by_pickup": 0}),
]


def main() -> None:
    if "--queue" in sys.argv:
        queued = sum(enqueue(LEVEL, seed, changed, priority=-1) for _, changed in PARTS for seed in SEEDS if load(LEVEL, seed, changed) is None)
        print(f"queued {queued} weeks")
    base = {seed: load(LEVEL, seed, {}) for seed in SEEDS}
    full = st.mean(run["score"]["marginCents"] for run in base.values() if run) / 100
    print(f"the current version: {full:,.0f} a week, lowest week {min(run['score']['onTimeShare'] for run in base.values() if run):.1%} on time\n")
    print(f"{'left out':78} {'weeks':>5} {'costs a week':>14} {'cars':>6} {'on time':>8} {'lowest':>7} {'under 90%':>9}")
    for name, changed in PARTS:
        runs = {seed: load(LEVEL, seed, changed) for seed in SEEDS}
        both = [seed for seed in SEEDS if runs[seed] and base[seed]]
        if len(both) < 2:
            print(f"{name:78} {len(both):5}")
            continue
        loss = [(base[s]["score"]["marginCents"] - runs[s]["score"]["marginCents"]) / 100 for s in both]
        share = [runs[s]["score"]["onTimeShare"] for s in both]
        cars = st.mean(runs[s]["score"]["wonOrders"] - base[s]["score"]["wonOrders"] for s in both)
        print(f"{name:78} {len(both):5} {st.mean(loss):+8,.0f} ± {st.stdev(loss) / len(loss) ** 0.5:3.0f} {cars:+6.1f} {st.mean(share):8.1%} {min(share):7.1%} {sum(v < 0.9 for v in share):9}")


if __name__ == "__main__":
    main()
