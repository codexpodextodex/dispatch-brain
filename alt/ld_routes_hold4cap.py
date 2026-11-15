"""leaders/routes: ld_routes_hold4 (a short plain car waits up to 4 hours for a round-trip partner) and
ld_routes_cap (a two-car gig counts as one car against the day cap) together."""
from alt.ld_routes_cap import Hold, build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, Hold(hours=4, max_drive=180))
