"""On-time line: see alt/ld_ontime_w3.py. This desk only LISTENS: the pickup window ends exactly at the last pickup (no
buffer; a pair's first pickup at the pair's last start), so nothing changes for a driver who comes in time, and one who
plans to come later must say so (`driver_late`); then the release rule of version 3. With the pairing fix."""
from alt.ld_ontime_w3 import Parts, build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, Parts(buffer=0, buffer_share=0.0, pair_buffer=0, fix=True))
