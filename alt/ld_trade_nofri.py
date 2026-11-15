"""leaders/trade, variant "nofri": the hour window (variant "hour") without the trade-ins whose customer's hour is on a
Friday: in the first screens 7 of 15 of those came late against 4 of 41 on the other days. See alt/ld_trade_core.py."""
from alt.ld_trade_core import Trade, build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, Trade(on=True, friday=False))
