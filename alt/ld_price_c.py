"""Version 7's own quotes, raised where the new price book gives the higher price at least 90% chance of a yes
(alt/ld_price_hyb.py). Offline on 13 measured weeks: 96% of version 7's cars, 9.5 cars a week fewer, +1.24 euros
a car on the shared cars."""
from alt.ld_price_hyb import make_with


def make(client, world, level, now, params):
    return make_with(client, world, level, now, params, sure=0.9)
