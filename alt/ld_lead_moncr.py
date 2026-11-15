"""Version 7 with the last Monday treated by how the week is going (leaders/ swarm, lead).

alt/ld_lead_monc85 (no day cap and cost x 0.85 for cars due after Friday) won 34 more cars a week and +434 ± 407 on
the 12 screen weeks, but all of the gain came from ordinary weeks and the hard weeks paid for it (hold-10 -3.6
points of on-time share, fresh-9 under 90%). By Thursday the desk knows which kind of week it is in:
  - careful (the guard has tripped): version 7 as it is, cap and all;
  - going well (`Policy.relaxed`: at least 40 cars decided, late share under half the guard's line): no cap for
    cars due after Friday and their cost x `scale`;
  - in between: no cap for them (alt/ld_lead_monoff, +253 ± 85 on the same weeks)."""
from dataclasses import replace

from dispatch.desk import Desk
from dispatch.geo import DAY, Geo
from dispatch.policy import Params, Policy


class MondayByWeek(Policy):
    scale = 0.85

    def cost(self, desk, request, option, last):
        if last // DAY < 5 or (self.p.guard and self.careful(desk)):
            return super().cost(desk, request, option, last)
        keep = self.p
        self.p = replace(keep, day_cap=0.0)
        try:
            cost = super().cost(desk, request, option, last)
        finally:
            self.p = keep
        return self.scale * cost if self.relaxed(desk) else cost


def make(client, world, level: int, now: int, params: Params, scale: float = 0.85):
    policy = MondayByWeek(params)
    policy.scale = scale
    desk = Desk(world, level, now, policy, Geo(client.map()))
    desk.meet(world.roster())
    return desk
