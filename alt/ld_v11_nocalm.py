"""leaders/lead: version 11 with trade-ins quoted also while the brake is on (calm=False). See alt/ld_v11_core.py."""
from alt.ld_v11_core import build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, calm=False)
