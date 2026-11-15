"""Scores the note reader against the truth of every order we have won in practice.

    python -m lab.notes_score            # the score for each kind of fact
    python -m lab.notes_score --misses   # also the notes it got wrong

The reveal of a practice week says what each won order's note meant. lab/sweep.py --keep saves reveals in
data/worlds/, and this script reads every one of them."""
from __future__ import annotations

import json
import sys

from dispatch.env import ROOT
from dispatch.notes import read
from lab.runs import read_gz


def truths() -> list[dict]:
    """One row for each distinct won single-car order with a note: the note, and what was true."""
    rows: dict[tuple, dict] = {}
    paths = list((ROOT / "data" / "reveals").glob("*.json*")) + list((ROOT / "data" / "worlds").glob("*/reveal.json"))
    for path in paths:
        reveal = read_gz(path) if path.suffix == ".gz" else json.loads(path.read_text(encoding="utf-8"))
        answers = {x["request"]["id"]: x for x in reveal["requests"]}
        for order in reveal["orders"]:
            answer = answers[order["orderId"]]
            request = answer["request"]
            if len(request["legs"]) != 1 or not request["note"]:
                continue
            deadline = next(o["deadline"] for o in request["options"] if o["kind"] == answer["option"])
            rows[(request["id"], request["arrivedAt"], request["note"]["text"])] = {"request": request, "leg": request["legs"][0], "truth": order["legs"][0], "deadline": deadline}
    return list(rows.values())


def hours(h: dict | None) -> tuple | None:
    return None if h is None else (h["opens"], h["closes"])


def main() -> None:
    rows, show = truths(), "--misses" in sys.argv
    kinds = ["plates", "manual", "summer tyres", "ready or released later", "pickup hours", "delivery hours", "deadline"]
    score = {k: {"right": 0, "missed": 0, "wrong": 0, "false alarm": 0} for k in kinds}
    misses: dict[str, list[str]] = {k: [] for k in kinds}
    for row in rows:
        request, leg, truth = row["request"], row["leg"], row["truth"]
        text, arrived = request["note"]["text"], request["arrivedAt"]
        facts = read(request["note"], arrived)

        def mark(kind: str, real, got, safe=None) -> None:
            """`real` and `got` are None when there is nothing to find. `safe` says whether a different answer still avoids the harm."""
            if real is None and got is None:
                return
            outcome = "right" if real == got else "false alarm" if real is None else "missed" if got is None else "right" if safe and safe(real, got) else "wrong"
            score[kind][outcome] += 1
            if outcome != "right":
                misses[kind].append(f"{outcome:11} real {real} got {got} | {text}")

        mark("plates", truth["needsPlates"] or None, facts.plates or None)
        mark("manual", truth["manualGearbox"] or None, facts.manual or None)
        mark("summer tyres", truth["summerTyres"] or None, facts.summer_tyres or None)
        stated = leg["pickup"]["window"]["from"]
        later = max(truth["readyAt"] or 0, truth["releasedAt"] or 0)
        mark("ready or released later", later if later > stated else None, facts.pickup_from if facts.pickup_from and facts.pickup_from > stated else None)
        for site, key in (("pickup", "pickupHours"), ("delivery", "deliveryHours")):
            real, said = hours(truth[key]), hours(leg[site]["hours"])
            got = (getattr(facts, f"{site}_opens") or (said[0] if said else None), getattr(facts, f"{site}_closes") or (said[1] if said else None)) if said else None
            mark(f"{site} hours", real if real != said else None, got if got != said else None)
        tighter = lambda at: at if at is not None and at < row["deadline"] else None  # a deadline that is not tighter changes nothing
        mark("deadline", tighter(truth["noteDeadline"]), tighter(facts.deadline))
    print(f"{len(rows)} won orders with a note\n")
    print(f"{'fact':26} {'right':>6} {'missed':>7} {'wrong':>6} {'false alarm':>12}")
    for kind in kinds:
        s = score[kind]
        print(f"{kind:26} {s['right']:>6} {s['missed']:>7} {s['wrong']:>6} {s['false alarm']:>12}")
        if show:
            for line in sorted(set(misses[kind]))[:40]:
                print("     " + line)


if __name__ == "__main__":
    main()
