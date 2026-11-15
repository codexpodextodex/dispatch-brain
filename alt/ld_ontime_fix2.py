"""On-time line: see alt/ld_ontime_w2.py. This desk: Parts(window=False, act=False, fix=True)."""
from alt.ld_ontime_w2 import Parts, build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, Parts(window=False, act=False, fix=True))
