"""Version 8 with the volume target as a ceiling only: where the cars won for a due day run ahead of the path to
1.04 x the usual cars per listed driver, the cost of a car for that day goes up (to 1.2 x at most); it never goes
under version 8's. See alt/ld_target_core.py."""
from alt.ld_target_core import make as base_make


def make(client, world, level, now, params):
    return base_make(client, world, level, now, params, gain=1.0, aim=1.04, floor=1.0, ceiling=1.2)
