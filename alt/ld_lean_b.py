"""Version 8, and on the day the price book reads as lean (the price-war day) a car costs 1.10 of the usual: stand
aside. The mirror of alt/ld_lean_a.py; see alt/ld_lean_core.py."""
from alt.ld_lean_core import make as base_make


def make(client, world, level, now, params):
    return base_make(client, world, level, now, params, lean_k=1.10)
