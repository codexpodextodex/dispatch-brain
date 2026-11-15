"""A rehearsal of the final on a practice world: the clock moves by itself and the desk answers from the
live stream, exactly as `python -m dispatch --final` does.

    python -m lab.live_check                 # Monday and Tuesday of level 8, seed lab-1, at the final's speed
    python -m lab.live_check --days 1 --speed 2

One thread moves the clock of a practice world as the final's clock moves (18 real seconds for a weekday hour
from 06:00 to 22:00, 3 seconds for a night hour). The main thread runs the final runner on that world. Then the
script reads the reveal of what was played and counts the requests that got no quote in time: in the final,
each of those goes to the competitor. It also stops the desk once in the middle and starts it again."""
from __future__ import annotations

import argparse
import threading
import time

from dispatch.env import load_env
from dispatch.play import play_final
from lab.runs import create, own
from spread.client import Client, SpreadError

HOUR, DAY = 60, 24 * 60


class Stop(Exception):
    pass


def seconds_per_hour(minute: int) -> float:
    """The final's clock: a weekday hour from 06:00 to 22:00 takes 18 real seconds, a night hour 3."""
    day, hour = minute // DAY % 7, minute % DAY // HOUR
    return 18.0 if day < 5 and 6 <= hour < 22 else 3.0


def tick_clock(world_id: str, until: int, speed: float, state: dict) -> None:
    world = Client().world(world_id)  # its own connection: the kit's client is not made for two threads
    now = world.snapshot()["now"]
    while now < until and not state.get("abort"):
        started = time.monotonic()
        now = world.advance(by=1)["now"]
        state["now"] = now
        time.sleep(max(0.0, seconds_per_hour(now) / 60 / speed - (time.monotonic() - started)))
    state["done"] = True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seed", default="lab-1")
    parser.add_argument("--days", type=float, default=2.0, help="how much of the week to play")
    parser.add_argument("--speed", type=float, default=1.0, help="2 runs the clock twice as fast as the final")
    args = parser.parse_args()
    load_env()
    client = Client()
    world = create(client, 8, args.seed)
    marker = own(world)
    until = int(args.days * DAY)
    state: dict = {"now": 0}
    sent: list[tuple[int, int]] = []  # (world minute, actions) for each request the desk sent
    try:
        clock = threading.Thread(target=tick_clock, args=(world.id, until, args.speed, state), daemon=True)
        clock.start()

        def watch(desk) -> None:
            state["desk"] = desk
            if desk.outbox:
                sent.append((state["now"], len(desk.outbox)))
            if state.get("done") or (not state.get("restarted") and state["now"] >= until // 2):
                raise Stop  # once in the middle: the desk "dies" and a new one starts from the world alone

        for attempt in (1, 2):
            try:
                play_final(client, world, clock=lambda: state["now"], on_send=watch)
            except Stop:
                if state.get("done"):
                    break
                state["restarted"] = True
                print(f"desk stopped at world minute {state['now']}; starting a new one", flush=True)
        clock.join(timeout=5)
        snapshot = world.snapshot()
        events = world.events()
        requests = {e["request"]["id"]: e["request"] for e in events if e["kind"] == "price_request"}
        answered = {e["order"]["id"] for e in events if e["kind"] == "order_won"} | {e["requestId"] for e in events if e["kind"] == "order_lost"}
        decided = [r for r in requests.values() if r["respondBy"] <= snapshot["now"]]
        open_orders = [o for o in snapshot["orders"] if o["status"] == "waiting"]
        with_gig = {stop["orderId"] for gig in snapshot["gigs"] if gig["status"] in ("open", "booked", "working") for stop in gig["stops"]}
        print(f"played to world minute {snapshot['now']}: {len(decided)} requests decided, {len(answered)} answered by a dealer to us (won or lost)")
        print(f"orders won {snapshot['score']['wonOrders']}, waiting orders without a live gig: {sum(1 for o in open_orders if o['id'] not in with_gig)}")
        print(f"requests the desk sent: {len(sent)}, actions: {sum(n for _, n in sent)}, largest batch: {max((n for _, n in sent), default=0)}")
        late = {reason: n for reason, n in state["desk"].refused.items() if reason.startswith("quote")} if state.get("desk") else {}
        print(f"quotes the world refused (too late or other): {late or 'none'}")
        # A restart takes a few real seconds, and a request leaves 4.5: the requests of those seconds may go unanswered.
        ok = len(decided) > 0 and sum(late.values()) <= 0.02 * len(decided) and all(o["id"] in with_gig for o in open_orders)
        print("PASS" if ok else "FAIL")
    finally:
        state["abort"] = True
        marker.unlink(missing_ok=True)
        try:
            world.delete()
        except SpreadError:
            pass


if __name__ == "__main__":
    main()
