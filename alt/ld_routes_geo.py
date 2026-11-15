"""leaders/routes: see alt/ld_routes_core.py. This desk: version 7 with the fee of a two-car gig set by its route line (0.82 of it; the opening fee is 0.70), and a returned pair known again."""
from alt.ld_routes_core import Routes, build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, Routes())
