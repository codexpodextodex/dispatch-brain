"""Trust built on purpose, the price part only: a delivery's later value comes off the car's cost (0.75 of it), by the
day the car would be delivered; version 7's rule for which cars to quote is unchanged (alt/ld_trust_core.py)."""
from alt.ld_trust_core import Build, make as core_make


def make(client, world, level, now, params):
    return core_make(client, world, level, now, params, Build(gain=0.75, notice=0.0))
