"""Runs the desk.

    python -m dispatch                 # one level 8 practice week on a random seed
    python -m dispatch --seed lab-1    # the same week every time
    python -m dispatch --board         # the next ranking run: it counts in the practice rankings
    python -m dispatch --final         # the final, or a test final, from the live stream; start it again if it stops
"""
from __future__ import annotations

import argparse
import sys
import time

from spread import starter as kit
from spread.client import Client, SpreadError, Unreachable

from .env import load_env
from .play import new_desk, play_final, play_practice


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--level", type=int, choices=range(1, 9), default=8)
    parser.add_argument("--seed")
    parser.add_argument("--board", action="store_true")
    parser.add_argument("--final", action="store_true")
    args = parser.parse_args()
    load_env()
    try:
        client = Client()
        if args.final:
            world = None
            while True:  # a server restart drops every connection: rebuild from the world and go on
                try:
                    if world is None:
                        world = kit.next_final(client)
                        print(f"Final world {world.id}.", flush=True)
                    play_final(client, world)
                    score = world.score()
                    break
                except Unreachable as error:
                    print(f"spread: {error}. Trying again in 5 seconds.", file=sys.stderr, flush=True)
                    time.sleep(5)
        else:
            world = client.create(level=args.level, seed=args.seed, board=args.board)
            print(f"{'Ranking run' if args.board else 'Practice world'} {world.id}, level {args.level}.", flush=True)
            try:
                score = play_practice(world, new_desk(client, world, args.level, world.snapshot()["now"]))
            except BaseException:
                if not args.board:  # a ranking run that is deleted still counts; leave it to be played again
                    try:
                        world.delete()
                    except SpreadError:
                        pass
                raise
        kit.report("End", score)
        print("Ranked." if score["ranked"] else "Not ranked.")
    except SpreadError as error:
        sys.exit(f"spread: {error}")
    except KeyboardInterrupt:
        sys.exit("Stopped. A final world keeps running without the desk: start it again with --final.")


if __name__ == "__main__":
    main()
