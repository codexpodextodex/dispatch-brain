"""Reads the dealers' exact answers with `fork`: the same requests, the same minute, the same future, at several
prices.

    python -m lab.probe --seed lab-3 --set cost=1.0         # one week, probed at about 60 moments
    python -m lab.probe --report                            # what all saved probes say

The desk plays a practice week as usual. At some of the moments when it is about to quote, the script copies
the world a few times. In each copy it sends the same quotes times a factor (0.8, 0.9, 1.1, 1.25, 1.45), moves
the copy's clock past the response deadline, and reads which requests the dealer gave us. The copy is then
deleted, and the real week goes on with our own quotes. Because a copy has the same future draws, the answers
differ only by the price: for each request we learn the highest of the six prices that would have won.

A copy answers its first move of the clock with the whole history of the week, so a probe late in the week is a
large download. That is why only some moments are probed."""
from __future__ import annotations

import argparse
import json
import math
import time
from collections import defaultdict

from dispatch.desk import WAKE_ON
from dispatch.env import load_env
from dispatch.play import new_desk
from dispatch.pricing import chance
from lab.runs import DATA, KINDS, create, params_from
from spread.client import Client, SpreadError

LADDER = (0.8, 0.9, 1.1, 1.25, 1.45)
PROBES = DATA / "probes"


def probe_week(seed: str, changed: dict, every: int, least: int) -> list[dict]:
    client = Client()
    world = create(client, 8, seed)
    marker = DATA / "queue" / "running" / f"byhand-probe-{seed}.json"  # tells the worker that this world has an owner
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps({"level": 8, "seed": seed, "params": changed, "worldId": world.id}), encoding="utf-8")
    rows: list[dict] = []
    try:
        snapshot = world.snapshot()
        desk = new_desk(client, world, 8, snapshot["now"], params_from(changed))
        last_probe = -10_000
        while desk.now < snapshot["endsAt"]:
            quotes = [a for a in desk.outbox if a["type"] == "quote" and a["requestId"] in desk.policy.quoted]
            if len(quotes) >= least and desk.now - last_probe >= every:
                last_probe = desk.now
                desk.send()  # the real quotes go first, so every copy starts with them and only replaces the prices
                answers: dict[str, dict[float, bool]] = defaultdict(dict)
                for factor in LADDER:
                    copy = world.fork()
                    try:
                        scaled = [{**q, "prices": {kind: round(cents * factor) for kind, cents in q["prices"].items()}} for q in quotes]
                        step = copy.advance(to=desk.now + 16, actions=scaled)
                        for event in step["events"]:
                            if event["at"] >= desk.now and event["kind"] == "order_won" and event["order"]["id"] in desk.policy.quoted:
                                answers[event["order"]["id"]][factor] = True
                            elif event["at"] >= desk.now and event["kind"] == "order_lost" and event["requestId"] in desk.policy.quoted:
                                answers[event["requestId"]][factor] = False
                    finally:
                        try:
                            copy.delete()
                        except SpreadError:
                            pass
                for quote in quotes:
                    request = desk.requests[quote["requestId"]]
                    keys = desk.policy.keys.get(request["id"], [])
                    rows.append({"seed": seed, "request": request["id"], "at": desk.now, "dealer": request["dealerId"], "to": request["legs"][0]["delivery"]["placeId"],
                                 "options": sorted(desk.policy.quoted[request["id"]]), "markup": min(desk.policy.quoted[request["id"]].values()),
                                 "level": desk.policy.book.level(keys), "typical": request["referenceFeeCents"], "list": request["options"][0]["listPriceCents"],
                                 "answers": {str(k): v for k, v in answers[request["id"]].items()}})
            actions, desk.outbox = desk.outbox, []
            step = world.advance(until=WAKE_ON, max=snapshot["endsAt"], actions=actions)
            desk.read_results(actions, step["results"])
            desk.now = step["now"]
            for event in step["events"]:
                desk.handle(event)
                if event["kind"] in ("order_won", "order_lost"):  # the answer to our own price, factor 1.0
                    rid = event["order"]["id"] if event["kind"] == "order_won" else event["requestId"]
                    for row in rows:
                        if row["request"] == rid and row["seed"] == seed:
                            row["answers"]["1.0"] = event["kind"] == "order_won"
            desk.tick()
        score = world.score()
        print(f"{seed}: {len(rows)} requests probed; week margin {score['marginCents'] / 100:,.0f}, on time {score['onTimeShare']:.1%}", flush=True)
    finally:
        marker.unlink(missing_ok=True)
        try:
            world.delete()
        except SpreadError:
            pass
    return rows


def report() -> None:
    rows = [row for path in PROBES.glob("price-*.json") for row in json.loads(path.read_text(encoding="utf-8"))]
    rows = [r for r in rows if len(r["answers"]) == len(LADDER) + 1]
    factors = sorted(float(k) for k in rows[0]["answers"])
    print(f"{len(rows)} requests, each answered at {len(factors)} prices around our quote\n")
    print("price as a multiple of our quote -> share won, and margin per request at that price (cost = 1.0 typical fee)")
    for factor in factors:
        won = [r for r in rows if r["answers"][str(factor)]]
        value = sum(r["markup"] * factor * r["list"] - r["typical"] for r in won) / len(rows) / 100
        print(f"   x{factor:<5} won {len(won) / len(rows):6.1%}   margin per request {value:6.2f}")
    odd = sum(1 for r in rows if any(r["answers"][str(a)] is False and r["answers"][str(b)] is True for a in factors for b in factors if b > a))
    print(f"\nrequests that lost at a lower price but won at a higher one: {odd} ({odd / len(rows):.1%})")
    highest = [max((f for f in factors if r["answers"][str(f)]), default=0.0) for r in rows]
    print("highest winning price, as a multiple of our quote: " + "  ".join(f"x{f}: {sum(1 for h in highest if h == f) / len(rows):.1%}" for f in [0.0] + factors))
    # how sharp is the dealer's answer around the level our book holds? compare with the spread the book assumes
    print("\nby our quote against the book's level (markup / level): share won at our own price, and what the book expected")
    for low, high in ((0, 0.9), (0.9, 1.0), (1.0, 1.1), (1.1, 1.25), (1.25, 9)):
        group = [r for r in rows if low <= r["markup"] / r["level"] < high]
        if group:
            expected = sum(chance(r["level"], r["markup"], 0.14) for r in group) / len(group)
            print(f"   {low:.2f}-{high:.2f}: {len(group):5} requests, won {sum(r['answers']['1.0'] for r in group) / len(group):6.1%}, book expected {expected:6.1%}")
    # the best single factor by expected margin, overall and by group
    def best(group: list[dict]) -> str:
        values = {f: sum(r["markup"] * f * r["list"] - r["typical"] for r in group if r["answers"][str(f)]) / len(group) / 100 for f in factors}
        top = max(values, key=values.get)
        return f"best x{top} ({values[top]:.2f} a request against {values[1.0]:.2f} at our price), {len(group)} requests"
    print("\nall requests:", best(rows))
    for name, key in (("weekday", lambda r: ["Mon", "Tue", "Wed", "Thu", "Fri"][r["at"] // 1440]), ("options", lambda r: "+".join(r["options"]))):
        groups = defaultdict(list)
        for r in rows:
            groups[key(r)].append(r)
        for value, group in sorted(groups.items()):
            if len(group) >= 40:
                print(f"   {name} {value}: {best(group)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seed", default="lab-3")
    parser.add_argument("--set", nargs="*", default=[], metavar="NAME=VALUE")
    parser.add_argument("--every", type=int, default=45, help="at most one probe in this many world minutes")
    parser.add_argument("--least", type=int, default=2, help="probe only when at least this many quotes go out together")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()
    if args.report:
        return report()
    load_env()
    changed = {k: KINDS[k](v) for k, v in (item.split("=", 1) for item in args.set)}
    started = time.time()
    rows = probe_week(args.seed, changed, args.every, args.least)
    PROBES.mkdir(parents=True, exist_ok=True)
    (PROBES / f"price-{args.seed}.json").write_text(json.dumps(rows), encoding="utf-8")
    print(f"saved {len(rows)} probed requests in {time.time() - started:.0f}s")


if __name__ == "__main__":
    main()
