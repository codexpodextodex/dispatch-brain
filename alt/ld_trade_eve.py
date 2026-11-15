"""leaders/trade, variant "eve": variant "hour" + the road line in place of the typical fee's draw + the top fee on the
evening before the last pickup (a round trip is planned the day before: the first booking of a trade-in came 17.6 hours
before its last pickup, median). See alt/ld_trade_core.py."""
from alt.ld_trade_core import Trade, build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, Trade(on=True, line=True, evening=True))
