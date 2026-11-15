"""What do the hard weeks look like? Late cars by the day of their last pickup, by cause and by thinness, cost 1.0."""
import sys
from collections import Counter, defaultdict

from lab.orders import rows
from lab.runs import DATA, load

CHANGED = {"cost": 1.0}
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
weeks = []
for family in ("lab", "hold"):
    for n in range(1, 21):
        run = load(8, f"{family}-{n}", CHANGED)
        if run and (DATA / "events" / f"{run['worldId']}.json.gz").exists():
            weeks.append(run)
print(f"{len(weeks)} weeks at cost 1.0 with details here")
table = []
for run in weeks:
    cars = [r for r in rows(run) if not r["cancelled"]]
    late = [r for r in cars if not r["on_time"]]
    by_day = Counter(r["last_pickup_weekday"] for r in late)
    all_day = Counter(r["last_pickup_weekday"] for r in cars)
    thin = lambda r: min(r["near_pickup"], r["near_delivery"]) < 40
    cause = Counter()
    for r in late:
        if r["drops"]:
            cause["dropped"] += 1
        elif r["failed"]:
            cause["failed visit"] += 1
        elif r["book_wait"] is None:
            cause["never booked"] += 1
        elif r["warned"]:
            cause["booked late"] += 1
        else:
            cause["other"] += 1
    worst = max(DAYS[:5], key=lambda d: by_day[d] / max(1, all_day[d]))
    table.append((1 - len(late) / len(cars), run["seed"], len(cars), len(late), sum(thin(r) for r in late), sum(thin(r) for r in cars),
                  " ".join(f"{d} {by_day[d]}/{all_day[d]}" for d in DAYS[:5]), dict(cause), cars[0]["drivers"], worst, sum(r["warned"] for r in cars)))
table.sort()
print("on time  seed      cars late (thin late / thin cars)  drivers  warned  late/cars by day of last pickup              causes")
for share, seed, n, late, thin_late, thin_cars, days, cause, drivers, worst, warned in table:
    print(f"{share:6.1%}  {seed:8} {n:4} {late:4}  ({thin_late:3}/{thin_cars:3})          {drivers:5}   {warned:4}   {days:44} {cause}")
