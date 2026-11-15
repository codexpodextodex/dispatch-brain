"""One week under two settings: which cars are late under one and not the other, and what happened to them.

    python week_diff.py fresh-12 early_hour=13 night_hold=1"""
import sys
from collections import Counter

from lab.late_causes import cause
from lab.orders import rows
from lab.runs import KINDS, load

seed = sys.argv[1]
setting = {k: KINDS[k](v) for k, v in (a.split("=") for a in sys.argv[2:])}
a, b = load(8, seed, {}), load(8, seed, setting)
ra, rb = rows(a), rows(b)
for name, run, rr in (("version 6", a, ra), ("changed", b, rb)):
    late = [r for r in rr if not r["on_time"] and not r["cancelled"]]
    print(f"{name:10} margin {run['score']['marginCents'] / 100:8,.0f} cars {len(rr)} on time {run['score']['onTimeShare']:.1%} late {len(late)}  fees {sum(r['fees'] for r in rr) / 100:,.0f} refunds {sum(r['refunds'] for r in rr) / 100:,.0f}")
    print("   late by cause:", dict(Counter(cause(r) for r in late)))
    print("   late by last-pickup day:", dict(sorted(Counter(r["last_pickup_weekday"] for r in late).items())))
    print("   late by last-pickup hour:", dict(sorted(Counter(r["last_pickup_hour"] for r in late).items())))
    print("   late by option:", dict(Counter(r["option"] for r in late)))


def key(r):  # the same request in both runs
    return (r["dealer"], r["pickup"], r["delivery"], r["weekday"], r["hour"], r["list"])


ka, kb = {key(r): r for r in ra}, {key(r): r for r in rb}
print("\ncars won in both:", len(set(ka) & set(kb)), " only version 6:", len(set(ka) - set(kb)), " only changed:", len(set(kb) - set(ka)))
print("\nlate under the change, on time under version 6 (same car):")
print(f"  {'won':9} {'last pickup':12} {'lane':34} {'drive h':>7} {'near':>4} {'cause':13} {'v6: booked after h / fee':>25} {'changed: booked after h / fee':>30} {'left h':>7}")
for k in sorted(set(ka) & set(kb), key=lambda k: kb[k]["last_pickup_weekday"]):
    x, y = ka[k], kb[k]
    if x["on_time"] and not y["on_time"] and not y["cancelled"]:
        def book(r):
            return f"{r['book_wait']:.0f} / {r['final_fee']:.2f}" if r["book_wait"] is not None else "never"
        left = (y["find_hours"] - y["book_wait"]) if y["book_wait"] is not None else 0
        print(f"  {y['weekday']} {y['hour']:02}:00 {y['last_pickup_weekday']} {y['last_pickup_hour']:02}:00    {(y['pickup'] + ' > ' + y['delivery'])[:34]:34} {y['drive'] / 60:7.1f} {y['near_delivery']:4} "
              f"{cause(y):13} {book(x):>25} {book(y):>30} {left:7.1f}  drops {y['drops']} late {y['late_hours'] if y['late_hours'] is None else round(y['late_hours'], 1)}")
print("\nlate under version 6, on time under the change:", sum(1 for k in set(ka) & set(kb) if not ka[k]["on_time"] and kb[k]["on_time"]))
print("late under both:", sum(1 for k in set(ka) & set(kb) if not ka[k]["on_time"] and not kb[k]["on_time"]))
