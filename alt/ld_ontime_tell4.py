"""On-time line: see alt/ld_ontime_w4.py. This desk: Parts(buffer=0, buffer_share=0.0, pair_buffer=0, fix=True)."""
from alt.ld_ontime_w4 import Parts, build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, Parts(buffer=0, buffer_share=0.0, pair_buffer=0, fix=True))
