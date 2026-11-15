"""leaders/trade, variant "hour": trade-ins that one driver near the dealer can do as a round trip on the day of the
customer's hour, with that hour as the window of the new car's delivery. Version 10's fees. See alt/ld_trade_core.py."""
from alt.ld_trade_core import Trade, build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, Trade(on=True))
