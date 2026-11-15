"""Version 6, 60 exact weeks: which requests we do not quote, and which we quote and lose."""
from collections import defaultdict

from dispatch.geo import Geo
from lab.orders import geo, note_kind
from lab.runs import load, read_gz, REVEALS

g = geo()
cells = defaultdict(lambda: [0, 0, 0, 0.0])  # requests, quoted, won, list value of requests
n = 0
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
for fam in ("lab", "hold", "fresh"):
    for i in range(1, 21):
        run = load(8, f"{fam}-{i}", {})
        rv = read_gz(REVEALS / f"{run['worldId']}.json.gz")
        n += 1
        for x in rv["requests"]:
            r = x["request"]
            leg = r["legs"][0]
            quoted, won = bool(x.get("quote")), x["outcome"] == "won"
            drive = g.drive(leg) / 60
            private = leg["pickup"]["privateAddress"] or leg["delivery"]["privateAddress"]
            kinds = [o["kind"] for o in r["options"]]
            first_deadline = min(o["deadline"] for o in r["options"])
            last_deadline = max(o["deadline"] for o in r["options"])
            notice = (last_deadline - r["arrivedAt"]) / 60 - drive  # hours to find a driver on the latest option, roughly
            tags = {
                "all": "all",
                "legs": "one car" if len(r["legs"]) == 1 else "two cars or more",
                "private": "private address" if private else "dealer to dealer",
                "premium": "premium" if any(l["car"]["premium"] for l in r["legs"]) else "ordinary car",
                "electric": "electric" if any(l["car"]["electric"] for l in r["legs"]) else "not electric",
                "weekday": DAYS[r["arrivedAt"] // 1440 % 7],
                "options": "+".join(k[:4] for k in kinds),
                "drive": "under 2 h" if drive < 2 else "2-4 h" if drive < 4 else "4-5 h" if drive < 5 else "5-7 h" if drive < 7 else "7 h+",
                "time to find a driver (latest option)": "under 6 h" if notice < 6 else "6-12 h" if notice < 12 else "12-24 h" if notice < 24 else "24-48 h" if notice < 48 else "48 h+",
                "note": note_kind(r),
                "batch": "bulk order" if r.get("batchId") else "single request",
            }
            value = max(o["listPriceCents"] for o in r["options"]) / 100
            for k, v in tags.items():
                c = cells[k, v]
                c[0] += 1
                c[1] += quoted
                c[2] += won
                c[3] += value
print(f"weeks: {n}")
last = None
for (k, v), c in sorted(cells.items()):
    if k != last:
        print(f"\n{k}\n  {'':26} {'requests/wk':>11} {'quoted':>7} {'not quoted/wk':>13} {'won/wk':>7} {'won of quoted':>13} {'list value':>10}")
        last = k
    print(f"  {v[:26]:26} {c[0] / n:11.1f} {c[1] / max(1, c[0]):7.0%} {(c[0] - c[1]) / n:13.1f} {c[2] / n:7.1f} {c[2] / max(1, c[1]):13.0%} {c[3] / max(1, c[0]):10.0f}")
