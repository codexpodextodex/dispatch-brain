"""leaders/chains A: a driver who holds a gig of ours is offered the open car that takes him at least half of the way
home from where that gig ends, at typical x (1 - 0.45 x way-home share), then 0.30; see alt/ld_chains_core.py."""
from alt.ld_chains_core import Chain, make as core_make


def make(client, world, level, now, params):
    return core_make(client, world, level, now, params, Chain())
