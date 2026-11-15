"""Plays a world with the desk: a practice week that we step ourselves, or the final on its live clock."""
from __future__ import annotations

import importlib
import time

from spread import starter as kit
from spread.client import Client, World

from .desk import WAKE_ON, Desk
from .geo import DAY, HOUR, Geo
from .policy import Params, Policy


def new_desk(client: Client, world: World, level: int, now: int, params: Params = Params()) -> Desk:
    if params.design:  # the lab only: a whole different desk from alt/, to compare designs on the same weeks
        return importlib.import_module(f"alt.{params.design}").make(client, world, level, now, params)
    if params.trade_hour:  # the desk that also carries trade-ins, by the customer's hour
        from .trade import Trade, build
        return build(client, world, level, now, params, Trade(on=True, line=True, evening=True))
    if params.windows and "driver_late" not in WAKE_ON:
        WAKE_ON.append("driver_late")  # the practice clock must stop at the notice; the live stream of the final brings it by itself
    desk = Desk(world, level, now, Policy(params), Geo(client.map()))
    desk.meet(world.roster())
    return desk


def play_practice(world: World, desk: kit.Desk, record: list | None = None) -> dict:
    """Steps a practice world from one event that needs an answer to the next, to the end. One request a step:
    the advance applies the desk's waiting actions at the current minute, then moves the clock. `record`
    collects the week's events for the lab, without the views: the reveal has those."""
    ends_at = world.snapshot()["endsAt"]
    stride = getattr(desk.policy.p, "lab_step", 0) if hasattr(desk, "policy") else 0
    wake = WAKE_ON + ["delivered"] if hasattr(desk, "policy") and desk.policy.p.chain_fee else WAKE_ON  # a chain offer answers a delivery
    if hasattr(desk, "policy") and desk.policy.p.flu:
        wake = wake + ["gig_dropped"]  # the flu shows in the drops just after midnight: wake for them
    while desk.now < ends_at:
        actions, desk.outbox = desk.outbox, []
        if stride and desk.now // DAY % 7 < 5 and 8 * HOUR <= desk.now % DAY < 18 * HOUR + 20:
            # The lab's fast mode: in the hours when requests come, answer them every `stride` minutes together.
            # A quote has 15 minutes, so nothing is missed; a week costs a quarter of the calls.
            step = world.advance(to=min(ends_at, desk.now + stride), actions=actions)
        else:
            step = world.advance(until=wake, max=ends_at, actions=actions)
        desk.read_results(actions, step["results"])
        desk.now = step["now"]
        for event in step["events"]:
            desk.handle(event)
            if record is not None and event["kind"] != "gig_viewed":
                record.append(event)
        if hasattr(desk, "tick"):
            desk.tick()
    return world.score()


def refusals(desk: Desk) -> None:
    """Says what the world did not take from us so far: a quote that came after its 4.5 seconds is a request lost,
    and the score alone does not show it."""
    refused = getattr(desk, "refused", None)
    if refused:
        print("  the world refused: " + ", ".join(f"{reason} x{count}" for reason, count in refused.most_common(6)), flush=True)


def play_final(client: Client, world: World, params: Params = Params(), clock=None, on_send=None) -> None:
    """Plays the final, or a test final, from the live stream. It first rebuilds everything it knows from the
    world, so a desk that stopped can start again at any minute and go on: it keeps no file of its own.

    Events that arrive together are answered together: the desk handles every event that is already there,
    then sends its actions in one request. A request for a price leaves 4.5 real seconds, so the desk never
    holds an action longer than 0.2 seconds. `clock` reads the world minute (the lab passes its own)."""
    clock = clock or (lambda: client.final()["now"])
    history, snapshot = world.events(), world.snapshot()
    if snapshot["now"] >= snapshot["endsAt"]:
        return
    level = next((w["level"] for w in client.worlds() if w["worldId"] == world.id), 8)
    desk = new_desk(client, world, level, snapshot["now"], params)
    desk.relearn(history)
    desk.rejoin(snapshot, history)
    desk.send()
    held_since, clock_read = None, time.monotonic()
    for event in world.stream(after=history[-1]["seq"] if history else -1, idle=0.05):
        day = desk.now // kit.DAY
        if event is not None:
            desk.now = max(desk.now, event["at"])
            desk.handle(event)
            if desk.outbox and held_since is None:
                held_since = time.monotonic()
        elif time.monotonic() - clock_read >= 1.0:  # a quiet second: read the clock, fee schedules start from the current minute
            desk.now, clock_read = max(desk.now, clock()), time.monotonic()
        if event is None or (held_since is not None and time.monotonic() - held_since >= 0.2):
            desk.tick()
            if on_send:
                on_send(desk)
            desk.send()
            held_since = None
        if desk.now // kit.DAY > day:
            kit.report(kit.WEEKDAYS[day % 7], world.score())
            refusals(desk)
        if desk.now >= snapshot["endsAt"]:
            refusals(desk)
            return
