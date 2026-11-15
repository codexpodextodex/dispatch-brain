"""Version 8, and on a day the price book reads as dear (its level 10% or more over the mean close of the week's
earlier days) a car costs 1.10 of the usual: fewer, dearer cars when the day fills to its cap. The mirror of
alt/ld_lean_e.py, whose added cars paid 0.99 typical fees and came late 8.7%; see alt/ld_lean_core.py."""
from alt.ld_lean_core import make as base_make


def make(client, world, level, now, params):
    return base_make(client, world, level, now, params, dear_k=1.10)
