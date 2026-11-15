"""A cost that follows TODAY's price level, on version 8 (leaders/ swarm, line "lean").

The rule, in one line: on a day the price book reads as lean (the price-war day), a car's cost is multiplied by
`lean_k`; on a day it reads as dear, by `dear_k`.

  today's level   `book.market`: the log of the market level the price book holds right now
  the reference   the mean of the book's level at the close of each earlier day of this week
  a lean day      from the 8th answer to today's quotes on: today's level stands `drop` (10%) or more under the
                  reference. On Monday there is no earlier day: Monday is lean when, 16 answers in, the book has
                  not risen 3% above the level it started the week at (a usual Monday lifts it 10% by then)
  a dear day      from the 8th answer on: today's level stands `rise` or more over the reference
  lean_k < 1      fill on the lean day: the drivers are the same as any day, the margin over the true cost is thin
  lean_k > 1      stand aside on the lean day: its cars are due tomorrow, when the dealers pay 20% more

The dealers' level is one level a day; one day a week it is 20% under the others and the next morning it is back
(leaders/lean/out/levels.txt). The book has taken half of an overnight jump after 16 answers and 80% by noon.
The rule reads only the book and the clock: `Desk.relearn` prices every past request again after a restart, which
rebuilds the closes and the count of today's answers exactly as they were.
With lean_k = dear_k = 1 the desk is version 8 to the cent (python -X utf8 -m leaders.lean.check)."""
from __future__ import annotations

import math

from dispatch.desk import Desk
from dispatch.geo import DAY, Geo
from dispatch.policy import Params, Policy


class LeanPolicy(Policy):
    lean_k = 1.0  # a car's cost on a lean day, times this; 1 is off
    dear_k = 1.0  # ... and on a dear day
    drop = 0.10  # a lean day: the book's level this far under the reference, in log price
    rise = 0.10  # a dear day: this far over it
    after = 8  # answers to today's quotes heard before the day is called
    monday = 1  # 1: the first day can be called lean, by the book's own starting level
    monday_after = 16  # ... after this many answers,
    monday_slack = 0.03  # ... when the book stands under its starting level plus this

    def __init__(self, params: Params = Params()):
        super().__init__(params)
        self.lean_day = None  # the working day of the last request
        self.closes: list[float] = []  # the book's level at the close of each earlier day
        self.heard_today = 0  # answers to today's quotes so far
        self.lean_start = math.log(params.start_level)

    def quote(self, desk, request):
        day = request["arrivedAt"] // DAY
        if day != self.lean_day:
            if self.lean_day is not None:
                self.closes.append(self.book.market)
            self.lean_day, self.heard_today = day, 0
        return super().quote(desk, request)

    def observe(self, desk, event):
        if event["kind"] in ("order_won", "order_lost"):
            rid = event["order"]["id"] if event["kind"] == "order_won" else event["requestId"]
            request = desk.requests.get(rid)
            if rid in self.quoted and request and request["arrivedAt"] // DAY == self.lean_day:
                self.heard_today += 1
        super().observe(desk, event)

    def day_kind(self) -> int:
        """-1 on a lean day, +1 on a dear day, 0 on any other day and while the day cannot be told."""
        if not self.closes:
            lean = self.monday and self.heard_today >= self.monday_after and self.book.market < self.lean_start + self.monday_slack
            return -1 if lean else 0
        if self.heard_today < self.after:
            return 0
        gap = self.book.market - sum(self.closes) / len(self.closes)
        return -1 if gap < -self.drop else 1 if gap > self.rise else 0

    def cost(self, desk, request, option, last):
        cost = super().cost(desk, request, option, last)
        if self.lean_k == 1.0 and self.dear_k == 1.0:
            return cost
        kind = self.day_kind()
        if kind:
            desk.stats[f"{'lean' if kind < 0 else 'dear'}_day{self.lean_day}"] += 1  # option prices made on a called day, for the lab's tables
        return cost * (self.lean_k if kind < 0 else self.dear_k if kind > 0 else 1.0)


def make(client, world, level: int, now: int, params: Params, **rule):
    policy = LeanPolicy(params)
    for name, value in rule.items():
        if not hasattr(LeanPolicy, name):
            raise ValueError(name)
        setattr(policy, name, value)
    desk = Desk(world, level, now, policy, Geo(client.map()))
    desk.meet(world.roster())
    return desk
