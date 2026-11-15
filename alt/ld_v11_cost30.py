"""leaders/lead: version 11 with a trade-in's extra cost at 0.3 typical fees in place of 0.5 (offline the margin of trade-ins peaks at 1.3 x list, leaders/trade/out/size.txt; version 11 sells them at 1.43). See alt/ld_v11_core.py."""
from alt.ld_v11_core import build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, cost=0.3)
