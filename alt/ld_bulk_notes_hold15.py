"""leaders/bulk: both small pairing rules together. A new plain car waits up to 15 minutes for a partner
(alt/ld_bulk_hold15.py), and a car whose note changes nothing in effect counts as plain (alt/ld_bulk_notes.py).
In the replay: 12.5 and 4.5 more two-car gigs a week."""
from __future__ import annotations

from alt.ld_bulk_notes import NotePlain
from alt.pairhold import Hold, HoldDesk
from dispatch.geo import Geo
from dispatch.policy import Params, Policy


class NoteHoldDesk(NotePlain, HoldDesk):
    pass


def make(client, world, level: int, now: int, params: Params):
    desk = NoteHoldDesk(world, level, now, Policy(params), Geo(client.map()), hold=Hold(hours=0.25, until=17.5))
    desk.meet(world.roster())
    return desk
