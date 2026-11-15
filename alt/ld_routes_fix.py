"""leaders/routes: see alt/ld_routes_core.py. This desk: version 7 with a returned pair known again, nothing else (the control for the other ld_routes desks)."""
from alt.ld_routes_core import Routes, build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, Routes(geo_fee=False))
