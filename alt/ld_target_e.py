"""Version 8 with a volume target that rides the day: the flat target of alt/ld_target_a.py (1.04 x the usual cars
per listed driver, gain 1, cost between 0.93 and 1.2 of version 8's) times the day's level over its usual level,
squared, between 0.85 and 1.15; on a rich day the day cap rises with it. See alt/ld_target_ride.py."""
from alt.ld_target_ride import make as base_make


def make(client, world, level, now, params):
    return base_make(client, world, level, now, params, gain=1.0, aim=1.04, floor=0.93, ceiling=1.2, ride=2.0, ride_low=0.85, ride_high=1.15, ride_cap=1)
