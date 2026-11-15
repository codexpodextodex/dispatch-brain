"""Version 7 with the price book of alt/ld_price_core.py (one level a day, the price-war hump, outage rows, offsets
of route and towns with their uncertainty, trust counted and not learned). The price is set against twice the
spread the book believes, and a car costs 0.98 of version 7's cost: offline (leaders/price/fixed.py) that wins
version 7's number of cars, so that a better estimate shows as price and not as more cars."""
from alt.ld_price_core import make_with


def make(client, world, level, now, params):
    return make_with(client, world, level, now, params, {"widen": 2.0, "scale": 0.98})
