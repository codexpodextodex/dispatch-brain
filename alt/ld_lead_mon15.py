"""Version 7 with the day cap for cars due after Friday multiplied by 1.5 (0 = no cap for them); see alt/ld_lead_mon.py."""
from alt.ld_lead_mon import make as base_make


def make(client, world, level, now, params):
    return base_make(client, world, level, now, params, factor=1.5)
