"""Version 8 with a volume target for each due day (leaders/ swarm, line "target").

Version 8's price follows the dealers' level, so its volume does too: about 377 cars in a lean-price week and 435 in a
dear one, on the same drivers. This desk wants `rate[d]` cars per listed driver due on day d (the day of the last
pickup), knows how the cars of a due day usually accumulate over the request hours (`PATH`: the share of version 8's
cars for that day won by each hour, 60 saved weeks: the request stream is the same size every week), and steers:

    ratio = (cars won for d so far + open quotes' chances + `prior`) / (target x path share so far + `prior`)
    cost of a car due d  =  version 8's cost  x  ratio ^ `gain`,  kept between `floor` and `ceiling`

Behind the path the cost comes down towards what a car costs when drivers are free; ahead of it the cost goes up, so
a rich day is taken as price from the morning and not only when the day cap bites. The cap, the guard and every rule
on the driver side are version 8's. In a week the guard calls careful the cost never goes under version 8's.

Restart-safe by construction: the ratio is read from the desk's orders (all cars won, delivered or not), the open
quotes and the clock of the request: nothing is remembered. With `gain` 0 every quote is version 8's."""
from dispatch.desk import Desk
from dispatch.geo import DAY, HOUR, Geo
from dispatch.policy import Params, Policy

# The share of a due day's cars that version 8 has won by each full hour from 08:00 to 18:00 of the five request days
# (leaders/target/timing.py; 60 weeks). Key 7: every last pickup after Friday.
PATH = {
    1: [[0.0, 0.026, 0.122, 0.218, 0.29, 0.37, 0.461, 0.535, 0.646, 0.742, 0.825], [0.881, 0.883, 0.899, 0.918, 0.941, 0.959, 0.978, 0.993, 0.996, 0.999, 1.0]],
    2: [[0.0, 0.003, 0.014, 0.03, 0.046, 0.058, 0.074, 0.088, 0.107, 0.122, 0.147], [0.165, 0.176, 0.248, 0.33, 0.408, 0.476, 0.555, 0.638, 0.731, 0.803, 0.882],
        [0.908, 0.909, 0.922, 0.938, 0.953, 0.975, 0.989, 0.996, 0.998, 0.999, 1.0]],
    3: [[0.0, 0.001, 0.009, 0.015, 0.023, 0.029, 0.036, 0.043, 0.056, 0.068, 0.078], [0.083, 0.085, 0.098, 0.112, 0.126, 0.14, 0.155, 0.171, 0.196, 0.219, 0.244],
        [0.255, 0.265, 0.339, 0.41, 0.48, 0.546, 0.612, 0.672, 0.748, 0.81, 0.874], [0.903, 0.906, 0.92, 0.936, 0.956, 0.972, 0.987, 0.994, 0.996, 0.999, 1.0]],
    4: [[0.0, 0.0, 0.004, 0.008, 0.012, 0.016, 0.019, 0.023, 0.027, 0.032, 0.035], [0.037, 0.038, 0.046, 0.056, 0.067, 0.076, 0.087, 0.099, 0.111, 0.127, 0.135],
        [0.138, 0.14, 0.16, 0.178, 0.198, 0.227, 0.25, 0.274, 0.294, 0.321, 0.348], [0.365, 0.373, 0.436, 0.495, 0.558, 0.613, 0.658, 0.7, 0.751, 0.797, 0.838],
        [0.854, 0.858, 0.881, 0.899, 0.924, 0.953, 0.977, 0.991, 0.994, 0.997, 1.0]],
    7: [[0.0, 0.0, 0.0, 0.001, 0.002, 0.003, 0.004, 0.005, 0.005, 0.005, 0.006], [0.006, 0.007, 0.009, 0.013, 0.02, 0.025, 0.03, 0.032, 0.035, 0.038, 0.04],
        [0.043, 0.044, 0.051, 0.061, 0.071, 0.08, 0.086, 0.096, 0.111, 0.127, 0.141], [0.146, 0.148, 0.174, 0.195, 0.216, 0.242, 0.276, 0.308, 0.34, 0.38, 0.419],
        [0.438, 0.444, 0.5, 0.547, 0.596, 0.642, 0.69, 0.749, 0.847, 0.921, 1.0]],
}
# Version 8's own cars per listed driver by due day, the mean of 60 weeks: the targets are multiples of it.
USUAL = {1: 0.079, 2: 0.094, 3: 0.102, 4: 0.121, 7: 0.112}


def path_share(group: int, minute: int) -> float:
    """The usual share of a due day's cars that is won by `minute` of the week."""
    rows = PATH[group]
    day, hour = minute // DAY, (minute % DAY) / HOUR
    if day >= len(rows):
        return 1.0
    row = rows[day]
    if hour <= 8:
        return row[0]
    if hour >= 18:  # the few evening requests: on to the next morning's share by 21:00
        after = rows[day + 1][0] if day + 1 < len(rows) else 1.0
        return row[-1] + (after - row[-1]) * min(1.0, (hour - 18) / 3)
    k = int(hour) - 8
    return row[k] + (row[k + 1] - row[k]) * (hour - 8 - k)


def group_of(day: int) -> int:
    """The due day a car counts for: every last pickup after Friday is one day."""
    return 7 if day >= 5 else day


class TargetPolicy(Policy):
    gain = 0.0  # how hard the cost follows the ratio; 0 is version 8
    aim = 1.0  # the target for every due day, as a multiple of version 8's usual cars per listed driver
    rate: dict = {}  # ... or a target per due day in cars per listed driver, where given
    prior = 8.0  # cars: early in a day's path a few cars more or less say little
    floor = 0.93  # the cost never goes under this share of version 8's,
    ceiling = 1.2  # ... or over this
    careful_floor = 1.0  # the floor in a week the guard calls careful
    days = (1, 2, 3, 4, 7)  # the due days steered (7: every last pickup after Friday)

    def ratio(self, desk, request, day: int) -> float:
        """How far the cars won for a due day run ahead of (over 1) or behind (under 1) the path to its target."""
        group = group_of(day)
        won = sum(1 for order_id, order in desk.orders.items() if group_of(desk.last_pickup.get(order_id, order["lastPickupAt"]) // DAY) == group)
        won += sum(hope for hoped_day, hope in self.hoped.values() if group_of(hoped_day) == group)
        target = self.rate.get(group, self.aim * USUAL[group]) * desk.drivers
        return (won + self.prior) / (target * path_share(group, request["arrivedAt"]) + self.prior)

    def steer(self, desk, request, last: int) -> float:
        day = last // DAY
        if not self.gain or group_of(day) not in self.days:
            return 1.0
        factor = self.ratio(desk, request, day) ** self.gain
        floor = self.careful_floor if self.p.guard and self.careful(desk) else self.floor
        return min(self.ceiling, max(min(floor, 1.0) if factor < 1 else 1.0, factor))

    def cost(self, desk, request, option, last):
        return super().cost(desk, request, option, last) * self.steer(desk, request, last)


def make(client, world, level: int, now: int, params: Params, **settings):
    policy = TargetPolicy(params)
    for name, value in settings.items():
        assert hasattr(TargetPolicy, name), name
        setattr(policy, name, value)
    desk = Desk(world, level, now, policy, Geo(client.map()))
    desk.meet(world.roster())
    return desk
