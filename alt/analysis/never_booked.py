"""The late cars that never had a driver, in a design's saved weeks: their gigs (pairs or single), when each was
posted and how it ended, the last pickup, and the order's events. To see why a held or paired car found nobody.

    python3 -X utf8 -m alt.analysis.never_booked design=pairhold_h4 lab_step=12 [--show 8]"""
from __future__ import annotations

import sys
from collections import Counter

from lab.orders import rows, snapshot_of
from lab.runs import EVENTS, KINDS, load, read_gz

WEEK = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def at(minute: int) -> str:
    return f"{WEEK[minute // 1440 % 7]} {minute % 1440 // 60:02}:{minute % 60:02}"


def main() -> None:
    args = sys.argv[1:]
    show = int(args[args.index("--show") + 1]) if "--show" in args else 8
    words = [a for a in args if "=" in a]
    changed = {k: KINDS[k](v) for k, v in (w.split("=", 1) for w in words)}
    kinds, shown = Counter(), 0
    for family in ("lab", "hold"):
        for n in range(1, 21):
            run = load(8, f"{family}-{n}", changed)
            if not run:
                continue
            cars = [r for r in rows(run) if not r["cancelled"] and not r["on_time"] and r["book_wait"] is None]
            if not cars:
                continue
            snap, events = snapshot_of(run["worldId"]), read_gz(EVENTS / f"{run['worldId']}.json.gz")
            won = {e["order"]["id"]: e for e in events if e["kind"] == "order_won"}
            for r in cars:
                gigs = [g for g in snap["gigs"] if any(s["orderId"] == r["order"] for s in g["stops"])]
                pair = any(len({s["orderId"] for s in g["stops"]}) > 1 for g in gigs)
                kinds["was in a pair" if pair else "single only"] += 1
                kinds[f"gigs posted {min(len(gigs), 4)}"] += 1
                if shown < show:
                    shown += 1
                    o = won[r["order"]]["order"]
                    print(f"{run['seed']} {r['order']} won {at(won[r['order']]['at'])} last pickup {at(o['lastPickupAt'])} {r['pickup']}>{r['delivery']} drive {r['drive']} min")
                    for g in gigs:
                        print(f"   gig {g['id']} posted {at(g['postedAt'])} status {g['status']} orders {len({s['orderId'] for s in g['stops']})} fees {[round(s['feeCents'] / r['typical'], 2) for s in g['schedule']][:8]}")
    print(dict(kinds))


if __name__ == "__main__":
    main()
