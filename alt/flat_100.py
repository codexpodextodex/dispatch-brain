"""Design B, one fee of 1.00 typical fees (see alt/flatfee.py)."""
from alt.flatfee import Flat, make as flat_make


def make(client, world, level, now, params):
    return flat_make(client, world, level, now, params, Flat(fee=1.00))
