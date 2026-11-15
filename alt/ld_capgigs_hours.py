"""leaders/capgigs: version 8 with the day cap counted in driver-hours instead of cars (see alt/ld_capgigs_core.py).
A car due on day d costs x (1 + its driver-hours / 5.06 x (driver-hours of our cars due on d / (0.5497 x listed
drivers)) ^ 4). The cap 0.5497 gives version 8's mean multiplier (1.1086) over its 60 saved weeks."""
from alt.ld_capgigs_core import build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, mode="hours", cap=0.5497, ref=5.06)
