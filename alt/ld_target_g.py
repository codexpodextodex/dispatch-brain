"""Version 8 that takes a rich day as price and as cars, and leaves a lean day alone: on a day whose level stands above
its usual level the target for every due day and the day cap rise with it (level ratio squared, at most 1.15 x); the
cost of a car never goes under version 8's, and goes up (to 1.2 x at most) only where the cars won for a due day run
ahead of the path to that risen target. See alt/ld_target_ride.py."""
from alt.ld_target_ride import make as base_make


def make(client, world, level, now, params):
    return base_make(client, world, level, now, params, gain=1.0, aim=1.04, floor=1.0, ceiling=1.2, ride=2.0, ride_low=1.0, ride_high=1.15, ride_cap=1)
