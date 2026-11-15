"""A candidate against the current version on a seed family that was used for nothing: check-1..20.

    python lab/confirm.py pair_safe=1 windows=1 guard=0.08       (queue the weeks first, with lab.sweep --prefix check)"""
import statistics as st
import sys

from lab.runs import KINDS, load

changed = {k: KINDS[k](v) for k, v in (a.split("=", 1) for a in sys.argv[1:])}
seeds = [f"check-{i}" for i in range(1, 21)]
a, b = {s: load(8, s, {}) for s in seeds}, {s: load(8, s, changed) for s in seeds}
both = [s for s in seeds if a[s] and b[s]]
print(f"{len(both)} of 20 weeks played under both")
if both:
    g = [(b[s]["score"]["marginCents"] - a[s]["score"]["marginCents"]) / 100 for s in both]
    for name, runs in (("current version", a), ("candidate", b)):
        sh = [runs[s]["score"]["onTimeShare"] for s in both]
        print(f"  {name:16} mean {st.mean(runs[s]['score']['marginCents'] for s in both) / 100:8,.0f}  cars {st.mean(runs[s]['score']['wonOrders'] for s in both):4.0f}  on time {st.mean(sh):.1%}  "
              f"lowest {min(sh):.1%}  under 93%: {sum(v < .93 for v in sh)}  under 90%: {sum(v < .9 for v in sh)}  worst week {min(runs[s]['score']['marginCents'] for s in both) / 100:,.0f}")
    print(f"  gain {st.mean(g):+,.0f} ± {st.stdev(g) / len(g) ** .5 if len(g) > 1 else 0:.0f} a week, better in {sum(x > 0 for x in g)} of {len(g)} weeks; per week: {sorted(round(x) for x in g)}")
