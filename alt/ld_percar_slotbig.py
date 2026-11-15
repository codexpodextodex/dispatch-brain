"""Version 7 with the day cap's charge for a place limited to no limit: must replay version 7 to the cent (a check of the plug-in) (alt/ld_percar_slot.py)."""
from alt.ld_percar_slot import make as base_make


def make(client, world, level, now, params):
    return base_make(client, world, level, now, params, limit=1000000000)
