"""leaders/routes: see alt/ld_routes_core.py. This desk: the route fee, the short wait for an open quote, and a third car may join a gig of two that no driver has taken."""
from alt.ld_routes_core import Routes, build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, Routes(wait=True, cars=3))
