"""Does the live outage detector find the outage, and only from what it could know at the time?

    python -m lab.outage_check            # score 3.0
    python -m lab.outage_check 4.0

For each week with measured dealer limits (lab/limits.py) this does two separate things:
  1. The truth, with hindsight: the day and the town around which the measured limits (trust taken out, the
     day's level taken out) stand highest above the rest of that day, between 08:00 and 18:00.
  2. The live detector (dispatch/policy.py, `outage_answer`): the plain price book quotes each request as it
     arrives, gets the answer 15 minutes later (won when its price is at or under the measured limit), and the
     detector sees those answers in that order and nothing else.
Then it prints both, the minute the detector fired, and how many of the day's affected requests were still to come."""
from __future__ import annotations

import math
import sys
from collections import Counter, defaultdict
from types import SimpleNamespace

from dispatch.geo import neighbours
from dispatch.policy import ROAD_BASE, ROAD_MINUTE, Policy
from lab.limit_fit import load
from lab.orders import geo
from lab.runs import params_from

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]


def truth(rows: list[dict], regions: dict[str, set[str]]) -> tuple:
    """(gap, day, centre, towns): where the limits of one day's working hours stand out most."""
    best = (0.0, None, None, set())
    for day in range(5):
        today = [r for r in rows if r["day"] == day and 8 * 60 <= r["respondBy"] % 1440 < 18 * 60]
        for centre, region in regions.items():
            inside = [r["z"] for r in today if r["pickup"] in region]
            outside = [r["z"] for r in today if r["pickup"] not in region]
            if len(inside) >= 8 and len(outside) >= 8:
                gap = sum(inside) / len(inside) - sum(outside) / len(outside)
                if gap > best[0]:
                    best = (gap, day, centre, region)
    return best


def main() -> None:
    score = float(sys.argv[1]) if len(sys.argv) > 1 else 3.0
    g = geo()
    regions = {town: set(neighbours(g, town, 80)) for town in g.at}
    weeks = defaultdict(list)
    for row in load():
        row["z"] = row["y"] - math.log(1 + row["trusted"] / 100)
        weeks[row["seed"]].append(row)
    print(f"{'week':8} | truth: day, centre, limits there against the rest, requests | detector at score {score}: day, centre, fired at, affected requests still to come")
    hits = fired = 0
    for seed, rows in sorted(weeks.items()):
        rows.sort(key=lambda r: r["at"])
        gap, day, centre, region = truth(rows, regions)
        affected = [r for r in rows if r["day"] == day and r["pickup"] in region and 8 * 60 <= r["respondBy"] % 1440 < 18 * 60]
        policy = Policy(params_from({"cost": 1.0, "outage": score}))
        desk = SimpleNamespace(geo=g, stats=Counter(), requests={})
        waiting, found = [], None
        for row in rows:
            request = {"id": row["request"], "dealerId": row["dealer"], "arrivedAt": row["at"], "respondBy": row["respondBy"],
                       "legs": [{"pickup": {"placeId": row["pickup"]}, "delivery": {"placeId": row["delivery"]}}], "options": [{"kind": row["fastest"]}]}
            while waiting and waiting[0][0] < row["at"]:  # an answer of the same minute comes after the request, as in the real event order
                _, old, keys, markup, yes = waiting.pop(0)
                policy.outage_answer(desk, old, keys, markup, yes)
                policy.book.learn(keys, markup, yes)
                if policy.outage_towns and found is None:
                    found = (policy.day, old["respondBy"], set(policy.outage_towns))
            if row["at"] // 1440 != policy.day:  # what `quote` does each morning
                policy.day = row["at"] // 1440
                policy.book.new_day()
                policy.outage_seen = policy.outage_seen or bool(policy.outage_towns)
                policy.outage_towns, policy.answers_today = set(), []
                for key in [key for key in policy.book.offset if key[0] == "outage"]:
                    policy.book.offset[key] = 0.0
            if row["kind"] != "plain":
                continue
            keys = policy.keys_of(request, [row["fastest"]])
            cost = min(1.25 * row["typical"], max(0.8 * row["typical"], ROAD_BASE + ROAD_MINUTE * row["minutes"])) / row["list"]
            markup = policy.book.best_markup(keys, cost, floor=cost * 1.05, ceiling=3.0)[0]
            waiting.append((row["respondBy"], request, keys, markup, math.log(markup) <= row["y"]))
            waiting.sort(key=lambda item: item[0])
        line = f"{seed:8} | {DAYS[day]} {centre:12} {math.exp(gap) - 1:+5.0%} {len(affected):4} requests |"
        if found:
            fired += 1
            overlap = len(found[2] & region) / max(1, len(found[2] | region))
            right = found[0] == day and overlap >= 0.5
            hits += right
            left = sum(1 for r in affected if r["at"] > found[1]) if found[0] == day else 0
            line += f" {DAYS[found[0]]} {sorted(found[2], key=lambda t: -sum(r['pickup'] == t for r in rows))[0]:12} at {found[1] % 1440 // 60:02}:{found[1] % 60:02}  overlap {overlap:4.0%}  {'RIGHT' if right else 'WRONG'}  {left} of {len(affected)} still to come"
        else:
            line += " did not fire"
        print(line)
    print(f"\nfired in {fired} of {len(weeks)} weeks; the right day and at least half the region in {hits}")


if __name__ == "__main__":
    main()
