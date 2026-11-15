"""The volume target that rides the day (leaders/ swarm, line "target"; the flat target is alt/ld_target_core.py).

A rich day is a day on which the dealers accept more than usual: the price book's market level stands above what it
usually is at this hour of this request day (`USUAL_LEVEL`: version 8's 60 saved weeks; by 10:00 the level tells the
rest of the day with a correlation of 0.73 to 0.91, by noon 0.93 to 0.95). On such a day the target for every due day
rises with the level (level ratio ^ `ride`, at most `ride_high`: the upper third of version 8's weeks carried 1.12
to 1.23 x the usual cars a listed driver at the usual fees and lateness), and so does the day cap, so the day is taken
as a higher price (the book's own doing) AND as more cars. On a lean day the target falls with the level (to
`ride_low` at least): fewer cars, each priced over a higher cost. In a week the guard calls careful the cap stays
version 8's and the cost never goes under version 8's.

State: the book's level (relearned from the answers after a restart, as version 8's prices are), the desk's orders,
the open quotes and the clock. With `ride` 0 this is the flat target; with `gain` 0 as well it is version 8."""
import math
from dataclasses import replace

from alt.ld_target_core import PATH, USUAL, TargetPolicy, group_of, path_share
from dispatch.desk import Desk
from dispatch.geo import DAY, HOUR, Geo
from dispatch.policy import Params, Policy

# The book's market level at version 8's real quotes, the mean of 60 weeks by request day (Monday first) and full
# hour from 08:00 to 18:00 (leaders/target/levels.py).
USUAL_LEVEL = [
    [1.162, 1.192, 1.229, 1.242, 1.245, 1.258, 1.256, 1.266, 1.283, 1.27, 1.316],
    [1.359, 1.341, 1.369, 1.38, 1.377, 1.377, 1.396, 1.409, 1.412, 1.427, 1.451],
    [1.419, 1.438, 1.44, 1.448, 1.459, 1.473, 1.462, 1.454, 1.461, 1.479, 1.48],
    [1.495, 1.467, 1.436, 1.438, 1.443, 1.462, 1.416, 1.421, 1.433, 1.434, 1.458],
    [1.441, 1.419, 1.425, 1.403, 1.414, 1.427, 1.428, 1.438, 1.464, 1.455, 1.455],
]


def usual_level(minute: int) -> float:
    row = USUAL_LEVEL[min(4, minute // DAY)]
    hour = min(18.0, max(8.0, (minute % DAY) / HOUR))
    k = min(9, int(hour) - 8)
    return row[k] + (row[k + 1] - row[k]) * (hour - 8 - k)


class RidePolicy(TargetPolicy):
    ride = 0.0  # how steeply the target follows the day's level; 0 is the flat target
    ride_low = 0.85  # the target on the leanest day, as a share of the flat one
    ride_high = 1.15  # ... and on the richest
    ride_cap = 1  # 1: on a rich day the day cap rises with the target

    def richness(self, request) -> float:
        """The factor on today's targets: over 1 on a day whose level stands above the usual."""
        if not self.ride:
            return 1.0
        return min(self.ride_high, max(self.ride_low, (math.exp(self.book.market) / usual_level(request["arrivedAt"])) ** self.ride))

    def ratio(self, desk, request, day: int) -> float:
        group = group_of(day)
        won = sum(1 for order_id, order in desk.orders.items() if group_of(desk.last_pickup.get(order_id, order["lastPickupAt"]) // DAY) == group)
        won += sum(hope for hoped_day, hope in self.hoped.values() if group_of(hoped_day) == group)
        target = self.rate.get(group, self.aim * USUAL[group]) * desk.drivers * self.richness(request)
        return (won + self.prior) / (target * path_share(group, request["arrivedAt"]) + self.prior)

    def cost(self, desk, request, option, last):
        rich = self.richness(request)
        if self.ride_cap and rich > 1.0 and self.p.day_cap and not (self.p.guard and self.careful(desk)):
            keep = self.p
            self.p = replace(keep, day_cap=keep.day_cap * rich)
            try:
                base = Policy.cost(self, desk, request, option, last)
            finally:
                self.p = keep
        else:
            base = Policy.cost(self, desk, request, option, last)
        return base * self.steer(desk, request, last)


def make(client, world, level: int, now: int, params: Params, **settings):
    policy = RidePolicy(params)
    for name, value in settings.items():
        assert hasattr(RidePolicy, name), name
        setattr(policy, name, value)
    desk = Desk(world, level, now, policy, Geo(client.map()))
    desk.meet(world.roster())
    return desk
