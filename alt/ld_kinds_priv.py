"""leaders/kinds, variant "priv": version 8 + the road line for private cars (rule 1) + private deliveries up to 5 hours of
drive at a booked hour from 12:00 to 18:00 (14:00 for 3 hours and more; rule 2) + private pickups up to 5 hours of drive
when the seller's slot starts before 12:00 and ends 8 hours or more after our answer (rule 3) + no private pickup whose
slot starts at 18:00 or later (those earned nothing). See alt/ld_kinds_core.py."""
from alt.ld_kinds_core import Kinds, build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, Kinds(steady_all=True, pd_hours=5.0, pp_hours=5.0, pp_evening=18.0))
