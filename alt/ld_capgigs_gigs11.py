"""leaders/capgigs: the day cap counts GIGS at version 8's own number: 0.11 gigs a listed driver, a two-car gig is one.
A LOOSER cap by the pairs (15% of the cars due at a quote under pair holding): first order +29 cars a week
(leaders/capgigs/out/replay_gigs.txt). The same-charge form is alt/ld_capgigs_gigs.py. See alt/ld_capgigs_more.py."""
from alt.ld_capgigs_more import build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, mode="gigs", cap=0.11)
