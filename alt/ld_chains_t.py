"""leaders/chains T: a single car that has waited 45 minutes in the app is offered, at the fee the app shows, to the
drivers who hold a gig of ours it can follow that day (pickup within 60 road minutes of where their gig ends), three
at a time, the ones it takes home first; see alt/ld_chains_core2.py."""
from alt.ld_chains_core2 import Tell, make as core_make


def make(client, world, level, now, params):
    return core_make(client, world, level, now, params, Tell())
