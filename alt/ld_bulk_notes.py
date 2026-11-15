"""leaders/bulk: a car whose note changes nothing in effect may ride in a two-car gig.

Version 7 keeps a car out of every pair when its note states site hours, a ready time or a deadline: 63 cars a
week. For 22 of them the note changes nothing: the hours are the stated ones or wider, the ready time is no later
than the request's, the deadline no earlier than the option's ("destination open weekdays 9-21"). Letting those
in makes 4.5 more two-car gigs a week in the replay (leaders/bulk/s4f_notepairs.py); a two-car gig is driven for
0.73 of two typical fees. A note that narrows anything keeps its car alone, as before. The rest is version 7."""
from __future__ import annotations

from dispatch.desk import Desk
from dispatch.geo import Geo
from dispatch.notes import apply
from dispatch.policy import Params, Policy


class NotePlain:
    """`plain` for any desk: mix in before the desk class."""

    def plain(self, order: dict) -> bool:
        if len(order["legs"]) != 1 or None not in order["deliveredAt"] or order["legs"][0]["car"]["premium"]:
            return False
        if order["id"] in self.urgent or order["id"] in self.alone:
            return False
        facts, leg = self.facts(self.requests[order["id"]]), order["legs"][0]
        hours = any(value is not None for value in (facts.pickup_opens, facts.pickup_closes, facts.delivery_opens, facts.delivery_closes))
        if facts.plates or (hours and (leg["pickup"]["privateAddress"] or leg["delivery"]["privateAddress"])):
            return False
        real = apply(leg, facts)  # the leg as the note changes it
        if real["pickup"]["hours"] != leg["pickup"]["hours"] or real["delivery"]["hours"] != leg["delivery"]["hours"]:
            return False
        if facts.pickup_from and facts.pickup_from > leg["pickup"]["window"]["from"]:
            return False
        return not (facts.deadline and facts.deadline < order["deadline"])


class NoteDesk(NotePlain, Desk):
    pass


def make(client, world, level: int, now: int, params: Params):
    desk = NoteDesk(world, level, now, Policy(params), Geo(client.map()))
    desk.meet(world.roster())
    return desk
