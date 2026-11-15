"""Design B, 0.90, one raise to 1.20 when drivers plan the day (see alt/flatfee.py)."""
from alt.flatfee import Flat, make as flat_make


def make(client, world, level, now, params):
    return flat_make(client, world, level, now, params, Flat(fee=0.90, top=1.20))
