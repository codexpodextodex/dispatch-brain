"""Version 7 with the day cap's charge for a place limited to 80 euros, the average cost the cap multiplies today (alt/ld_percar_slot.py)."""
from alt.ld_percar_slot import make as base_make


def make(client, world, level, now, params):
    return base_make(client, world, level, now, params, limit=8000)
