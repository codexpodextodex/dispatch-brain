"""Version 8 priced to a volume target per due day: 1.04 x its usual cars per listed driver, gain 1, cost between
0.93 and 1.2 of version 8's (never under it in a careful week); see alt/ld_target_core.py."""
from alt.ld_target_core import make as base_make


def make(client, world, level, now, params):
    return base_make(client, world, level, now, params, gain=1.0, aim=1.04, floor=0.93, ceiling=1.2)
