"""Version 7 with a wall per due day in place of the one day cap (leaders/ swarm, line "capacity").

What the saved weeks say (leaders/capacity/REPORT.md):
  - The cap counts the LIVE cars of a day (won, not yet delivered), not all cars won for it. On that count version 7
    peaks at 0.064 / 0.074 / 0.078 / 0.088 / 0.075 cars a listed driver for last pickups on Tue / Wed / Thu / Fri /
    the last Monday, so the cap (0.11, power 4) charges 4 to 11% on average and never more than about 40%.
  - The last Monday has a real limit, and it is on this live count: its cars come late 1.1% while the count stays
    under 0.08 a driver, 2.3% at 0.08 to 0.10, 5.6% at 0.10 to 0.12 and 12 to 13% above (96 week-runs: version 7 and
    the lead's Monday designs). Under 0.09 there is nothing to charge for; from 0.10 the desk must stop.
  - At the same count the Monday cars come late three to five times as often when that day's own gigs are slow to
    find drivers (of the Monday cars won 6 hours ago or more, the share without a driver: under 10% -> 1.4% late,
    10 to 25% -> 6.5%, 25 to 50% -> 9.4%), and in a week the guard calls careful.

So for cars due after Friday: the cost times `scale`, and a steep wall at `wall` live cars a listed driver
(cost x (1 + (count / wall)^`power`)); the wall moves in, by up to a quarter in all, when that day's cars are slow
to find drivers and (by `careful_wall`) in a careful week. Days up to Friday keep version 7's cap unless
`tue_cap` or `late_week` say otherwise."""
from dataclasses import replace

from dispatch.desk import Desk
from dispatch.geo import DAY, HOUR, Geo
from dispatch.policy import Params, Policy


class DayWalls(Policy):
    scale = 0.85  # the cost of a car due after Friday, against version 7's
    wall = 0.105  # live cars due after Friday per listed driver at which a new one costs double
    power = 8.0
    flow = 1  # 1: the wall moves in while that day's cars are slow to find drivers:
    flow_from = 0.2  # ... from this share of them waiting,
    flow_slope = 1.0  # ... by this much of the wall for each further 100% waiting,
    floor = 0.75  # ... and with the careful week never under this share of the wall
    careful_wall = 0.85  # the wall in a careful week, as a share
    tue_cap = 1.0  # the cap for last pickups up to Tuesday, as a multiple of version 7's (0 = none)
    late_week = 1.0  # the cap for last pickups on Thursday and Friday in a careful week, as a multiple of version 7's

    def __init__(self, params: Params = Params()):
        super().__init__(params)
        self.won_at: dict[str, int] = {}

    def observe(self, desk, event):
        if event["kind"] == "order_won":
            self.won_at[event["order"]["id"]] = event["at"]
        super().observe(desk, event)

    def waiting(self, desk) -> float:
        """Of our cars due after Friday that we won at least 6 hours ago, the share that has no driver. 0 with
        fewer than five such cars."""
        old = [order for order_id, order in desk.orders.items() if None in order["deliveredAt"]
               and desk.last_pickup.get(order_id, order["lastPickupAt"]) // DAY >= 5 and self.won_at.get(order_id, desk.now) <= desk.now - 6 * HOUR]
        if len(old) < 5:
            return 0.0
        return sum(1 for order in old if not any(gig in desk.booked for gig in desk.gigs_of(order["id"]))) / len(old)

    def plain_cost(self, desk, request, option, last, cap: float) -> float:
        keep = self.p
        self.p = replace(keep, day_cap=cap)
        try:
            return super().cost(desk, request, option, last)
        finally:
            self.p = keep

    def cost(self, desk, request, option, last):
        p, day = self.p, last // DAY
        if not p.day_cap:
            return super().cost(desk, request, option, last)
        careful = bool(p.guard) and self.careful(desk)
        if day < 5:
            factor = self.tue_cap if day <= 1 else self.late_week if day >= 3 and careful else 1.0
            return super().cost(desk, request, option, last) if factor == 1.0 else self.plain_cost(desk, request, option, last, p.day_cap * factor)
        cost = self.scale * self.plain_cost(desk, request, option, last, 0.0)
        squeeze = self.careful_wall if careful else 1.0
        if self.flow:
            squeeze *= 1.0 - self.flow_slope * max(0.0, self.waiting(desk) - self.flow_from)
        wall = self.wall * max(self.floor, squeeze)  # never under the floor: at that count version 7's Monday cars were on time in every week
        due = sum(desk.due(d) for d in (5, 6, 7)) + sum(hope for hoped_day, hope in self.hoped.values() if hoped_day >= 5)
        return cost * (1 + (due / (wall * desk.drivers)) ** self.power)


def make(client, world, level: int, now: int, params: Params, **settings):
    policy = DayWalls(params)
    for name, value in settings.items():
        assert hasattr(DayWalls, name), name
        setattr(policy, name, value)
    desk = Desk(world, level, now, policy, Geo(client.map()))
    desk.meet(world.roster())
    return desk
