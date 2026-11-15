"""leaders/kinds, variant "safe": the rules of the line without premium cars (alt/ld_kinds_core2.py): the road line for
private cars; private deliveries to 5 hours of drive at a booked hour from 12:00 (14:00 from 3 hours) to 18:00; private
pickups to 5 hours of drive with a slot that starts before 12:00 and ends 8 hours after our answer, none with a slot from
18:00; on Monday every plain car with 6 hours of notice, on Tuesday with 8."""
from alt.ld_kinds_core2 import Kinds, build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, Kinds(steady_all=True, pd_hours=5.0, pp_hours=5.0, pp_evening=18.0, notice=((6, 4), (8, 4))))
