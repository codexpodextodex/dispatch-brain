"""Cars due after Friday at 0.85 of version 7's cost behind a steep wall on the live count (0.105 a listed driver,
moving in when their gigs are slow to find drivers or the week is careful); see alt/ld_capacity_core.py."""
from alt.ld_capacity_core import make as base_make


def make(client, world, level, now, params):
    return base_make(client, world, level, now, params, scale=0.85)
