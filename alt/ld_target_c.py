"""Version 8 that fills the first day: only cars due on Tuesday (nine in ten are won on Monday) are steered, towards
0.094 cars per listed driver (Wednesday's usual load, a fifth more than Tuesday's), by a lower cost only (down to
0.88 of version 8's, gain 2). Every other due day is version 8's. See alt/ld_target_core.py."""
from alt.ld_target_core import make as base_make


def make(client, world, level, now, params):
    return base_make(client, world, level, now, params, gain=2.0, rate={1: 0.094}, days=(1,), floor=0.88, ceiling=1.0)
