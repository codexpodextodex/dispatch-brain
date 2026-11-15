"""What predicts a dealer's limit? Reads the measured limits (lab/limits.py) and shows how much of their spread
each fact about a request explains.

    python -m lab.limit_fit                 # all measured weeks
    python -m lab.limit_fit lab             # only the weeks of one family

The limit of a request is the highest multiple of the list price the dealer takes (the same multiple on every
option). We work with its logarithm, as the price book does: a spread of 0.10 is about 10%."""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict

from dispatch.policy import ROAD_BASE, ROAD_MINUTE
from lab.runs import DATA

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]


def load(prefix: str = "") -> list[dict]:
    rows = []
    for path in sorted((DATA / "probes").glob(f"limits-{prefix}*.json")):
        for r in json.loads(path.read_text(encoding="utf-8")):
            if r["won_at"] and r["lost_at"]:
                r["y"] = math.log((r["won_at"] * r["lost_at"]) ** 0.5)
                r["day"], r["hour"] = r["at"] // 1440, r["at"] % 1440 // 60
                r["menu"] = "+".join(sorted(r["options"]))
                r["fastest"] = min(r["options"], key=["same_day", "next_day", "within_3_days"].index)
                r["kind"] = "trade-in" if r["legs"] == 2 else "premium" if r["premium"] else "private pickup" if r["private_pickup"] else "private delivery" if r["private_delivery"] else "plain"
                r["noise"] = r["typical"] / (ROAD_BASE + ROAD_MINUTE * r["minutes"])
                r["list"] = r["options"][r["fastest"]]
                rows.append(r)
    return rows


def spread(values: list[float]) -> float:
    mean = sum(values) / len(values)
    return (sum((v - mean) ** 2 for v in values) / len(values)) ** 0.5


def table(rows: list[dict], title: str, key, least: int = 25) -> None:
    groups = defaultdict(list)
    for r in rows:
        groups[key(r)].append(r["y"])
    print(f"\n{title}")
    for name, ys in sorted(groups.items(), key=lambda item: str(item[0])):
        if len(ys) >= least:
            print(f"   {str(name):26} {len(ys):6}   limit {math.exp(sum(ys) / len(ys)):5.2f} x list   spread {spread(ys):.3f}")


def remove(rows: list[dict], key, name: str, by_week: bool = True) -> None:
    """Takes the mean of each group out of `y` and says how much spread is left."""
    groups = defaultdict(list)
    for r in rows:
        groups[(r["seed"] if by_week else None, key(r))].append(r)
    for group in groups.values():
        mean = sum(r["y"] for r in group) / len(group)
        for r in group:
            r["y"] -= mean
    print(f"   after {name:44} {spread([r['y'] for r in rows]):.3f}   ({len(groups)} group means)")


def main() -> None:
    rows = load(sys.argv[1] if len(sys.argv) > 1 else "")
    weeks = sorted({r["seed"] for r in rows})
    print(f"{len(rows)} requests with a measured limit, {len(weeks)} weeks: {' '.join(weeks)}")
    print(f"spread of the limit (log): {spread([r['y'] for r in rows]):.3f};   of the limit against our book's level at that minute: {spread([r['y'] - math.log(r['level']) for r in rows]):.3f}")
    table(rows, "By the kind of request", lambda r: r["kind"])
    table(rows, "By weekday", lambda r: DAYS[r["day"]])
    table(rows, "By hour", lambda r: f"{r['hour']:02}")
    table(rows, "By the options the dealer asks for", lambda r: r["menu"])
    table(rows, "By dealer (the ten biggest)", lambda r: r["dealer"], least=len(rows) // 40)
    table(rows, "By the size of the list price", lambda r: "1 under 80 eur" if r["list"] < 8000 else "2 80-120" if r["list"] < 12000 else "3 120-180" if r["list"] < 18000 else "4 180-260" if r["list"] < 26000 else "5 over 260")
    table(rows, "By road time", lambda r: "1 under 1 h" if r["minutes"] < 60 else "2 1-2 h" if r["minutes"] < 120 else "3 2-3 h" if r["minutes"] < 180 else "4 3-5 h" if r["minutes"] < 300 else "5 over 5 h")
    table(rows, "By the typical fee against the road line (its noise)", lambda r: "1 under 0.85" if r["noise"] < 0.85 else "2 0.85-0.95" if r["noise"] < 0.95 else "3 0.95-1.05" if r["noise"] < 1.05 else "4 1.05-1.15" if r["noise"] < 1.15 else "5 over 1.15")
    table(rows, "By our on-time orders with the dealer so far", lambda r: "0" if r["trusted"] == 0 else "1-5" if r["trusted"] <= 5 else "6-15" if r["trusted"] <= 15 else "16-25")
    table(rows, "Part of a bulk order", lambda r: bool(r["batch"]))
    print("\nHow much spread is left when we take out, one after the other, the mean of each group (within each week):")
    print(f"   at the start {'':45} {spread([r['y'] for r in rows]):.3f}")
    remove(rows, lambda r: None, "the week's own level")
    remove(rows, lambda r: r["kind"], "the kind of request")
    remove(rows, lambda r: r["day"], "the weekday")
    remove(rows, lambda r: r["dealer"], "the dealer")
    remove(rows, lambda r: (r["dealer"], r["day"]), "the dealer on that day")
    remove(rows, lambda r: r["menu"], "the options asked for")
    remove(rows, lambda r: r["delivery"], "the delivery town")
    remove(rows, lambda r: r["pickup"], "the pickup town")
    remove(rows, lambda r: (r["pickup"], r["delivery"]), "the lane")
    remove(rows, lambda r: (r["day"], r["hour"]), "the hour of that day")


if __name__ == "__main__":
    main()
