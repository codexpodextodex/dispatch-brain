"""leaders/capgigs: version 8's cap on cars, unchanged, AND the cap on driver-hours (0.5497 a listed driver, the new car
by its own hours / 5.06); the larger of the two charges counts. See alt/ld_capgigs_more.py."""
from alt.ld_capgigs_more import build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, mode="both", cap=0.5497, ref=5.06)
