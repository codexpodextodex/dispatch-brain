"""Version 8 whose day cap rides the day, and nothing else: on a day whose level stands above its usual level the cap
on cars due per day rises with it (level ratio squared, at most 1.15 x; never in a careful week). A rich day is then
taken as the book's higher price AND as more cars; a lean or usual day is version 8's. See alt/ld_target_ride.py."""
from alt.ld_target_ride import make as base_make


def make(client, world, level, now, params):
    return base_make(client, world, level, now, params, gain=0.0, ride=2.0, ride_low=1.0, ride_high=1.15, ride_cap=1)
