"""leaders/chains T0: as alt/ld_chains_t.py, but the holders are told the minute the car comes into the app."""
from alt.ld_chains_core2 import Tell, make as core_make


def make(client, world, level, now, params):
    return core_make(client, world, level, now, params, Tell(age=0))
