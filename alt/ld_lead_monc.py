"""Version 7 with no day cap for cars whose last pickup falls after Friday, and their cost scaled by `scale`
(leaders/ swarm, lead). Follows alt/ld_lead_mon.py: with the cap off for those days version 7 gained +253 ± 85 on
the 12 screen weeks but only 8 cars. This asks whether winning MORE cars for the last Monday on purpose pays:
they are the safest and best-paid cars of the week (python -X utf8 leaders/day_load.py)."""
from dataclasses import replace

from dispatch.desk import Desk
from dispatch.geo import DAY, Geo
from dispatch.policy import Params, Policy


class MondayCost(Policy):
    scale = 0.85

    def cost(self, desk, request, option, last):
        if last // DAY >= 5:
            keep = self.p
            self.p = replace(keep, day_cap=0.0)
            try:
                return self.scale * super().cost(desk, request, option, last)
            finally:
                self.p = keep
        return super().cost(desk, request, option, last)


def make(client, world, level: int, now: int, params: Params, scale: float = 0.85):
    policy = MondayCost(params)
    policy.scale = scale
    desk = Desk(world, level, now, policy, Geo(client.map()))
    desk.meet(world.roster())
    return desk
