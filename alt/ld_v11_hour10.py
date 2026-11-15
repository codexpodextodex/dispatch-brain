"""leaders/lead: version 11 with first_hour=10.0. See alt/ld_v11_core.py."""
from alt.ld_v11_core import build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, first_hour=10.0)
