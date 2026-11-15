"""The ABSOLUTE form of alt/ld_lean_core.py: a lean day is called by the book's level itself, not against the week.

The rule, in one line: from the 8th answer to today's quotes on (the 16th on the first day), while the price book's
market level stands under `under` list prices, a car's cost is multiplied by `lean_k`.

Why a second form: the relative call (today against the mean close of the week's earlier days) finds the price-war
day but is silent in a week that is lean on every day, and those are the weeks where the desk carries fewest cars
(369 against 444 in dear weeks) with the freest drivers (0.895 typical fees paid, 2.3% late: leaders/lean/out/absolute.txt).
Reads only the book and the clock, like the first form. With lean_k = 1 the desk is version 8 to the cent."""
from __future__ import annotations

import math

from alt.ld_lean_core import LeanPolicy
from dispatch.desk import Desk
from dispatch.geo import Geo
from dispatch.policy import Params


class LowLevelPolicy(LeanPolicy):
    under = 1.30  # a lean day: the book's market level under this many list prices (a usual day closes at 1.42)

    def day_kind(self) -> int:
        heard_enough = self.heard_today >= (self.after if self.closes else self.monday_after)
        return -1 if heard_enough and self.book.market < math.log(self.under) else 0


def make(client, world, level: int, now: int, params: Params, **rule):
    policy = LowLevelPolicy(params)
    for name, value in rule.items():
        if not hasattr(LowLevelPolicy, name):
            raise ValueError(name)
        setattr(policy, name, value)
    desk = Desk(world, level, now, policy, Geo(client.map()))
    desk.meet(world.roster())
    return desk
