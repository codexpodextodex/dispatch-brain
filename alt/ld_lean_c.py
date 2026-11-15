"""Version 8, and on a day the price book reads as dear (its level 10% or more over the mean close of the week's
earlier days: mostly the days after the price-war day) a car costs 0.95 of the usual: take more when the dealers pay
more. See alt/ld_lean_core.py."""
from alt.ld_lean_core import make as base_make


def make(client, world, level, now, params):
    return base_make(client, world, level, now, params, dear_k=0.95)
