"""Version 8, and while the price book's level stands under 1.30 list prices (8 answers into the day, 16 on Monday)
a car costs 0.90 of the usual: fill when the dealers pay little, in a lean week as on a price-war day.
See alt/ld_lean_core2.py."""
from alt.ld_lean_core2 import make as base_make


def make(client, world, level, now, params):
    return base_make(client, world, level, now, params, under=1.30, lean_k=0.90)
