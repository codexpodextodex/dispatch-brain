"""leaders/capgigs: the day cap counts GIGS, not cars: a two-car gig is one (cap 0.0929 gigs a listed driver, the same
mean charge as version 8's 0.11 cars under pair holding). Play it with pair_hold=4 and compare with pair_hold=4 alone:
    --set design=ld_capgigs_gigs pair_hold=4.0        See alt/ld_capgigs_more.py."""
from alt.ld_capgigs_more import build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, mode="gigs", cap=0.0929)
