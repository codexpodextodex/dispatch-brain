"""Cars due after Friday at version 7's cost (no cut) behind the steep wall on the live count in place of the cap:
the safe form of alt/ld_lead_monoff; see alt/ld_capacity_core.py."""
from alt.ld_capacity_core import make as base_make


def make(client, world, level, now, params):
    return base_make(client, world, level, now, params, scale=1.0)
