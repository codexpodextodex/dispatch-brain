"""Version 7 with one change in the price: a place on a full day never costs a car more than `limit` euros
(leaders/ swarm, line "percar": leaders/percar/REPORT.md).

Why. Version 7 slows its wins as a day fills up by multiplying a new car's cost by 1 + load, where
load = (cars due that day / (0.11 x drivers)) ** 4. The charge is the car's OWN cost again: at load 0.5 a
40-minute car pays 14 euros for its place on that day and a 6-hour car 120, though each takes one place. Measured on
version 7's 60 weeks (leaders/percar/cap_state.py): the cap adds 3 euros to the cost of a car under an hour and
23 to a car over six hours on average, 12 and 98 on the tenth of quotes where the day is filling; there the desk
still wins 36% of the short cars (18 euros of margin each) and 8% of the longest (120 each).

The rule. A desk that fills a limited number of places with the most margin charges for the place, not for the size
of the car. The charge stays the car's own cost x load for small cars and stops at `limit` x load: no car pays
more for its place than an average car does (80 euros is the load-weighted average cost the cap multiplies today).
Offline replay against every request's measured limit (leaders/percar/slot_eval.py), 60 weeks: +480 a week with 6
more cars (drives over two hours), the same on lab, hold and fresh weeks; drivers and lateness are not in that replay.

With `limit` very large this is version 7 to the cent."""
from dataclasses import replace

from dispatch.desk import Desk
from dispatch.geo import DAY, Geo
from dispatch.policy import Params, Policy


class SlotPolicy(Policy):
    limit = 8000  # cents: the most a car pays for its place when the day is exactly at the cap

    def cost(self, desk, request, option, last):
        p = self.p
        if not p.day_cap:
            return super().cost(desk, request, option, last)
        self.p = replace(p, day_cap=0.0, strain=0.0)
        try:
            own = super().cost(desk, request, option, last)  # the car's cost without the cap, in list prices of the option
        finally:
            self.p = p
        day, leg = last // DAY, request["legs"][0]
        due = desk.due(day, thin_only=bool(p.cap_thin)) + sum(hope for hoped_day, hope in self.hoped.values() if hoped_day == day)
        load = self.cap_weight(desk, leg) * (due / (p.day_cap * desk.drivers)) ** p.cap_power
        capped = min(own, self.limit / option["listPriceCents"])
        if capped < own:
            desk.stats["slot_capped"] += 1
        cost = own + load * capped
        if p.strain:
            cost *= 1 + p.strain * max(0.0, desk.strain() - 0.03)
        return cost


def make(client, world, level: int, now: int, params: Params, limit: int = 8000):
    policy = SlotPolicy(params)
    policy.limit = limit
    desk = Desk(world, level, now, policy, Geo(client.map()))
    desk.meet(world.roster())
    return desk
