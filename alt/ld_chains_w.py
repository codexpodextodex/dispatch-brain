"""leaders/chains control: version 7 woken on the same events as alt/ld_chains_a.py, sending no offer."""
from alt.ld_chains_core import Chain, make as core_make


def make(client, world, level, now, params):
    return core_make(client, world, level, now, params, Chain(on_post=False, on_book=False))
