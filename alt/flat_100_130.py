"""Design B, 1.00, one raise to 1.30 when drivers plan the day (see alt/flatfee.py)."""
from alt.flatfee import Flat, make as flat_make


def make(client, world, level, now, params):
    return flat_make(client, world, level, now, params, Flat(fee=1.00, top=1.30))
