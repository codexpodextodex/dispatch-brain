"""leaders/capgigs: the day's load in driver-hours (cap 0.5503 a listed driver), every new car charged alike. See alt/ld_capgigs_core.py."""
from alt.ld_capgigs_core import build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, mode="flat", cap=0.5503)
