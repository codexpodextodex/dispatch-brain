"""The candidates with 60 exact weeks: gain by family, lowest weeks, chance of a week under 90%."""
import math
import statistics as st
import sys

from lab.runs import load

SEEDS = [f"{f}-{i}" for f in ("lab", "hold", "fresh") for i in range(1, 21)]
HARD = "fresh-9,fresh-12,hold-10,hold-17,hold-2,hold-9,fresh-20,lab-11".split(",")


def phi(z):
    return 0.5 * (1 + math.erf(z / 2 ** 0.5))


def noise(x):
    return 0.0162 if x < 0.94 else 0.0081 if x < 0.96 else 0.0064 if x < 0.975 else 0.0054


CANDS = [("version 10", {}),
         ("cap kept after Friday for drives of 3 h and more", {"cap_after_hours": 3.0}),
         ("cap kept after Friday for drives of 4 h and more", {"cap_after_hours": 4.0}),
         ("cap kept after Friday for drives of 5 h and more", {"cap_after_hours": 5.0}),
         ("after Friday a 4 h+ drive pays for the long cars only, 2 per 100 drivers", {"cap_after_hours": 4.0, "cap_long": 0.02}),
         ("... 1.5 per 100 drivers", {"cap_after_hours": 4.0, "cap_long": 0.015}),
         ("version 9 (cap after Friday for every car)", {"cap_week_only": 0}),
         ("premium cars due after Friday", {"premium_after": 1}), ("long private drives due after Friday", {"private_after": 1})]
base = {s: load(8, s, {}) for s in SEEDS}
print(f"{'candidate':48} {'wks':>3} {'gain':>12} {'lab':>6} {'hold':>6} {'fresh':>6} {'better':>6} {'cars':>5} {'8 hardest':>9} {'<90':>3} {'risk':>5} {'5 wks ranked':>12}  lowest weeks")
for name, s in CANDS:
    runs = {x: load(8, x, s) for x in SEEDS}
    both = [x for x in SEEDS if runs[x] and base[x]]
    if len(both) < 8:
        print(f"{name:48} {len(both):3}")
        continue
    g = {x: (runs[x]["score"]["marginCents"] - base[x]["score"]["marginCents"]) / 100 for x in both}
    fam = lambda f: st.mean([g[x] for x in both if x.startswith(f)] or [0])
    sh = {x: runs[x]["score"]["onTimeShare"] for x in both}
    risk = st.mean(phi((0.90 - v) / noise(v)) for v in sh.values())
    low = sorted((v, x) for x, v in sh.items())[:3]
    print(f"{name:48} {len(both):3} {st.mean(g.values()):+6.0f} ± {st.stdev(g.values()) / len(g) ** .5:3.0f} {fam('lab'):+6.0f} {fam('hold'):+6.0f} {fam('fresh'):+6.0f} {sum(v > 0 for v in g.values()):3}/{len(g):<2} "
          f"{st.mean(runs[x]['score']['wonOrders'] for x in both):5.0f} {st.mean([sh[x] for x in both if x in HARD] or [0]):9.1%} {sum(v < .9 for v in sh.values()):3} {risk:5.1%} {(1 - risk) ** 5:12.0%}  "
          + ", ".join(f"{x} {v:.1%}" for v, x in low))
