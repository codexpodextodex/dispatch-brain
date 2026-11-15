"""What kinds of week are there, how often, and what does each version earn in each kind?

    python -m lab.week_types

From the 60 practice weeks (three seed families). A week's kind is what the world does in it, not what we do:
how many requests arrive, and on which day drivers fall ill (four or more of a day's bookings given back in its
first hour). Flu days are read from the saved version 6 weeks in data/cars.json.gz (python -m lab.cars_dump)."""
import glob
import gzip
import json
import statistics as st
from collections import defaultdict

from lab.runs import load

data = json.load(gzip.open("data/cars.json.gz", "rt", encoding="utf-8"))
flu = {w["seed"]: [d for d in w["flu"] if d <= 4] for w in data["weeks"] if not w["setting"]}
monday_wave = {w["seed"]: 7 in w["flu"] for w in data["weeks"] if not w["setting"]}
v6 = {}
for path in glob.glob("data/runs/L8-*.json"):
    run = json.load(open(path, encoding="utf-8"))
    if run.get("setting") == '{"version": 6}':
        v6[run["seed"]] = run
seeds = [f"{f}-{i}" for f in ("lab", "hold", "fresh") for i in range(1, 21)]
v7 = {s: load(8, s, {}) for s in seeds}
seeds = [s for s in seeds if v7[s] and s in v6 and s in flu]
requests = {s: v7[s]["stats"].get("price_request", 0) for s in seeds}
cut = sorted(requests.values())
lo, hi = cut[len(cut) // 3], cut[2 * len(cut) // 3]


def table(title, kind):
    groups = defaultdict(list)
    for s in seeds:
        groups[kind(s)].append(s)
    print(f"\n{title}")
    print(f"  {'kind of week':34} {'weeks':>5} {'chance':>6} {'requests':>8} | {'v6 margin':>9} {'on time':>7} {'lowest':>7} | {'v7 margin':>9} {'cars':>5} {'on time':>7} {'lowest':>7} {'v7 - v6':>8}")
    for name in sorted(groups):
        g = groups[name]
        m6, m7 = st.mean(v6[s]["score"]["marginCents"] for s in g) / 100, st.mean(v7[s]["score"]["marginCents"] for s in g) / 100
        print(f"  {name[2:]:34} {len(g):5} {len(g) / len(seeds):6.0%} {st.mean(requests[s] for s in g):8.0f} | {m6:9,.0f} {st.mean(v6[s]['score']['onTimeShare'] for s in g):7.1%} {min(v6[s]['score']['onTimeShare'] for s in g):7.1%} | "
              f"{m7:9,.0f} {st.mean(v7[s]['score']['wonOrders'] for s in g):5.0f} {st.mean(v7[s]['score']['onTimeShare'] for s in g):7.1%} {min(v7[s]['score']['onTimeShare'] for s in g):7.1%} {m7 - m6:+8,.0f}")


print(f"{len(seeds)} weeks. Requests in a week: {min(cut)} to {max(cut)}, median {st.median(cut):.0f}.")
table("by the day drivers fall ill (the last such day of the week)",
      lambda s: "0 no such day" if not flu[s] else "1 Tuesday" if max(flu[s]) == 1 else "2 Wednesday" if max(flu[s]) == 2 else "3 Thursday" if max(flu[s]) == 3 else "4 Friday")
table("by how many such days", lambda s: f"{len(flu[s])} {len(flu[s])} flu day(s)")
table("by the size of the week (requests)", lambda s: "0 lean (bottom third)" if requests[s] < lo else "1 middle" if requests[s] < hi else "2 rich (top third)")
table("size and flu together", lambda s: ("0 lean" if requests[s] < lo else "1 middle" if requests[s] < hi else "2 rich") + (", flu Thu or Fri" if flu[s] and max(flu[s]) >= 3 else ", flu earlier or none"))
table("drivers giving back the last Monday's bookings", lambda s: "1 yes" if monday_wave[s] else "0 no")
table("snow forecast in the week", lambda s: "1 yes" if v7[s]["stats"].get("forecast", 0) else "0 no")
m = [v7[s]["score"]["marginCents"] / 100 for s in seeds]
print(f"\nversion 7 over all weeks: mean {st.mean(m):,.0f}, median {st.median(m):,.0f}, a week in ten under {sorted(m)[len(m) // 10]:,.0f}, a week in ten over {sorted(m)[-len(m) // 10]:,.0f}; "
      f"margin against requests: correlation {st.correlation([requests[s] for s in seeds], m):.2f}")
