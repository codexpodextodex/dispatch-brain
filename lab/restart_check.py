"""Does the desk survive a restart? Plays one practice week twice: once straight through, once "killed" at
several minutes of the week and started again from nothing but the world, as the final runner does.

    python -m lab.restart_check                # level 8, seed lab-1, restarts on Tue 13:00, Thu 10:00, Sat 12:00
    python -m lab.restart_check --seed hold-3
    python -m lab.restart_check --set pair_safe=1 guard=0.08     # a candidate's settings on top of the defaults

After each restart the new desk rebuilds everything it knows from the world's events and snapshot
(Desk.relearn and Desk.rejoin), exactly as `python -m dispatch --final` does when it starts. The check passes
when the restarted week is ranked and its margin is close to the straight week's. They are not equal to the
cent: the price book is relearned from the answers to past quotes, and an order posted again gets a new fee
schedule from the current minute."""
from __future__ import annotations

import argparse

from dispatch.desk import WAKE_ON
from dispatch.env import load_env
from dispatch.play import new_desk, play_practice
from dispatch.policy import Params
from lab.runs import KINDS, create, own, params_from
from spread.client import Client

HOUR, DAY = 60, 24 * 60


def play_with_restarts(client: Client, level: int, seed: str, restarts: list[int], params: Params = Params()) -> dict:
    world = create(client, level, seed)
    marker = own(world)
    try:
        ends_at = world.snapshot()["endsAt"]
        desk = new_desk(client, world, level, world.snapshot()["now"], params)
        for stop in sorted(restarts) + [ends_at]:
            while desk.now < stop:  # the practice loop of dispatch/play.py, up to the minute of the "kill"
                actions, desk.outbox = desk.outbox, []
                step = world.advance(until=WAKE_ON, max=stop, actions=actions)
                desk.read_results(actions, step["results"])
                desk.now = step["now"]
                for event in step["events"]:
                    desk.handle(event)
                desk.tick()  # as the practice loop and the final runner do after every batch of events
            if stop < ends_at:  # the desk dies here, with its outbox; a new one starts from the world alone
                history, snapshot = world.events(), world.snapshot()
                desk = new_desk(client, world, level, snapshot["now"], params)
                desk.relearn(history)
                desk.rejoin(snapshot, history)
                world._last_seq = history[-1]["seq"] if history else -1
        return world.score()
    except BaseException:
        world.delete()
        raise
    finally:
        marker.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--level", type=int, default=8)
    parser.add_argument("--seed", default="lab-1")
    parser.add_argument("--set", nargs="*", default=[], metavar="NAME=VALUE", help="policy settings on top of the defaults")
    args = parser.parse_args()
    params = params_from({key: KINDS[key](value) for key, value in (item.split("=", 1) for item in args.set)})
    load_env()
    client = Client()
    restarts = [1 * DAY + 13 * HOUR, 3 * DAY + 10 * HOUR, 5 * DAY + 12 * HOUR]
    world = create(client, args.level, args.seed)
    marker = own(world)
    try:
        straight = play_practice(world, new_desk(client, world, args.level, world.snapshot()["now"], params))
    finally:
        marker.unlink(missing_ok=True)
    restarted = play_with_restarts(client, args.level, args.seed, restarts, params)
    for label, score in (("straight through", straight), ("three restarts", restarted)):
        print(f"{label:<17} margin {score['marginCents'] / 100:>10,.2f}  won {score['wonOrders']:>4}  on time {score['onTimeShare']:6.1%}  {'ranked' if score['ranked'] else 'NOT RANKED'}")
    gap = abs(restarted["marginCents"] - straight["marginCents"]) / max(1, abs(straight["marginCents"]))
    ok = restarted["ranked"] >= straight["ranked"] and gap < 0.15
    print("PASS" if ok else "FAIL", f"(margin differs by {gap:.1%})")


if __name__ == "__main__":
    main()
