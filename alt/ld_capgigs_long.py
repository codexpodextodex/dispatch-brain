"""leaders/capgigs: version 8 with the day cap in two pools (see alt/ld_capgigs_core.py). Every car pays for the cars
due on its day at a looser cap (0.125 a listed driver), and a car with 4 hours of road or more also pays for the long
cars due that day (cap 0.0237 a listed driver). Together they charge version 8's mean multiplier (1.1086)."""
from alt.ld_capgigs_core import build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, mode="long", cap=0.125, cap_long=0.0237, long_hours=4.0)
