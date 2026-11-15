"""Version 8 with both halves of the mirror: on the day the price book reads as lean (the price-war day) a car costs
1.10 of the usual, on a day it reads as dear 0.95. See alt/ld_lean_core.py."""
from alt.ld_lean_core import make as base_make


def make(client, world, level, now, params):
    return base_make(client, world, level, now, params, lean_k=1.10, dear_k=0.95)
