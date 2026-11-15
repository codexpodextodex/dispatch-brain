"""Plays our ranking runs of the current round at level 8: the five secret weeks that every team plays.

    python -m lab.round            # plays the runs that are left, one after the other, then shows the ranking
    python -m lab.round night_hold=1 early_hour=13   # the same with a candidate's settings on top of the defaults
                                                     # (after a stop, start it again with the same settings)

A ranking run counts whatever happens, cannot be played twice and cannot be revealed. So this script never
deletes one. If it is stopped in the middle of a week, start it again: it finds the unfinished run and goes on
from where the world stands, as the final runner does after a restart."""
from __future__ import annotations

import json
import sys
import time

from dispatch.desk import WAKE_ON
from dispatch.env import ROOT, load_env
from dispatch.play import new_desk
from dispatch.policy import Params
from spread.client import Client, SpreadError, Unreachable

LEVEL = 8


def play(client: Client, world, params: Params = Params()) -> dict:
    """Plays a world to its end from wherever it stands."""
    while True:
        try:
            history, snapshot = world.events(), world.snapshot()
            desk = new_desk(client, world, LEVEL, snapshot["now"], params)
            if history:  # an unfinished run: rebuild what we knew
                desk.relearn(history)
                desk.rejoin(snapshot, history)
                world._last_seq = history[-1]["seq"]
            while desk.now < snapshot["endsAt"]:
                actions, desk.outbox = desk.outbox, []
                step = world.advance(until=WAKE_ON, max=snapshot["endsAt"], actions=actions)
                desk.read_results(actions, step["results"])
                desk.now = step["now"]
                for event in step["events"]:
                    desk.handle(event)
                desk.tick()
            return world.score()
        except Unreachable as error:
            print(f"  server unreachable ({error}); going on in 30 seconds", flush=True)
            time.sleep(30)


def main() -> None:
    load_env()
    client = Client()
    log = ROOT / "data" / "rounds.jsonl"
    from lab.runs import KINDS, params_from, setting_of
    changed = {key: KINDS[key](value) for key, value in (arg.split("=", 1) for arg in sys.argv[1:])}
    params = params_from(changed)
    print(f"playing with {setting_of(changed)}", flush=True)
    while True:
        unfinished = [w for w in client.worlds() if w["boardRun"] is not None and w["level"] == LEVEL and not w["ended"]]
        if unfinished:
            world, summary = client.world(unfinished[0]["worldId"]), unfinished[0]
        else:
            try:
                world = client.create(level=LEVEL, board=True)
            except SpreadError as error:
                print(f"no further ranking run: {error}")
                break
            summary = next(w for w in client.worlds() if w["worldId"] == world.id)
        started = time.time()
        score = play(client, world, params)
        line = {"round": summary["season"], "run": summary["boardRun"], "worldId": world.id, "score": score, "at": time.strftime("%a %H:%M"), "setting": setting_of(changed)}
        with open(log, "a", encoding="utf-8") as file:
            file.write(json.dumps(line) + "\n")
        print(f"round {summary['season']} week {summary['boardRun']}: margin {score['marginCents'] / 100:>10,.2f}  won {score['wonOrders']:>4}  on time {score['onTimeShare']:6.1%}"
              f"  {'ranked' if score['ranked'] else 'NOT RANKED'}  ({time.time() - started:.0f}s)", flush=True)
    board = client.board(LEVEL)["current"]
    if board:
        full = [t for t in board["teams"] if t["played"] == 5]
        print(f"\n{board['name']}: {len([t for t in full if t['ranked']])} ranked teams")
        for t in full[:15]:
            mark = " <== us" if "moonshot" in t["name"].lower() else ""
            print(f"  {str(t['rank'] or '-'):>3} {t['name'][:26]:26} {t['marginCents'] / 100:>10,.0f}  on time {t['onTimeShare']:.1%}  {'ranked' if t['ranked'] else 'not ranked'}{mark}")
        ours = [t for t in board["teams"] if "moonshot" in t["name"].lower()]
        for t in ours:
            print(f"\nus: {t['name']}: played {t['played']}, rank {t['rank']}, margin {((t['marginCents'] or 0) / 100):,.0f}, runs: " + ", ".join(f"{r['marginCents'] / 100:,.0f} ({r['wonOrders']}, {r['onTimeShare']:.0%})" for r in t["runs"]))


if __name__ == "__main__":
    main()
