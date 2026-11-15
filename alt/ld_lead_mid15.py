"""leaders/lead: the day cap 1.5 times the usual one for last pickups on Tuesday and Wednesday. See alt/ld_lead_mid.py."""
from alt.ld_lead_mid import build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, factor=1.5, days=(1, 2))
