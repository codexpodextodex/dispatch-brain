"""API line: see alt/ld_api_core.py. This desk: Parts(pair_fix=True) = version 7 with its two faults around late and returned
gigs repaired: a pair that a driver gives back stays a pair (no car is left without a gig), and a car whose last pickup
has passed is posted again at once, without windows, at a late car's fees (version 7 leaves it dead in the app until
the pickup site closes, and can pay the urgent ladder for it afterwards)."""
from alt.ld_api_core import Parts, build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, Parts(pair_fix=True))
