"""On-time line: see alt/ld_ontime_w.py. This desk: Parts(window=False, act=False, select=True)."""
from alt.ld_ontime_w import Parts, build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, Parts(window=False, act=False, select=True))
