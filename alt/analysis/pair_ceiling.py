"""How many disjoint round trips the plain cars that version 6 won in a week allow, at several limits for the
hop to the second car and the way back (a greedy matching, ignoring when each car was won: a ceiling for a desk
that could wait for every partner). Uses the feasibility test of swarm/capacity/pair_space.py.

    PYTHONPATH=. python -X utf8 -m alt.analysis.pair_ceiling"""
from __future__ import annotations

from collections import Counter

from lab.orders import geo
from lab.runs import EVENTS, load, read_gz

DAY = 1440
g = geo()


def fits(a: dict, b: dict, hop_max: int, back_max: int) -> bool:
    hop, back = g.minutes[(a["deli"], b["pick"])], g.minutes[(b["deli"], a["pick"])]
    if hop > hop_max or back > back_max or a["drive"] + hop + b["drive"] > 720:
        return False
    lo, hi = max(a["from"], b["from"] - a["drive"] - hop - 120), min(a["last"], b["last"] - a["drive"] - hop)
    return lo <= hi and lo // DAY == hi // DAY


def match(cars: list, hop_max: int, back_max: int) -> int:
    pairs = [(a, b) for a in cars for b in cars if a is not b and fits(a, b, hop_max, back_max)]
    degree = Counter()
    for a, b in pairs:
        degree.update([a["id"], b["id"]])
    used, n = set(), 0
    for a, b in sorted(pairs, key=lambda ab: degree[ab[0]["id"]] + degree[ab[1]["id"]]):
        if a["id"] not in used and b["id"] not in used:
            used |= {a["id"], b["id"]}
            n += 1
    return n


def main() -> None:
    limits = [(60, 90), (90, 120), (120, 180)]
    total, weeks = Counter(), 0
    for family in ("lab", "hold", "fresh"):
        for n in range(1, 21):
            run = load(8, f"{family}-{n}", {})
            if not run:
                continue
            weeks += 1
            cars = []
            for e in read_gz(EVENTS / f"{run['worldId']}.json.gz"):
                if e["kind"] == "order_won" and len(e["order"]["legs"]) == 1:
                    leg = e["order"]["legs"][0]
                    if leg["car"]["premium"] or leg["pickup"]["privateAddress"] or leg["delivery"]["privateAddress"]:
                        continue
                    cars.append({"id": e["order"]["id"], "pick": leg["pickup"]["placeId"], "deli": leg["delivery"]["placeId"], "from": leg["pickup"]["window"]["from"],
                                 "last": e["order"]["lastPickupAt"], "drive": g.drive(leg)})
            total["cars"] += len(cars)
            for hop, back in limits:
                total[hop, back] += match(cars, hop, back)
    print(f"{weeks} weeks, {total['cars'] / weeks:.0f} plain cars a week")
    for hop, back in limits:
        print(f"  hop <= {hop:3} min, back <= {back:3} min: {total[hop, back] / weeks:5.1f} disjoint round trips a week")


if __name__ == "__main__":
    main()
