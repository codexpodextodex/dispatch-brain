"""One row for each order we won in a saved week: what the request was, what we quoted, how its gig went
with the drivers, and its money. lab/patterns.py groups these rows to show which cars make and lose money."""
from __future__ import annotations

import json
from collections import defaultdict

from dispatch.env import load_env
from dispatch.geo import Geo
from dispatch.notes import read
from collections import Counter

from dispatch.geo import neighbours
from lab.runs import DATA, EVENTS, REVEALS, ROSTERS, SNAPSHOTS, read_gz, write_gz
from spread.client import Client

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_geo: Geo | None = None


def geo() -> Geo:
    global _geo
    if _geo is None:
        path = DATA / "map.json"
        if not path.exists():
            load_env()
            path.write_text(json.dumps(Client().map()), encoding="utf-8")
        _geo = Geo(json.loads(path.read_text(encoding="utf-8")))
    return _geo


def snapshot_of(world_id: str) -> dict:
    path = SNAPSHOTS / f"{world_id}.json.gz"
    if not path.exists():  # a week saved before we kept snapshots: an ended world can still be read
        load_env()
        snapshot = Client().world(world_id).snapshot()
        write_gz(path, {"orders": snapshot["orders"], "gigs": snapshot["gigs"]})
    return read_gz(path)


def roster_of(world_id: str) -> list:
    path = ROSTERS / f"{world_id}.json.gz"
    if not path.exists():
        old = DATA / "rosters" / f"{world_id}.json"  # from before we saved rosters with each run
        if old.exists():
            write_gz(path, json.loads(old.read_text(encoding="utf-8")))
        else:
            load_env()
            write_gz(path, Client().world(world_id).roster())
    return read_gz(path)


def note_kind(request: dict) -> str:
    if not request["note"]:
        return "no note"
    facts = read(request["note"], request["arrivedAt"])
    kinds = [name for name, on in (("plates", facts.plates), ("manual", facts.manual), ("summer tyres", facts.summer_tyres), ("ready later", facts.pickup_from),
                                   ("deadline", facts.deadline), ("pickup hours", facts.pickup_opens is not None or facts.pickup_closes is not None),
                                   ("delivery hours", facts.delivery_opens is not None or facts.delivery_closes is not None)) if on]
    return "+".join(kinds) if kinds else "harmless note"


def rows(run: dict) -> list[dict]:
    """The orders of one saved run. Needs the run's events and reveal (lab/runs.py saves them)."""
    world_id = run["worldId"]
    events, reveal, snapshot = read_gz(EVENTS / f"{world_id}.json.gz"), read_gz(REVEALS / f"{world_id}.json.gz"), snapshot_of(world_id)
    g = geo()
    homes = Counter(driver["homePlaceId"] for driver in roster_of(world_id))
    near = {place: sum(homes[other] for other in neighbours(g, place)) for place in g.at}  # drivers living within 30 km
    answers = {x["request"]["id"]: x for x in reveal["requests"]}
    final = {o["id"]: o for o in snapshot["orders"]}
    # A gig can carry two cars (a pair): what happens to the gig happens to both, and its fee is shared between them.
    gig_orders = {gig["id"]: list(dict.fromkeys(stop["orderId"] for stop in gig["stops"])) for gig in snapshot["gigs"]}
    story: dict[str, list] = defaultdict(list)
    money: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    won = {}
    for event in events:
        kind = event["kind"]
        if kind == "order_won":
            won[event["order"]["id"]] = event
        elif kind == "ledger":
            line = event["line"]
            ids = [line["orderId"]] if line["orderId"] else gig_orders.get(line["gigId"], [])
            for k, order_id in enumerate(ids):  # cents shared evenly, the odd cent to the first car
                money[order_id][line["kind"]] += line["cents"] // len(ids) + (line["cents"] % len(ids) if k == 0 else 0)
        elif event.get("orderId"):
            story[event["orderId"]].append(event)
        else:
            ids = gig_orders.get(event.get("gigId"), [])
            for order_id in ids:
                story[order_id].append({**event, "feeCents": event["feeCents"] / len(ids)} if len(ids) > 1 and "feeCents" in event else event)
    out = []
    for order_id, event in won.items():
        order, last = event["order"], final.get(order_id)
        request = answers[order_id]["request"]
        leg = request["legs"][0]
        lane = (leg["pickup"]["placeId"], leg["delivery"]["placeId"])
        option = next(o for o in request["options"] if o["kind"] == order["option"])
        mine = story[order_id]
        books = [e for e in mine if e["kind"] == "gig_booked"]
        typical = request["referenceFeeCents"]
        delivered = [d for d in (last["deliveredAt"] if last else []) if d is not None]
        cancelled = bool(last) and last["status"] == "cancelled"
        on_time = bool(last) and last["status"] == "delivered" and all(d is not None and d <= last["deadline"] for d in last["deliveredAt"])
        m = money[order_id]
        out.append({
            "seed": run["seed"], "order": order_id, "dealer": request["dealerId"], "weekday": WEEKDAYS[event["at"] // 1440 % 7], "hour": event["at"] % 1440 // 60,
            "option": order["option"], "pickup": g.name[lane[0]], "delivery": g.name[lane[1]], "km": g.km[lane], "drive": g.drive(leg), "legs": len(request["legs"]),
            "private": leg["pickup"]["privateAddress"] or leg["delivery"]["privateAddress"], "premium": leg["car"]["premium"], "electric": leg["car"]["electric"],
            "near_pickup": near[lane[0]], "near_delivery": near[lane[1]], "drivers": sum(homes.values()),
            "typical": typical, "list": option["listPriceCents"], "price": order["priceCents"], "markup": order["priceCents"] / option["listPriceCents"],
            "find_hours": (order["lastPickupAt"] - event["at"]) / 60, "last_pickup_weekday": WEEKDAYS[order["lastPickupAt"] // 1440 % 7], "last_pickup_hour": order["lastPickupAt"] % 1440 // 60,
            "note": note_kind(request), "cancelled": cancelled, "on_time": on_time,
            "paired": any(order_id in ids and len(ids) > 1 for ids in gig_orders.values()),
            "late_hours": (max(delivered) - last["deadline"]) / 60 if last and delivered and not on_time and len(delivered) == len(last["deliveredAt"]) else None,
            "undelivered": bool(last) and not cancelled and len(delivered) < len(last["deliveredAt"]),
            "book_wait": (books[0]["at"] - event["at"]) / 60 if books else None, "first_fee": books[0]["feeCents"] / typical if books else None,
            "final_fee": books[-1]["feeCents"] / typical if books else None, "bookings": len(books),
            "drops": sum(1 for e in mine if e["kind"] in ("gig_dropped", "no_show")), "failed": [e["reason"] for e in mine if e["kind"] == "visit_failed"],
            "warned": any(e["kind"] == "deadline_close" for e in mine), "changed": sum(1 for e in mine if e["kind"] == "order_changed"),
            "revenue": m["revenue"], "fees": -m["driver_fee"], "refunds": -(m["late_refund"] + m["undelivered_penalty"]),
            "other": -(m["failed_visit"] + m["release_fee"] + m["waiting"] + m["fine"]), "margin": sum(m.values()),
        })
    return out
