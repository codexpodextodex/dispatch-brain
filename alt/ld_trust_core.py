"""Dealer trust as something the desk builds on purpose (leaders/trust). Everything not named here is version 7.

The rule of level 8: a dealer accepts 1% more from us for each order we delivered to it on time, up to 25.
Version 7 collects that as it comes. This desk also prices what a delivery adds to the dealer's LATER prices:

    value of one more on-time order, counted by the end of day d
        = 1% x (what we sell that dealer a day) x (the working days from the morning after d until its
          count would be full anyway)

and takes `gain` of that value off the cost of a car that would be delivered on day d. So a car for a large
dealer early in the week, delivered today, is worth 20 to 35 euros more than its own margin; a car for a dealer
whose count is full, or for a dealer who asks twice a week, is worth what it was.

`notice`: for a car whose value is at least `least` cents, a short drive (`drive` hours) from a town with
`drivers` drivers near the pickup may be quoted with this many hours to find a driver (version 7 wants 14, or 4
for its "easy" cars). These are the cars that can be delivered the day they are asked for, the only ones that
raise a dealer's count before the next morning."""
from __future__ import annotations

from dataclasses import dataclass

from dispatch.desk import Desk
from dispatch.geo import DAY, HOUR, Geo
from dispatch.policy import Params, Policy


@dataclass(frozen=True)
class Build:
    gain: float = 0.75  # the share of a delivery's later value that comes off the car's cost; 0 is off
    notice: float = 0.0  # hours to find a driver that are enough for a valuable short car; 0 keeps version 7's rule
    drive: float = 3.0  # ... a short car: at most this many hours of driving
    drivers: int = 50  # ... from a town with at least this many drivers within 30 km
    least: float = 1000.0  # ... valuable: one more counted order is worth at least this many cents
    on_time: float = 0.97  # the chance that a car arrives on time and is counted


class TrustPolicy(Policy):
    def __init__(self, params: Params, build: Build):
        super().__init__(params)
        self.build = build

    def point_value(self, request: dict, day_delivered: int) -> float:
        """What one more on-time order, counted by the end of `day_delivered`, adds to this dealer's later prices, in cents."""
        dealer, now = request["dealerId"], request["arrivedAt"]
        flying = self.wins.get(dealer, 0) - self.done.get(dealer, 0)  # won, not delivered yet: they will count too
        missing = 25 - self.trusted.get(dealer, 0) - flying
        if missing <= 0:
            return 0.0
        worked = min(5.0, now // DAY + min(1.0, max(0.0, (now % DAY - 8 * HOUR) / (10 * HOUR))))  # working days gone
        a_day = max(self.wins.get(dealer, 0), 0.4 * self.asked.get(dealer, 0)) / max(0.25, worked)  # orders a day from this dealer
        full_at = worked + missing / max(0.5, a_day) + 1.0  # the working day on which the count is full anyway: a delivery follows its win by about a day
        counted_from = max(worked, min(day_delivered, 4) + 1.0)  # a delivery today counts from tomorrow morning
        days = max(0.0, min(5.0, full_at) - counted_from)
        price = self.sold[0] / self.sold[1] if self.sold[1] else 8500.0
        return 0.01 * price * a_day * days

    def find_hours(self, desk: Desk, request: dict) -> float:
        usual, b, leg = super().find_hours(desk, request), self.build, request["legs"][0]
        if (b.notice and usual > b.notice and len(request["legs"]) == 1 and not leg["pickup"]["privateAddress"] and not leg["delivery"]["privateAddress"]
                and desk.geo.drive(leg) <= b.drive * HOUR and desk.near.get(leg["pickup"]["placeId"], 0) >= b.drivers
                and self.point_value(request, request["arrivedAt"] // DAY) >= b.least):
            desk.stats["trust_short_notice"] += 1
            return b.notice
        return usual

    def cost(self, desk: Desk, request: dict, option: dict, last: int) -> float:
        cost = super().cost(desk, request, option, last)  # in list prices of this option
        if self.build.gain:
            value = self.build.gain * self.build.on_time * self.point_value(request, last // DAY)
            if value > 0:
                desk.stats["trust_valued"] += 1
                desk.stats["trust_value_cents"] += round(value)
                cost = max(0.3 * cost, cost - value / option["listPriceCents"])
        return cost


def make(client, world, level: int, now: int, params: Params, build: Build = Build()):
    policy = TrustPolicy(params, build)
    desk = Desk(world, level, now, policy, Geo(client.map()))
    desk.meet(world.roster())
    return desk
