"""leaders/capgigs: version 8's count of cars (cap 0.1093), the new car charged by its own driver-hours / 5.06. See alt/ld_capgigs_more.py."""
from alt.ld_capgigs_more import build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, mode="own", cap=0.1093, ref=5.06)
