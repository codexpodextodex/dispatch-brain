"""Version 8 with both halves that the car-by-car reading supports: on the day the price book reads as lean a car
costs 0.90 of the usual (alt/ld_lean_a.py), on a day it reads as dear 1.10 (alt/ld_lean_f.py).
See alt/ld_lean_core.py."""
from alt.ld_lean_core import make as base_make


def make(client, world, level, now, params):
    return base_make(client, world, level, now, params, lean_k=0.90, dear_k=1.10)
