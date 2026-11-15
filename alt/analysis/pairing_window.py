"""How long a won car waits for a driver, and how often a round-trip partner arrives after the car is booked.

Reads version 6's saved exact weeks (no play). For each plain won car: hours from the win to its first booking,
and the clock hour of that booking. For each two plain cars won the same week whose geometry makes a round trip
(as desk.pair_start: hop <= 60 road minutes, way back <= 90, both last pickups on the same day): how many hours
passed between the two wins, and whether the first car was already booked when the second was won.

    PYTHONPATH=. python -X utf8 -m alt.analysis.pairing_window"""
from __future__ import annotations

from collections import Counter, defaultdict

from lab.orders import geo
from lab.runs import EVENTS, load, read_gz

DAY, HOUR = 1440, 60


def weeks():
    for family in ("lab", "hold", "fresh"):
        for n in range(1, 21):
            run = load(8, f"{family}-{n}", {})
            if run:
                yield run


def main() -> None:
    g = geo()
    waits, book_hour, gaps, already, total_pairs, pair_days = [], Counter(), [], 0, 0, Counter()
    posted_pairs = 0
    for run in weeks():
        events = read_gz(EVENTS / f"{run['worldId']}.json.gz")
        won, first_book, gig_orders = {}, {}, {}
        for e in events:
            if e["kind"] == "order_won":
                o = e["order"]
                if len(o["legs"]) == 1 and not o["legs"][0]["car"]["premium"] and not any(o["legs"][0][end]["privateAddress"] for end in ("pickup", "delivery")):
                    won[o["id"]] = (e["at"], o)
            elif e["kind"] == "gig_booked":
                for oid in e.get("orderIds", []) or []:
                    first_book.setdefault(oid, e["at"])
        # gig_booked may not carry order ids: map via snapshot gigs
        if not first_book:
            from lab.orders import snapshot_of
            snap = snapshot_of(run["worldId"])
            gig_orders = {gig["id"]: {s["orderId"] for s in gig["stops"]} for gig in snap["gigs"]}
            for e in events:
                if e["kind"] == "gig_booked":
                    orders = gig_orders.get(e["gigId"], set())
                    if len(orders) > 1 and not any(o in first_book for o in orders):
                        posted_pairs += 1
                    for oid in orders:
                        first_book.setdefault(oid, e["at"])
        for oid, (at, o) in won.items():
            if oid in first_book:
                waits.append((first_book[oid] - at) / HOUR)
                book_hour[first_book[oid] % DAY // HOUR] += 1
        items = sorted(won.items(), key=lambda kv: kv[1][0])
        for i, (ida, (ta, a)) in enumerate(items):
            la = a["legs"][0]
            for idb, (tb, b) in items[i + 1:]:
                lb = b["legs"][0]
                if a["lastPickupAt"] // DAY != b["lastPickupAt"] // DAY:
                    continue
                ok = False
                for x, y in ((la, lb), (lb, la)):
                    hop = g.minutes[(x["delivery"]["placeId"], y["pickup"]["placeId"])]
                    back = g.minutes[(y["delivery"]["placeId"], x["pickup"]["placeId"])]
                    if hop <= 60 and back <= 90 and g.drive(x) + hop + g.drive(y) <= 12 * HOUR:
                        ok = True
                if ok:
                    total_pairs += 1
                    gaps.append((tb - ta) / HOUR)
                    if ida in first_book and first_book[ida] <= tb:
                        already += 1
                    pair_days[a["lastPickupAt"] // DAY] += 1
    waits.sort()
    q = lambda xs, f: xs[int(f * (len(xs) - 1))]
    print(f"plain cars booked: {len(waits)}; hours from win to first booking: p10 {q(waits, .1):.1f} p25 {q(waits, .25):.1f} median {q(waits, .5):.1f} p75 {q(waits, .75):.1f} p90 {q(waits, .9):.1f}")
    for h in (1, 2, 4, 8, 12, 24):
        print(f"  booked within {h:>2} h: {sum(w <= h for w in waits) / len(waits):.0%}")
    print("first booking by clock hour:", " ".join(f"{h}:{book_hour[h]}" for h in range(24)))
    gaps.sort()
    weeks_n = sum(1 for _ in weeks())
    print(f"round-trip couples among won plain cars: {total_pairs / weeks_n:.0f} a week (not disjoint); pairs booked as one gig: {posted_pairs / weeks_n:.0f} a week")
    print(f"  hours between the two wins: p25 {q(gaps, .25):.1f} median {q(gaps, .5):.1f} p75 {q(gaps, .75):.1f}")
    for h in (1, 2, 4, 8, 24):
        print(f"  second won within {h:>2} h of the first: {sum(x <= h for x in gaps) / len(gaps):.0%}")
    print(f"  first already booked when the second was won: {already / total_pairs:.0%}")


if __name__ == "__main__":
    main()
