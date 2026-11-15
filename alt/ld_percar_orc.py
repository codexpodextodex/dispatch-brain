"""A MEASURING DESK, NOT FOR THE FINAL: version 7 that knows from the saved weeks of the same practice seed which
requests come late whoever carries them, and declines exactly those (leaders/ swarm, line "percar").

Why. Across all saved exact weeks of versions 6 and 7 of one seed (the same requests and drivers every time), 3.6% of
the requests hold 69% of the late arrivals: the same cars are late in most weeks they are carried in, under every
setting (leaders/percar/repeat_marks.py). Nothing known at the quote tells them apart (leaders/percar/doomed.py), so
this desk cannot be run on a new world. What it measures in real weeks: if a desk COULD tell them, would the week
really end near 99% on time, or do other cars come late in their place; and what are those points worth in margin
(refunds saved, dealers' trust kept) against the margin of the cars given up?

The table (leaders/percar/oracle/late.json) lists, for each practice seed, the requests late in at least 30% of the
exact weeks (four or more) that carried them. The seed is recognised by the driver list. On a seed without a table
the desk is version 7 to the cent."""
import json
import os

from dispatch.desk import Desk
from dispatch.geo import Geo
from dispatch.policy import Params, Policy

TABLE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "leaders", "percar", "oracle", "late.json")


class OraclePolicy(Policy):
    declined: frozenset = frozenset()

    def wanted(self, request: dict) -> bool:
        return request["id"] not in self.declined and super().wanted(request)


def make(client, world, level: int, now: int, params: Params, key: str = "late30"):
    policy = OraclePolicy(params)
    desk = Desk(world, level, now, policy, Geo(client.map()))
    roster = world.roster()
    desk.meet(roster)
    with open(TABLE, encoding="utf-8") as file:
        table = json.load(file)
    seed = table["by_roster"].get(roster[0]["id"].split("-")[0]) if roster else None
    policy.declined = frozenset(table["seeds"][seed][key]) if seed else frozenset()
    desk.stats["oracle_declines"] = len(policy.declined)
    return desk
