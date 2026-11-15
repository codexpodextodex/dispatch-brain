"""leaders/routes: see alt/ld_routes_core.py. This desk: the route fee, wider pairs gated by the route line, the short wait for an open quote, gigs of up to three cars."""
from alt.ld_routes_core import Routes, build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, Routes(hop=90, back=120, gate=1.15, wait=True, cars=3))
