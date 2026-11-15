"""Does snow make cars late? Compares cars whose last pickup day has a snow forecast at one of their two ends
with the rest, over the saved weeks of one setting.

    python -m lab.snow cost=1.0
"""
import sys
from collections import defaultdict

from lab.orders import geo, rows
from lab.runs import DATA, KINDS, load, read_gz

changed = {k: KINDS[k](v) for k, v in (item.split("=", 1) for item in sys.argv[1:])}
DAYS = {"Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6, "Mon": 7}  # a last pickup on a Monday is the Monday after
names = geo().name
groups, weeks, forecasts = defaultdict(list), 0, 0
for family in ("lab", "hold"):
    for n in range(1, 21):
        run = load(8, f"{family}-{n}", changed)
        path = DATA / "events" / f"{run['worldId']}.json.gz" if run else None
        if not run or not path.exists():
            continue
        weeks += 1
        snow = set()  # (town, day) with snow forecast
        for event in read_gz(path):
            if event["kind"] == "forecast":
                forecasts += 1
                for place in event["placeIds"]:
                    for day in range(event["from"] // 1440, (event["to"] - 1) // 1440 + 1):
                        snow.add((names[place], day))
        for r in rows(run):
            if r["cancelled"]:
                continue
            day = DAYS[r["last_pickup_weekday"]]
            ends = (r["pickup"], day) in snow, (r["delivery"], day) in snow
            groups["snow at both ends" if all(ends) else "snow at the pickup" if ends[0] else "snow at the delivery" if ends[1] else "no snow that day"].append(r)
print(f"{weeks} weeks, {forecasts} forecasts ({forecasts / max(1, weeks):.1f} a week)")
print(f"{'last pickup day':24} {'cars':>6} {'a week':>7} {'late':>7} {'dropped':>8} {'warned':>7} {'margin a car':>13}")
for name, g in sorted(groups.items(), key=lambda item: -len(item[1])):
    print(f"{name:24} {len(g):6} {len(g) / weeks:7.1f} {sum(not r['on_time'] for r in g) / len(g):7.1%} {sum(r['drops'] > 0 for r in g) / len(g):8.1%} "
          f"{sum(r['warned'] for r in g) / len(g):7.1%} {sum(r['margin'] for r in g) / len(g) / 100:13.1f}")
