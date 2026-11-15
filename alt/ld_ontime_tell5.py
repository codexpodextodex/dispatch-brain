"""On-time line: see alt/ld_ontime_w4.py. As ld_ontime_tell4 (the pickup window ends exactly at the last pickup, so the
only change for a driver is that a plan to come later must be announced), with the first release rule again: a driver who
announces a pickup after the last pickup is released whenever 2 hours or more remain. In the 12 weeks of ld_ontime_tell3,
11 of 12 released cars arrived on time, and 11 of 13 kept drivers delivered late, 8 of them after the site had closed (a
quarter of the price back, not a tenth): keeping a late driver is not the cheap option it looked."""
from alt.ld_ontime_w4 import Parts, build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, Parts(buffer=0, buffer_share=0.0, pair_buffer=0, fix=True, min_left=120, left_per_drive=0.0))
