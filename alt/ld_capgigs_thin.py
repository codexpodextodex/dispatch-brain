"""leaders/capgigs: version 8's count of cars (cap 0.1112); a car with 4 hours of road or more, or with fewer than 150
drivers living within 60 km of its ends, is charged twice the cap's term, any other car half. See alt/ld_capgigs_more.py."""
from alt.ld_capgigs_more import build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, mode="thin", cap=0.1112, ref=2.0, cap_long=0.5)
