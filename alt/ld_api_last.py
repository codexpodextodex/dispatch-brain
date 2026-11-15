"""API line: see alt/ld_api_core.py. This desk: Parts() = a gig is posted again, without windows, in the minute after its
car's last pickup, and a late car's fees are version 7's late fees from that minute."""
from alt.ld_api_core import Parts, build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, Parts())
