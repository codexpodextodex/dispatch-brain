"""Design B, one fee by kind of car: 0.85, or 1.05 to a town with few drivers; one raise to 1.20 (see alt/flatfee.py)."""
from alt.flatfee import Flat, make as flat_make


def make(client, world, level, now, params):
    return flat_make(client, world, level, now, params, Flat(fee=0.85, top=1.20, thin=1.05))
