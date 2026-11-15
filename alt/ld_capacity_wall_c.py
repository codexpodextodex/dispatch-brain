"""Cars due after Friday at 0.92 of version 7's cost behind the steep wall on the live count; see alt/ld_capacity_core.py."""
from alt.ld_capacity_core import make as base_make


def make(client, world, level, now, params):
    return base_make(client, world, level, now, params, scale=0.92)
