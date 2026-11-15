"""Trust built on purpose: a delivery's later value comes off the car's cost (0.75 of it), and a valuable short car
may be quoted with 5 hours to find a driver, so that it is delivered, and counted, the same day (alt/ld_trust_core.py)."""
from alt.ld_trust_core import Build, make as core_make


def make(client, world, level, now, params):
    return core_make(client, world, level, now, params, Build(gain=0.75, notice=5.0))
