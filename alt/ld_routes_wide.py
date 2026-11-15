"""leaders/routes: see alt/ld_routes_core.py. This desk: the route fee, and pairs up to 90 road minutes between the cars and 120 back when the route line is at most 1.15 times the two cars' own lines."""
from alt.ld_routes_core import Routes, build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, Routes(hop=90, back=120, gate=1.15))
