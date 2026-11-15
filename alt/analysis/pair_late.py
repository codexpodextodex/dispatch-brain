"""Are cars that rode in a pair late more often than cars that went alone? Per design's saved weeks.

    python3 -X utf8 -m alt.analysis.pair_late design=pairhold_h4 lab_step=12"""
from __future__ import annotations

import sys

from lab.orders import rows, snapshot_of
from lab.runs import KINDS, load


def main() -> None:
    changed = {k: KINDS[k](v) for k, v in (w.split("=", 1) for w in sys.argv[1:])}
    tally = {"pair": [0, 0, 0, 0], "single": [0, 0, 0, 0]}  # cars, late, margin cents, weeks
    weeks = 0
    for family in ("lab", "hold"):
        for n in range(1, 21):
            run = load(8, f"{family}-{n}", changed)
            if not run:
                continue
            weeks += 1
            snap = snapshot_of(run["worldId"])
            paired = {s["orderId"] for g in snap["gigs"] if g["status"] == "done" and len({s["orderId"] for s in g["stops"]}) > 1 for s in g["stops"]}
            for r in rows(run):
                if r["cancelled"] or r["legs"] != 1:
                    continue
                t = tally["pair" if r["order"] in paired else "single"]
                t[0] += 1
                t[1] += not r["on_time"]
                t[2] += r["revenue"] - r["refunds"]
    for k, (cars, late, net, _) in tally.items():
        print(f"{k:7} cars a week {cars / weeks:6.1f}  late {late / max(1, cars):.1%}  revenue after refunds a car {net / max(1, cars) / 100:6.1f}")


if __name__ == "__main__":
    main()
