"""Why is a car late? Sorts every late car of the saved weeks of one setting into one cause.

    python -m lab.late_causes cost=1.0 road_fee_blend=1.0 road_cost_blend=1.0

Causes, first match wins:
  dropped      a driver had booked it and gave it back (or did not show up); the next driver came too late
  failed visit the driver came and could not take or leave the car
  never booked no driver at all before the deadline
  booked late  no driver until the world's warning, 3 hours before the last pickup
  arrived late booked in good time, no drop, and still late: the driver's own day slipped (snow, an earlier gig)
"""
import sys
from collections import Counter, defaultdict

from lab.orders import rows
from lab.runs import DATA, KINDS, load


def cause(r: dict) -> str:
    if r["drops"]:
        return "dropped"
    if r["failed"]:
        return "failed visit"
    if r["book_wait"] is None:
        return "never booked"
    if r["warned"]:
        return "booked late"
    return "arrived late"


def main() -> None:
    changed = {k: KINDS[k](v) for k, v in (item.split("=", 1) for item in sys.argv[1:])}
    weeks = []
    for family in ("lab", "hold"):
        for n in range(1, 21):
            run = load(8, f"{family}-{n}", changed)
            if run and (DATA / "events" / f"{run['worldId']}.json.gz").exists():
                cars = [r for r in rows(run) if not r["cancelled"]]
                weeks.append((sum(r["on_time"] for r in cars) / len(cars), run["seed"], cars))
    weeks.sort()
    print(f"{len(weeks)} weeks of {changed or 'the defaults'}")
    print(f"{'week':9} {'on time':>7} {'cars':>5} {'late':>5}   dropped  failed  never  booked late  arrived late   | of the late: drive over 5 h, last pickup before 13:00, won Thu or Fri, thin end")
    total, late_all, cars_all = Counter(), [], []
    for share, seed, cars in weeks:
        late = [r for r in cars if not r["on_time"]]
        c = Counter(cause(r) for r in late)
        total.update(c)
        late_all += late
        cars_all += cars
        flags = (sum(r["drive"] > 300 for r in late), sum(r["last_pickup_hour"] < 13 for r in late), sum(r["weekday"] in ("Thu", "Fri") for r in late),
                 sum(min(r["near_pickup"], r["near_delivery"]) < 10 for r in late))
        print(f"{seed:9} {share:7.1%} {len(cars):5} {len(late):5}   {c['dropped']:7} {c['failed visit']:7} {c['never booked']:6} {c['booked late']:12} {c['arrived late']:13}   | {flags[0]:3} {flags[1]:3} {flags[2]:3} {flags[3]:3}")
    n = len(late_all)
    print(f"\nall weeks: {n} late cars of {len(cars_all)} ({n / len(cars_all):.1%}): " + ", ".join(f"{k} {v} ({v / n:.0%})" for k, v in total.most_common()))
    print("\nlate share and what a late car costs, by cause (refund + lost margin against the same kind of car on time is not counted here):")
    for name in ("dropped", "booked late", "arrived late", "failed visit", "never booked"):
        g = [r for r in late_all if cause(r) == name]
        if g:
            print(f"   {name:13} {len(g):5} cars, late by a median of {sorted((r['late_hours'] or 0) for r in g)[len(g) // 2]:5.1f} h, refunds {sum(r['refunds'] for r in g) / len(g) / 100:6.1f} a car, fee paid {sum((r['final_fee'] or 0) for r in g) / len(g):.2f} typical fees")
    print("\nshare of ALL cars with a drop:", f"{sum(r['drops'] > 0 for r in cars_all) / len(cars_all):.1%}", "; of cars with a drop, late:", f"{sum(1 for r in cars_all if r['drops'] and not r['on_time']) / max(1, sum(1 for r in cars_all if r['drops'])):.1%}")
    by = defaultdict(lambda: [0, 0])
    for r in cars_all:
        key = ("drive over 5 h" if r["drive"] > 300 else "drive under 5 h", "won Thu/Fri" if r["weekday"] in ("Thu", "Fri") else "won Mon-Wed")
        by[key][0] += 1
        by[key][1] += not r["on_time"]
    for key, (cars, late) in sorted(by.items()):
        g = [r for r in cars_all if ("drive over 5 h" if r["drive"] > 300 else "drive under 5 h", "won Thu/Fri" if r["weekday"] in ("Thu", "Fri") else "won Mon-Wed") == key]
        print(f"   {key[0]:16} {key[1]:12} {cars:6} cars, {late / cars:5.1%} late, margin {sum(r['margin'] for r in g) / len(g) / 100:6.1f} a car")


if __name__ == "__main__":
    main()
