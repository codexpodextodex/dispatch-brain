"""Which cars get a deadline warning (no driver 3 hours before the last pickup)? By last-pickup hour, time to find, thinness."""
from collections import defaultdict

from lab.orders import rows
from lab.runs import DATA, load

CHANGED = {"cost": 1.0}
cars = []
for family in ("lab", "hold"):
    for n in range(1, 21):
        run = load(8, f"{family}-{n}", CHANGED)
        if run and (DATA / "events" / f"{run['worldId']}.json.gz").exists():
            week = [r for r in rows(run) if not r["cancelled"]]
            share = sum(r["on_time"] for r in week) / len(week)
            for r in week:
                r["hard"] = share < 0.93
            cars += week
print(f"{len(cars)} cars, {sum(r['hard'] for r in cars)} of them in hard weeks (under 93% on time)\n")


def table(title, key, order=None):
    print(title)
    print(f"   {'group':22} {'cars':>6} {'warned':>7} {'late':>6} | hard weeks: {'cars':>5} {'warned':>7} {'late':>6} | {'fee paid':>8} {'margin':>7}")
    groups = defaultdict(list)
    for r in cars:
        groups[key(r)].append(r)
    for name in (order or sorted(groups)):
        g = groups.get(name, [])
        if len(g) < 30:
            continue
        h = [r for r in g if r["hard"]]
        paid = [r["final_fee"] for r in g if r["final_fee"]]
        print(f"   {str(name):22} {len(g):6} {sum(r['warned'] for r in g) / len(g):7.1%} {sum(not r['on_time'] for r in g) / len(g):6.1%} |"
              f"             {len(h):5} {sum(r['warned'] for r in h) / max(1, len(h)):7.1%} {sum(not r['on_time'] for r in h) / max(1, len(h)):6.1%} |"
              f" {sum(paid) / max(1, len(paid)):8.2f} {sum(r['margin'] for r in g) / len(g) / 100:7.1f}")
    print()


def hour_band(r):
    h = r["last_pickup_hour"]
    return "1 before 09" if h < 9 else "2 09-11" if h < 11 else "3 11-13" if h < 13 else "4 13-15" if h < 15 else "5 15-17" if h < 17 else "6 17 or later"


def find_band(r):
    f = r["find_hours"]
    return "1 under 18 h" if f < 18 else "2 18-24 h" if f < 24 else "3 24-48 h" if f < 48 else "4 48-72 h" if f < 72 else "5 over 72 h"


def thin_band(r):
    m = min(r["near_pickup"], r["near_delivery"])
    return "1 under 10 drivers" if m < 10 else "2 10-20" if m < 20 else "3 20-40" if m < 40 else "4 40-100" if m < 100 else "5 100 or more"


table("By the hour of the last pickup", hour_band)
table("By the time we had to find a driver", find_band)
table("By the weekday of the last pickup", lambda r: r["last_pickup_weekday"], ["Tue", "Wed", "Thu", "Fri", "Sat", "Sun", "Mon"])
table("By drivers living within 30 km of the thinner end", thin_band)
table("By driving time", lambda r: "1 under 1 h" if r["drive"] < 60 else "2 1-2 h" if r["drive"] < 120 else "3 2-3 h" if r["drive"] < 180 else "4 3-5 h" if r["drive"] < 300 else "5 over 5 h")
table("By typical fee", lambda r: "1 under 20 eur" if r["typical"] < 2000 else "2 20-35" if r["typical"] < 3500 else "3 35-60" if r["typical"] < 6000 else "4 over 60")
table("By option", lambda r: r["option"])
warned = [r for r in cars if r["warned"]]
booked = [r for r in warned if r["final_fee"]]
print(f"warned cars: {len(warned)}; late {sum(not r['on_time'] for r in warned) / len(warned):.1%}; fee paid in the end, as a multiple of typical: "
      + "  ".join(f"{lo}-{hi}: {sum(lo <= r['final_fee'] < hi for r in booked) / len(booked):.0%}" for lo, hi in ((0, 1.3), (1.3, 1.7), (1.7, 1.9), (1.9, 2.3), (2.3, 9))))
print("when warned cars are late, by how many hours: " + "  ".join(f"{lo}-{hi} h: {sum(1 for r in warned if r['late_hours'] is not None and lo <= r['late_hours'] < hi)}" for lo, hi in ((0, 1), (1, 3), (3, 8), (8, 24), (24, 999))))
