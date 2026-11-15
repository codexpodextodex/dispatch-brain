"""How likely is a version to fall under 90% on time in one random week?

Counting weeks under 90% among 60 is too coarse: one week at 88.6% or 91.4% is partly luck. So: every exact-mode
run of version 6 and of its small variations gives, per week, the spread of the on-time share that small changes
of policy cause. With that spread as the noise of one week, the chance of a week under 90% for a version is the
mean over weeks of P(share + noise < 0.90)."""
import glob
import json
import math
import statistics as st
import sys
from collections import defaultdict

from lab.runs import load

FAMILIES = [("lab", 20), ("hold", 20), ("fresh", 20)]
SEEDS = [f"{f}-{i}" for f, n in FAMILIES for i in range(1, n + 1)]


def phi(z: float) -> float:
    return 0.5 * (1 + math.erf(z / 2 ** 0.5))


# 1. the spread per week across exact-mode runs of version 6 variations (same version, no fast mode, same cost)
by_seed = defaultdict(list)
for path in glob.glob("data/runs/L8-*.json"):
    try:
        run = json.load(open(path, encoding="utf-8"))
    except Exception:
        continue
    s = run.get("setting") or "{}"
    if s == "starter":
        continue
    s = json.loads(s)
    if s.get("version") != 6 or s.get("lab_step") or s.get("design") or "cost" in s or "day_cap" in s or "menu" in s:
        continue
    by_seed[run["seed"]].append((run["score"]["onTimeShare"], run["score"]["marginCents"] / 100, s))
print("weeks with exact runs of version 6 variations:", len(by_seed), " runs:", sum(len(v) for v in by_seed.values()))
pairs = []  # (mean share of the week, sd of the share across variations)
for seed, runs in by_seed.items():
    if len(runs) >= 5:
        shares = [r[0] for r in runs]
        pairs.append((st.mean(shares), st.stdev(shares), len(runs), seed))
pairs.sort()
print("\nspread of the on-time share of one week across small policy changes, by how hard the week is:")
for lo, hi in ((0, 0.94), (0.94, 0.96), (0.96, 0.975), (0.975, 1.01)):
    sel = [p for p in pairs if lo <= p[0] < hi]
    if sel:
        print(f"  weeks at {lo:.1%}-{hi:.1%}: {len(sel):2} weeks, sd {st.mean(p[1] for p in sel):.2%} (largest {max(p[1] for p in sel):.2%})")


def noise(share: float) -> float:
    for lo, hi in ((0, 0.94), (0.94, 0.96), (0.96, 0.975), (0.975, 1.01)):
        sel = [p[1] for p in pairs if lo <= p[0] < hi]
        if lo <= share < hi and sel:
            return st.mean(sel)
    return 0.012


# 2. the chance of a week under 90% per version
VERSIONS = [("version 6", {}), ("fee change", {"early_hour": 13.0, "night_hold": 1}),
            ("fee change + long trips 12 h", {"early_hour": 13.0, "night_hold": 1, "long_lead": 12.0}),
            ("fee change + guard 6%", {"early_hour": 13.0, "night_hold": 1, "guard": 0.06}),
            ("guard 6%", {"guard": 0.06}), ("menu=2", {"menu": 2}),
            ("half 1: early_hour=13", {"early_hour": 13.0}), ("half 2: night_hold=1", {"night_hold": 1}),
            ("early_hour=14 + night_hold", {"early_hour": 14.0, "night_hold": 1}),
            ("fee change, long drives keep rule", {"early_hour": 13.0, "night_hold": 1, "early_long": 15.0}),
            ("the same + guard 6%", {"early_hour": 13.0, "night_hold": 1, "early_long": 15.0, "guard": 0.06}),
            ("fee change + flu rescue, long", {"early_hour": 13.0, "night_hold": 1, "flu": 2}),
            ("night hold + weekend hold", {"night_hold": 1, "weekend_hold": 1})]
base = {s: load(8, s, {}) for s in SEEDS}
print(f"\n{'version':30} {'weeks':>5} {'mean':>7} {'gain':>12} {'lowest':>7} {'<90':>3} {'<92':>3} {'chance of a week under 90%':>27} {'same weeks, v6':>15} {'5 weeks all ranked':>19}")
for name, setting in VERSIONS:
    runs = {s: load(8, s, setting) for s in SEEDS}
    both = [s for s in SEEDS if runs[s] and base[s]]
    if len(both) < 10:
        print(f"{name:30} {len(both):5}")
        continue
    shares = [runs[s]["score"]["onTimeShare"] for s in both]
    gains = [(runs[s]["score"]["marginCents"] - base[s]["score"]["marginCents"]) / 100 for s in both]
    risk = st.mean(phi((0.90 - x) / noise(x)) for x in shares)
    risk6 = st.mean(phi((0.90 - base[s]["score"]["onTimeShare"]) / noise(base[s]["score"]["onTimeShare"])) for s in both)
    print(f"{name:30} {len(both):5} {st.mean(runs[s]['score']['marginCents'] for s in both) / 100:7,.0f} {st.mean(gains):+6,.0f} ± {st.stdev(gains) / len(gains) ** 0.5:3,.0f} "
          f"{min(shares):7.1%} {sum(x < 0.90 for x in shares):3} {sum(x < 0.92 for x in shares):3} {risk:27.1%} {risk6:15.1%} {(1 - risk) ** 5:19.1%}")

# 3. the weeks where the fee change and version 6 differ most in on-time share
FEE = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {"early_hour": 13.0, "night_hold": 1}
fee = {s: load(8, s, FEE) for s in SEEDS}
rows = sorted(((fee[s]["score"]["onTimeShare"] - base[s]["score"]["onTimeShare"], s) for s in SEEDS if fee[s] and base[s]))
print("\nfee change against version 6, on-time share: mean change", f"{st.mean(r[0] for r in rows):+.2%}", " weeks lower:", sum(r[0] < 0 for r in rows), " higher:", sum(r[0] > 0 for r in rows))
print("  largest falls:", ", ".join(f"{s} {base[s]['score']['onTimeShare']:.1%}->{fee[s]['score']['onTimeShare']:.1%}" for _, s in rows[:6]))
print("  largest rises:", ", ".join(f"{s} {base[s]['score']['onTimeShare']:.1%}->{fee[s]['score']['onTimeShare']:.1%}" for _, s in rows[-6:]))
hard = "fresh-9,fresh-12,hold-10,hold-17,hold-2,hold-9,fresh-20,lab-11".split(",")
print("  eight hardest weeks: version 6", f"{st.mean(base[s]['score']['onTimeShare'] for s in hard):.1%}", " fee change", f"{st.mean(fee[s]['score']['onTimeShare'] for s in hard if fee[s]):.1%}",
      " margin gain on them", f"{st.mean((fee[s]['score']['marginCents'] - base[s]['score']['marginCents']) / 100 for s in hard if fee[s]):+,.0f}")
