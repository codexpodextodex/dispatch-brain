"""leaders/lead: version 11 where a car under 4 hours of drive pays the day's load term on 40 euros, whatever its own cost. See alt/ld_v11_core.py."""
from alt.ld_v11_core import build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, flat_ref=40.0)
