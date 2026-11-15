"""As alt/ld_price_a.py (version 7 with the price book of alt/ld_price_core.py, priced against twice the spread the
book believes), with a car at 0.965 of version 7's cost instead of 0.98: design a won 10 cars a week fewer than
version 7 on the 12 screen weeks, and offline 0.01 of cost is worth about 8 cars. The aim is version 7's number of cars."""
from alt.ld_price_core import make_with


def make(client, world, level, now, params):
    return make_with(client, world, level, now, params, {"widen": 2.0, "scale": 0.965})
