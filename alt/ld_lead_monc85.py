"""Version 7, no day cap for cars due after Friday and their cost times 0.85; see alt/ld_lead_monc.py."""
from alt.ld_lead_monc import make as base_make


def make(client, world, level, now, params):
    return base_make(client, world, level, now, params, scale=0.85)
