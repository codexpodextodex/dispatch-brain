"""leaders/trade, the control of variant "hour": the same trade-ins at the same prices, posted as version 10 posts them
(no window on the new car's delivery). The difference between the two is what the customer's hour as a window does.
See alt/ld_trade_core.py."""
from alt.ld_trade_core import Trade, build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, Trade(on=True, hour=False))
