"""Version 7 with no day cap for cars whose last pickup falls on Monday or Tuesday (leaders/ swarm, line "capacity").

Why: the load on those days costs nothing that we can measure. The same car in two plays of one seed comes late
+0.5 ± 0.6 points more per 10 extra cars due that day and pays no higher fee, so one more car costs the others 0.01
± 0.06 typical fees there (0.10 to 0.12 on Thursday and Friday; python -X utf8 leaders/capacity/external.py), while
the cap charges 4% on average and up to 11% (leaders/capacity/charge.py). The cars a looser cap added for Tuesday
were late 1.7% (the day's own cars 2.5%). An early delivery also raises its dealer's accepted price for the rest of
the week. Everything from Wednesday on is version 7."""
from dataclasses import replace

from dispatch.desk import Desk
from dispatch.geo import DAY, Geo
from dispatch.policy import Params, Policy


class EarlyDaysFree(Policy):
    last_free_day = 1  # the last day of the week without a cap: 1 is Tuesday

    def cost(self, desk, request, option, last):
        if last // DAY <= self.last_free_day and self.p.day_cap:
            keep = self.p
            self.p = replace(keep, day_cap=0.0)
            try:
                return super().cost(desk, request, option, last)
            finally:
                self.p = keep
        return super().cost(desk, request, option, last)


def make(client, world, level: int, now: int, params: Params, last_free_day: int = 1):
    policy = EarlyDaysFree(params)
    policy.last_free_day = last_free_day
    desk = Desk(world, level, now, policy, Geo(client.map()))
    desk.meet(world.roster())
    return desk
