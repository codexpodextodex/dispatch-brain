"""Version 8 with one change: a car due on Tuesday (nine in ten are won on Monday, when every driver is free and
nothing is due yet) costs 0.85 of version 8's cost, whatever the count. Every other due day is version 8's.
The plain form of alt/ld_target_c.py; see alt/ld_target_core.py (a target no day reaches keeps the cost at the floor)."""
from alt.ld_target_core import make as base_make


def make(client, world, level, now, params):
    return base_make(client, world, level, now, params, gain=1.0, rate={1: 9.9}, days=(1,), floor=0.85, ceiling=1.0, careful_floor=0.85)
