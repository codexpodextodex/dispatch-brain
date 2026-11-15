"""Version 8, and on the day the price book reads as lean (the price-war day) a car costs 0.90 of the usual: fill.
See alt/ld_lean_core.py."""
from alt.ld_lean_core import make as base_make


def make(client, world, level, now, params):
    return base_make(client, world, level, now, params, lean_k=0.90)
