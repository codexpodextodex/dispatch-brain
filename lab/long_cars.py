"""Version 6, 60 exact weeks: the long drives. Late share and money by drive length, option and time to find a driver."""
import statistics as st
from collections import defaultdict

from lab.late_causes import cause
from lab.orders import rows
from lab.runs import load

HARD = set("fresh-9,fresh-12,hold-10,hold-17,hold-2,hold-9,fresh-20,lab-11,lab-19,fresh-2,lab-18,lab-10,hold-14,hold-13,hold-12".split(","))
allrows = []
for fam in ("lab", "hold", "fresh"):
    for i in range(1, 21):
        run = load(8, f"{fam}-{i}", {})
        allrows += [r for r in rows(run) if not r["cancelled"] and r["legs"] == 1]
print("cars:", len(allrows), " late:", sum(not r["on_time"] for r in allrows))


def table(title, key, sel=lambda r: True):
    groups = defaultdict(list)
    for r in allrows:
        if sel(r):
            groups[key(r)].append(r)
    print(f"\n{title}")
    print(f"  {'group':22} {'cars/wk':>7} {'late':>6} {'late/wk':>7} {'hard wks late':>13} {'margin/car':>10} {'on time':>8} {'late':>7} {'refund/car':>10} {'fee typ':>7} {'price/list':>10}")
    for g in sorted(groups):
        rr = groups[g]
        late = [r for r in rr if not r["on_time"]]
        hard = [r for r in rr if r["seed"] in HARD]
        print(f"  {str(g):22} {len(rr) / 60:7.1f} {len(late) / len(rr):6.1%} {len(late) / 60:7.2f} {sum(not r['on_time'] for r in hard) / max(1, len(hard)):13.1%} {st.mean(r['margin'] for r in rr) / 100:10.1f} "
              f"{st.mean([r['margin'] for r in rr if r['on_time']] or [0]) / 100:8.1f} {st.mean([r['margin'] for r in late] or [0]) / 100:7.1f} {sum(r['refunds'] for r in rr) / len(rr) / 100:10.1f} "
              f"{st.mean(r['final_fee'] or 0 for r in rr):7.2f} {st.mean(r['markup'] for r in rr):10.2f}")


def drive(r):
    d = r["drive"] / 60
    return "1 under 2 h" if d < 2 else "2 2-4 h" if d < 4 else "3 4-5 h" if d < 5 else "4 5-6 h" if d < 6 else "5 6-7 h" if d < 7 else "6 7-8 h" if d < 8 else "7 8 h+"


table("by drive length", drive)
long = lambda r: r["drive"] >= 7 * 60
mid = lambda r: 5 * 60 <= r["drive"] < 7 * 60
table("7 h+ by option", lambda r: r["option"], long)
table("7 h+ by hours from win to last pickup", lambda r: "1 under 18 h" if r["find_hours"] < 18 else "2 18-30 h" if r["find_hours"] < 30 else "3 30-54 h" if r["find_hours"] < 54 else "4 54 h+", long)
table("7 h+ late cars by cause", cause, lambda r: long(r) and not r["on_time"])
table("5-7 h by option", lambda r: r["option"], mid)
table("5-7 h by hours from win to last pickup", lambda r: "1 under 18 h" if r["find_hours"] < 18 else "2 18-30 h" if r["find_hours"] < 30 else "3 30-54 h" if r["find_hours"] < 54 else "4 54 h+", mid)
table("5-7 h late cars by cause", cause, lambda r: mid(r) and not r["on_time"])
table("5-7 h by last-pickup weekday", lambda r: r["last_pickup_weekday"], mid)
table("all cars by drivers living near the delivery", lambda r: "1 none" if r["near_delivery"] == 0 else "2 1-10" if r["near_delivery"] <= 10 else "3 11-50" if r["near_delivery"] <= 50 else "4 over 50")
table("5 h+ by drivers near the delivery", lambda r: "1 none" if r["near_delivery"] == 0 else "2 1-10" if r["near_delivery"] <= 10 else "3 11-50" if r["near_delivery"] <= 50 else "4 over 50", lambda r: r["drive"] >= 300)
