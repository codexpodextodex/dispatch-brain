"""leaders/routes: see alt/ld_routes_hold.py. This desk: version 8, and a plain car with at most 3 hours of driving
and at least 16 hours to its last pickup waits up to 4 hours (never past 18:00) for a round-trip partner."""
from alt.ld_routes_hold import Hold, build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, Hold(hours=4, max_drive=180))
