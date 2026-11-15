"""Every setting played in exact mode on the current version, against the defaults on the same weeks.

    python -m lab.tested [word]     # only settings whose text contains the word, for example private"""
import glob
import json
import statistics as st
import sys
from collections import defaultdict

from dispatch.policy import VERSION

HARD = set("fresh-9,fresh-12,hold-10,hold-17,hold-2,hold-9,fresh-20,lab-11".split(","))
word = sys.argv[1] if len(sys.argv) > 1 else ""
runs = defaultdict(dict)
for path in glob.glob("data/runs/L8-*.json"):
    try:
        run = json.load(open(path, encoding="utf-8"))
    except Exception:
        continue
    s = run.get("setting") or ""
    if s == "starter" or not s:
        continue
    setting = json.loads(s)
    if setting.get("version") != VERSION or setting.get("lab_step"):
        continue
    key = " ".join(f"{k}={v}" for k, v in sorted(setting.items()) if k != "version")
    runs[key][run["seed"]] = run["score"]
base = runs[""]
rows = []
for key, weeks in runs.items():
    both = [s for s in weeks if s in base]
    if not key or len(both) < 12 or word not in key:
        continue
    g = [(weeks[s]["marginCents"] - base[s]["marginCents"]) / 100 for s in both]
    shares = [weeks[s]["onTimeShare"] for s in both]
    hard = [weeks[s]["onTimeShare"] for s in both if s in HARD]
    hard6 = [base[s]["onTimeShare"] for s in both if s in HARD]
    rows.append((st.mean(g), key, len(both), st.stdev(g) / len(g) ** 0.5, st.mean(weeks[s]["wonOrders"] - base[s]["wonOrders"] for s in both), min(shares), sum(x < 0.9 for x in shares),
                 st.mean(hard) if hard else None, st.mean(hard6) if hard6 else None))
print(f"{'gain':>6} {'±':>4} {'weeks':>5} {'cars':>6} {'lowest':>7} {'<90':>3} {'8 hardest (v6)':>15}  setting")
for gain, key, n, err, cars, low, under, hard, hard6 in sorted(rows, reverse=True):
    print(f"{gain:+6.0f} {err:4.0f} {n:5} {cars:+6.1f} {low:7.1%} {under:3} {(f'{hard:.1%} ({hard6:.1%})' if hard else ''):>15}  {key}")
