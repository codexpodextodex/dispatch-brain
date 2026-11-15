"""How much dealer trust do we hold when a request arrives, and what do late cars cost us in it?

A dealer counts our on-time orders up to 25, each worth 1% on the prices it accepts; a late order halves the
count. This replays the saved weeks of the default version: the count each dealer held at each request, as it
was, and as it would have been had no car come late."""
import statistics as st
from collections import defaultdict

from lab.runs import EVENTS, load, read_gz

rows = []
by_day = defaultdict(lambda: [0, 0.0, 0.0, 0.0])
share_top4 = []
for fam in ("lab", "hold", "fresh"):
    for i in range(1, 21):
        run = load(8, f"{fam}-{i}", {})
        if not run:
            continue
        events = read_gz(EVENTS / f"{run['worldId']}.json.gz")
        orders, real, ideal, left = {}, defaultdict(int), defaultdict(int), {}
        seen, asked, value = [], defaultdict(int), 0.0
        lates = 0
        for e in events:
            kind = e["kind"]
            if kind == "price_request":
                r = e["request"]
                asked[r["dealerId"]] += 1
                seen.append((e["at"], r["dealerId"], real[r["dealerId"]], ideal[r["dealerId"]]))
            elif kind == "order_won":
                o = e["order"]
                orders[o["id"]] = o
                left[o["id"]] = [None] * len(o["legs"])
            elif kind == "order_changed" and e["order"]["id"] in orders:
                orders[e["order"]["id"]] = e["order"]
            elif kind == "delivered" and e.get("orderId") in left:
                left[e["orderId"]][e["leg"]] = e["at"]
                if None not in left[e["orderId"]]:
                    o = orders[e["orderId"]]
                    on_time = max(left[e["orderId"]]) <= o["deadline"]
                    d = o["dealerId"]
                    real[d] = min(25, real[d] + 1) if on_time else real[d] // 2
                    ideal[d] = min(25, ideal[d] + 1)
                    lates += not on_time
        top = sorted(asked.values(), reverse=True)
        share_top4.append((sum(top[:4]) / sum(top), len(top)))
        rows.append((st.mean(s[2] for s in seen), st.mean(s[3] for s in seen), lates, run["score"]["onTimeShare"], run["seed"]))
        for at, d, a, b in seen:
            c = by_day[at // 1440]
            c[0] += 1
            c[1] += a
            c[2] += b
            c[3] += 25
print(f"weeks {len(rows)}; dealers in a week {st.mean(n for _, n in share_top4):.0f}; the four largest send {st.mean(s for s, _ in share_top4):.0%} of the requests")
print(f"mean trust count at a request: as it was {st.mean(r[0] for r in rows):.1f}, with no late car {st.mean(r[1] for r in rows):.1f}, the most possible 25")
print("by day of the request:   " + "  ".join(f"d{d}: {c[1] / c[0]:4.1f} (no late {c[2] / c[0]:4.1f})" for d, c in sorted(by_day.items()) if d < 5))
print(f"so late cars cost {st.mean(r[1] - r[0] for r in rows):.1f} points of accepted price on the average request; late cars a week {st.mean(r[2] for r in rows):.1f}")
print("weeks sorted by on-time share: trust lost (points) in the five hardest:", ", ".join(f"{r[4]} {r[3]:.1%}: {r[1] - r[0]:.1f}" for r in sorted(rows, key=lambda r: r[3])[:5]),
      "| five easiest:", ", ".join(f"{r[3]:.1%}: {r[1] - r[0]:.1f}" for r in sorted(rows, key=lambda r: -r[3])[:5]))
