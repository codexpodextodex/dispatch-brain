"""API line: see alt/ld_api_core.py. This desk: version 7 with one fault repaired. A pair that a driver gives back is
known as a pair again, so no new order takes one of its cars and leaves the other without a gig."""
from alt.ld_api_core import Parts, build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, Parts(repost=False, by_last=False, pair_fix=True))
