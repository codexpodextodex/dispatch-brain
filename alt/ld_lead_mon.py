"""Version 7 with a looser day cap for cars whose last pickup falls after Friday (leaders/ swarm, lead).

Why: cars due on the last Monday are the safest we carry (1.9% late on 60 weeks of version 6, the lowest of any
day, at the week's highest prices): drivers have Saturday and Monday for them and no new requests compete. But the
day cap (0.11 cars a listed driver) counts them like a Thursday: by Friday evening that day stands at 1.02 of the
cap on average and a new car for it costs 2.4 times its cost (python -X utf8 leaders/monday_cap.py).
`factor` multiplies the cap for those days only; 0 switches the cap off for them."""
from dataclasses import replace

from dispatch.desk import Desk
from dispatch.geo import DAY, Geo
from dispatch.policy import Params, Policy


class MondayCap(Policy):
    factor = 2.0

    def cost(self, desk, request, option, last):
        if last // DAY >= 5 and self.p.day_cap:
            keep = self.p
            self.p = replace(keep, day_cap=keep.day_cap * self.factor)
            try:
                return super().cost(desk, request, option, last)
            finally:
                self.p = keep
        return super().cost(desk, request, option, last)


def make(client, world, level: int, now: int, params: Params, factor: float = 2.0):
    policy = MondayCap(params)
    policy.factor = factor
    desk = Desk(world, level, now, policy, Geo(client.map()))
    desk.meet(world.roster())
    return desk
