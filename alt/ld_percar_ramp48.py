"""Version 7 with the guard rising evenly from 4% to 8% instead of switching at 6% (alt/ld_percar_ramp.py)."""
from alt.ld_percar_ramp import make as base_make


def make(client, world, level, now, params):
    return base_make(client, world, level, now, params, low=0.04, high=0.08)
