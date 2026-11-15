"""Version 6, 60 weeks: for every weekday of every week, the bookings for that day given back in its first hour,
and the late share of the cars whose last pickup is that day."""
import statistics as st
from collections import Counter, defaultdict

from lab.cars_dump import FIELDS
from lab.orders import rows, snapshot_of
from lab.runs import EVENTS, load, read_gz

days = []  # (seed, day, night drops, cars due, late, by drive bucket)
for fam in ("lab", "hold", "fresh"):
    for i in range(1, 21):
        run = load(8, f"{fam}-{i}", {})
        events = read_gz(EVENTS / f"{run['worldId']}.json.gz")
        won = {e["order"]["id"]: e["order"] for e in events if e["kind"] == "order_won"}
        gig_day = {g["id"]: won[g["stops"][0]["orderId"]]["lastPickupAt"] // 1440 for g in snapshot_of(run["worldId"])["gigs"] if g["stops"][0]["orderId"] in won}
        drops = Counter()
        for e in events:
            if e["kind"] == "gig_dropped" and e["at"] % 1440 < 60 and gig_day.get(e["gigId"]) == e["at"] // 1440:
                drops[e["at"] // 1440] += 1
        due = defaultdict(lambda: defaultdict(lambda: [0, 0]))
        for r in rows(run):
            if r["cancelled"] or r["legs"] != 1:
                continue
            day = won[r["order"]]["lastPickupAt"] // 1440
            b = "short" if r["drive"] < 120 else "mid" if r["drive"] < 240 else "long"
            for key in ("all", b):
                due[day][key][0] += 1
                due[day][key][1] += not r["on_time"]
        for day in range(0, 5):
            days.append((f"{fam}-{i}", day, drops[day], {k: tuple(v) for k, v in due[day].items()}, run["score"]["onTimeShare"]))


def share(sel, key):
    n = sum(d[3].get(key, (0, 0))[0] for d in sel)
    return sum(d[3].get(key, (0, 0))[1] for d in sel) / max(1, n), n / max(1, len(sel))


print(f"{'night drops':12} {'days':>4} {'cars due':>8} {'late all':>8} {'short':>7} {'mid':>7} {'long':>7}   worst days (late share of cars due)")
for lo, hi in ((0, 0), (1, 3), (4, 6), (7, 9), (10, 14), (15, 99)):
    sel = [d for d in days if lo <= d[2] <= hi]
    if not sel:
        continue
    per = sorted((d[3].get("all", (1, 0))[1] / max(1, d[3].get("all", (1, 0))[0]) for d in sel), reverse=True)
    print(f"{f'{lo}-{hi}':12} {len(sel):4} {share(sel, 'all')[1]:8.0f} {share(sel, 'all')[0]:8.1%} {share(sel, 'short')[0]:7.1%} {share(sel, 'mid')[0]:7.1%} {share(sel, 'long')[0]:7.1%}   "
          + " ".join(f"{x:.0%}" for x in per[:8]))
flu = [d for d in days if d[2] >= 4]
print("\nflu days (4 drops or more) by weekday:", dict(sorted(Counter(d[1] for d in flu).items())))
for wd in range(1, 5):
    sel = [d for d in flu if d[1] == wd]
    per = sorted((d[3].get("all", (1, 0))[1] / max(1, d[3].get("all", (1, 0))[0]) for d in sel), reverse=True)
    print(f"  weekday {wd}: {len(sel)} flu days, cars due {share(sel, 'all')[1]:.0f}, late {share(sel, 'all')[0]:.1%}; by day: " + " ".join(f"{x:.0%}" for x in per))
print("\nlate cars of a week that were due on its flu days:", f"{sum(d[3].get('all', (0, 0))[1] for d in flu)} of {sum(d[3].get('all', (0, 0))[1] for d in days)} (due on days 0-4)")
print("weeks by number of flu days:", dict(sorted(Counter(Counter(d[0] for d in flu).values()).items())), " weeks with none:", 60 - len({d[0] for d in flu}))
hard = sorted({(d[4], d[0]) for d in days})[:10]
for s, seed in hard:
    print(f"  {seed:9} {s:.1%}: " + "  ".join(f"d{d[1]} drops {d[2]} late {d[3].get('all', (0, 0))[1]}/{d[3].get('all', (0, 0))[0]}" for d in days if d[0] == seed))
