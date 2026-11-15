"""Measures every dealer's price limit in a practice week with `fork`.

    python -m lab.limits --seed lab-3 --set cost=1.0 road_fee_blend=1.0 road_cost_blend=1.0
    python -m lab.limits --report

The desk plays the week as usual. One world minute before a request must be answered, the week is copied a
few times in a row. Each copy quotes every waiting request at one price for all of its options (the same
multiple of each option's list price), moves 16 minutes on, reads the dealers' answers, and is deleted. The
next copy asks each request higher if it won and lower if it lost, so six copies close in on the limit: the
highest multiple of the list price that the dealer still takes from us, to about 3%. The real week never sees
these quotes, so its result is the one of an ordinary run.

Requests that the desk declines (private addresses, premium cars, trade-ins, short notice) are measured too.
One row per request goes to data/probes/limits-<seed>.json."""
from __future__ import annotations

import argparse
import json
import time

from dispatch.desk import WAKE_ON
from dispatch.env import load_env
from dispatch.play import new_desk
from lab.runs import DATA, KINDS, create, params_from
from spread.client import Client, SpreadError

PROBES = DATA / "probes"
STEPS = 6  # copies per moment
FIRST_STEP = 1.15  # how far the second question lies from the first
LOWEST, HIGHEST = 0.7, 3.2  # multiples of the list price we never ask beyond


def next_question(row: dict) -> float:
    """The next price to ask for a request: beyond what we know while one side is open, then halfway."""
    won, lost = row["won_at"], row["lost_at"]
    if won is None and lost is None:
        return row["level"]
    if lost is None:
        return min(HIGHEST, won * FIRST_STEP ** (2 if row["asked"] > 2 else 1))
    if won is None:
        return max(LOWEST, lost / FIRST_STEP ** (2 if row["asked"] > 2 else 1))
    return (won * lost) ** 0.5


def measure(world, desk, waiting: dict[str, dict]) -> None:
    """Six copies of the world at this minute; each asks every waiting request one price."""
    until = max(row["respondBy"] for row in waiting.values()) + 1
    for _ in range(STEPS):
        asked = {rid: next_question(row) for rid, row in waiting.items()}
        quotes = [{"type": "quote", "requestId": rid, "prices": {o["kind"]: round(asked[rid] * o["listPriceCents"]) for o in desk.requests[rid]["options"]}} for rid in waiting]
        copy = None
        for attempt in range(30):  # the eight slots can be full for a moment
            try:
                copy = world.fork()
                break
            except SpreadError as error:
                if error.status != 409:
                    raise
                time.sleep(2)
        if copy is None:
            return
        try:
            step = copy.advance(to=until, actions=quotes)
            for event in step["events"]:
                if event["at"] < desk.now:
                    continue  # the copy's first answer repeats the week so far
                if event["kind"] == "order_won" and event["order"]["id"] in waiting:
                    row = waiting[event["order"]["id"]]
                    row["won_at"] = max(row["won_at"] or 0, asked[row["request"]])
                    row["chose"][f"{asked[row['request']]:.3f}"] = event["order"]["option"]
                elif event["kind"] == "order_lost" and event["requestId"] in waiting:
                    row = waiting[event["requestId"]]
                    row["lost_at"] = min(row["lost_at"] or 99, asked[row["request"]])
        finally:
            try:
                copy.delete()
            except SpreadError:
                pass
        for row in waiting.values():
            row["asked"] += 1


def probe_week(seed: str, changed: dict) -> list[dict]:
    client = Client()
    world = create(client, 8, seed)
    marker = DATA / "queue" / "running" / f"byhand-limits-{seed}.json"  # tells the worker that this world has an owner
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps({"level": 8, "seed": seed, "params": changed, "worldId": world.id}), encoding="utf-8")
    rows: dict[str, dict] = {}
    waiting: dict[str, dict] = {}
    try:
        snapshot = world.snapshot()
        ends_at = snapshot["endsAt"]
        desk = new_desk(client, world, 8, snapshot["now"], params_from(changed))
        while desk.now < ends_at:
            stop = min((row["respondBy"] for row in waiting.values()), default=ends_at + 1) - 1
            actions, desk.outbox = desk.outbox, []
            step = world.advance(until=WAKE_ON, max=min(ends_at, max(stop, desk.now)), actions=actions)
            desk.read_results(actions, step["results"])
            desk.now = step["now"]
            for event in step["events"]:
                desk.handle(event)
                if event["kind"] == "price_request":
                    request = event["request"]
                    leg, policy = request["legs"][0], desk.policy
                    quoted = policy.quoted.get(request["id"])
                    keys = policy.keys.get(request["id"]) or policy.keys_of(request, [o["kind"] for o in request["options"]])
                    rows[request["id"]] = waiting[request["id"]] = {
                        "seed": seed, "request": request["id"], "at": request["arrivedAt"], "respondBy": request["respondBy"], "dealer": request["dealerId"],
                        "batch": request.get("batchId"), "pickup": leg["pickup"]["placeId"], "delivery": leg["delivery"]["placeId"], "legs": len(request["legs"]),
                        "private_pickup": leg["pickup"]["privateAddress"], "private_delivery": leg["delivery"]["privateAddress"], "premium": leg["car"]["premium"],
                        "note": bool(request.get("note")), "options": {o["kind"]: o["listPriceCents"] for o in request["options"]}, "typical": request["referenceFeeCents"],
                        "minutes": desk.geo.minutes[leg["pickup"]["placeId"], leg["delivery"]["placeId"]], "level": policy.book.level(keys), "market": policy.book.market,
                        "trusted": policy.trusted.get(request["dealerId"], 0), "ours": quoted, "outcome": None, "took": None,
                        "won_at": None, "lost_at": None, "asked": 0, "chose": {}}
                elif event["kind"] == "order_won" and event["order"]["id"] in rows:
                    rows[event["order"]["id"]].update(outcome="won", took=event["order"]["option"])
                elif event["kind"] == "order_lost" and event["requestId"] in rows:
                    rows[event["requestId"]]["outcome"] = "lost"
            desk.tick()
            due = {rid: row for rid, row in waiting.items() if row["respondBy"] - desk.now <= 1}
            if due:  # the last minute for the oldest waiting request: measure everything that waits now
                desk.send()  # our own quotes first, so the real week has them whatever the copies do
                measure(world, desk, waiting)
                waiting.clear()
            for rid in [rid for rid, row in waiting.items() if row["respondBy"] <= desk.now]:
                del waiting[rid]  # answered before we could ask: stays unmeasured
        score = world.score()
        done = [r for r in rows.values() if r["asked"]]
        print(f"{seed}: {len(done)} of {len(rows)} requests measured; week margin {score['marginCents'] / 100:,.0f}, on time {score['onTimeShare']:.1%}", flush=True)
    finally:
        marker.unlink(missing_ok=True)
        try:
            world.delete()
        except SpreadError:
            pass
    return list(rows.values())


def report() -> None:
    rows = [row for path in sorted(PROBES.glob("limits-*.json")) for row in json.loads(path.read_text(encoding="utf-8"))]
    measured = [r for r in rows if r["asked"]]
    closed = [r for r in measured if r["won_at"] and r["lost_at"]]
    print(f"{len(rows)} requests in {len({r['seed'] for r in rows})} weeks; {len(measured)} measured, {len(closed)} with the limit between two prices")
    if not closed:
        return
    width = sorted(r["lost_at"] / r["won_at"] - 1 for r in closed)
    print(f"the two prices lie {width[len(width) // 2]:.1%} apart in the middle case, {width[len(width) * 9 // 10]:.1%} at the 90th percentile")
    never = sum(1 for r in measured if r["won_at"] is None)
    print(f"never won, even at {LOWEST} times the list price: {never} ({never / len(measured):.1%}); still won at {HIGHEST}: {sum(1 for r in measured if r['lost_at'] is None)}")
    limits = sorted((r["won_at"] * r["lost_at"]) ** 0.5 for r in closed)
    print("limit in list prices: " + "  ".join(f"{q}%: {limits[len(limits) * q // 100]:.2f}" for q in (5, 25, 50, 75, 95)))
    ratio = sorted((r["won_at"] * r["lost_at"]) ** 0.5 / r["level"] for r in closed)
    print("limit against our book's level: " + "  ".join(f"{q}%: {ratio[len(ratio) * q // 100]:.2f}" for q in (5, 25, 50, 75, 95)))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seed", default="lab-3")
    parser.add_argument("--set", nargs="*", default=[], metavar="NAME=VALUE")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()
    if args.report:
        return report()
    load_env()
    changed = {k: KINDS[k](v) for k, v in (item.split("=", 1) for item in args.set)}
    started = time.time()
    rows = probe_week(args.seed, changed)
    PROBES.mkdir(parents=True, exist_ok=True)
    (PROBES / f"limits-{args.seed}.json").write_text(json.dumps(rows), encoding="utf-8")
    print(f"saved {len(rows)} requests in {time.time() - started:.0f}s")


if __name__ == "__main__":
    main()
