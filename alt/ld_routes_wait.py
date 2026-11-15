"""leaders/routes: see alt/ld_routes_core.py. This desk: the route fee, and a new car is held while a quote of ours that would make a pair with it awaits its answer."""
from alt.ld_routes_core import Routes, build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, Routes(wait=True))
