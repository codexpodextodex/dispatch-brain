"""leaders/kinds: the requests version 8 does not quote, taken by kind where the saved weeks say the kind was punctual
and paid. Every rule here is OFF by default: with `Kinds()` this desk sends exactly version 8's actions
(leaders/kinds/check.py replays a saved week through both and compares every action).

What the saved weeks showed (leaders/kinds/out/*.txt; 60 to 180 exact weeks that carried each kind):

1. `steady_all`. A premium or private car's typical fee is drawn around the same road line as a plain car's
   (16.04 euros + 38.44 cents a minute; median typical / line 0.99 to 1.01 for every kind). Version 8 takes that draw
   out of a plain car's cost and fees (`Policy.steady`) but not out of these kinds': so it wins the private and premium
   cars whose typical fee was drawn low, at a low price, and posts them at a fee no driver takes. Of the private
   deliveries we carried, 37% had a typical fee under 0.9 of the line: late 10.0%, 21 euros a car; the others late 3.1%,
   36 a car. Premium: 45% under 0.9, late 30%; the others 13%. With `steady_all` these kinds get the plain car's rule.
2. Private deliveries with a longer drive (`pd_hours`), at the booked hours that were punctual (`pd_from` to `pd_to`):
   2 to 3 hours of drive at a booked hour from 12:00 to 18:00 came late 2% (212 cars, 40 to 52 euros a car), 3 to 5 hours
   at a booked hour from 14:00 to 18:00 0% (45 cars, 77 to 86 a car); an evening hour or a morning hour 12 to 29%.
3. Private pickups with a longer drive (`pp_hours`) when the seller's slot starts in the morning (`pp_slot_before`) and
   ends at least `pp_lead` hours after the answer: 2 to 3 hours of drive with a slot before 12:00, 4% late and 46 to 54
   euros a car; a slot from 16:00 on, 8 to 65% late and nothing earned. `pp_evening` declines every private pickup whose
   slot starts at or after that hour: under 2 hours of drive those earned -0.6 (18:00 on) and 10.7 euros a car (16:00 on).
4. Premium cars (`premium`): only 61 of a week's 818 drivers are experienced. Kept: a drive from `prem_drive_from` to
   `prem_drive_to` minutes, or any drive when the last pickup falls after Friday (`prem_weekend`), on an option that
   leaves `prem_find` hours to find the driver: 347 cars in 90 weeks, 6.9% late, 45 euros a car, against 20.7% for all.
5. `monday_find`: on the first day every driver is free and nothing of ours is posted: a plain car needs less notice.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from dispatch import desk as desk_module
from dispatch.desk import Desk
from dispatch.geo import DAY, HOUR, PLATES_MINUTES, Geo, last_pickup
from dispatch.notes import apply
from dispatch.policy import ROAD_BASE, ROAD_MINUTE, Params, Policy


@dataclass(frozen=True)
class Kinds:
    steady_all: bool = False  # the road line in place of the typical fee's draw, for premium and private cars too
    pd_hours: float = 0.0  # private deliveries with a drive under this many hours (0: version 8's limit for every drive)
    pd_from: float = 12.0  # ... beyond version 8's limit only at a booked hour that starts from this hour
    pd_to: float = 18.0  # ... and before this one
    pd_far_hours: float = 3.0  # ... a drive of this many hours or more only at a booked hour from `pd_far_from`
    pd_far_from: float = 14.0
    pp_hours: float = 0.0  # private pickups with a drive under this many hours (0: version 8's limit)
    pp_slot_before: float = 12.0  # ... beyond version 8's limit only when the seller's slot starts before this hour
    pp_lead: float = 8.0  # ... and ends at least this many hours after our answer
    pp_evening: float = 0.0  # no private pickup whose slot starts at or after this hour; 0 is off
    premium: bool = False  # premium cars, as below
    prem_drive_from: int = 30  # a drive of at least this many minutes,
    prem_drive_to: int = 120  # ... and under this many,
    prem_weekend: bool = True  # or any drive when the last pickup falls after Friday
    prem_find: float = 24.0  # on an option that leaves this many hours to find an experienced driver
    prem_cost: float = 0.0  # more cost for a premium car, in typical fees
    monday_find: float = 0.0  # the least notice for a plain car asked on the first day, in hours; 0 keeps min_find_hours
    monday_until: int = 0  # ... the last day of the week (0 Monday) on which that looser notice holds


class KindsPolicy(Policy):
    def __init__(self, params: Params, kinds: Kinds):
        super().__init__(params)
        self.k = kinds

    def quote(self, desk: "Desk", request: dict) -> dict[str, int]:
        k, base, legs = self.k, self.p, request["legs"]
        leg, changed, asked = legs[0], {}, request
        if len(legs) == 1:
            drive = desk.geo.drive(leg)
            private_pickup, private_delivery, premium = bool(leg["pickup"]["privateAddress"]), bool(leg["delivery"]["privateAddress"]), bool(leg["car"]["premium"])
            if premium:
                if k.premium and not base.premium and not private_pickup and not private_delivery:
                    options = self.premium_options(desk, request, drive)
                    if options:
                        asked = {**request, "options": options}
                        changed.update(premium=1, cost_premium=k.prem_cost)
            elif private_pickup or private_delivery:
                slot = leg["pickup"]["window"]
                if private_pickup and k.pp_evening and slot["from"] % DAY >= k.pp_evening * HOUR:
                    changed["private_pickup"] = 0
                elif base.private_drive_hours > 0 and drive >= base.private_drive_hours * HOUR:
                    fits = True
                    if private_delivery:
                        hour = leg["delivery"]["window"]["from"] % DAY
                        first = k.pd_far_from if drive >= k.pd_far_hours * HOUR else k.pd_from
                        fits = drive < k.pd_hours * HOUR and first * HOUR <= hour < k.pd_to * HOUR
                    if private_pickup:
                        fits = fits and drive < k.pp_hours * HOUR and slot["from"] % DAY < k.pp_slot_before * HOUR and slot["to"] - request["respondBy"] >= k.pp_lead * HOUR
                    if fits:
                        changed["private_drive_hours"] = 0.0
            elif k.monday_find and request["arrivedAt"] // DAY <= k.monday_until:
                changed["min_find_hours"] = min(base.min_find_hours, k.monday_find)
        if not changed:
            return super().quote(desk, request)
        self.p = replace(base, **changed)  # version 8's own quote, with its switches set for this one request
        try:
            return super().quote(desk, asked)
        finally:
            self.p = base

    def premium_options(self, desk: "Desk", request: dict, drive: int) -> list[dict]:
        """The options of a premium request that we want: enough time to find one of the few experienced drivers, and a
        drive of the length that they took in time, or a last pickup after Friday (the weekend finds the driver)."""
        k, leg, facts = self.k, request["legs"][0], desk.facts(request)
        noted = apply(leg, facts) if self.p.notes == "ours" else leg
        minutes = drive + (PLATES_MINUTES if self.p.notes == "ours" and facts.plates else 0)
        kept = []
        for option in request["options"]:
            deadline = min(option["deadline"], facts.deadline) if self.p.notes == "ours" and facts.deadline else option["deadline"]
            last = last_pickup(noted, deadline, minutes)
            if last is None or last - request["respondBy"] < k.prem_find * HOUR:
                continue
            if k.prem_drive_from <= drive < k.prem_drive_to or (k.prem_weekend and last // DAY >= 5):
                kept.append(option)
        return kept

    def steady(self, desk: "Desk", request: dict, leg: dict, typical: float, blend: float) -> float:
        if self.k.steady_all and blend and len(request["legs"]) == 1:
            asked = request["legs"][0]
            special = leg["car"]["premium"] or leg["pickup"]["privateAddress"] or leg["delivery"]["privateAddress"]
            if special and all(leg[end]["placeId"] == asked[end]["placeId"] for end in ("pickup", "delivery")):
                line = ROAD_BASE + ROAD_MINUTE * desk.geo.minutes[leg["pickup"]["placeId"], leg["delivery"]["placeId"]]
                return typical + blend * (min(1.25 * typical, max(0.8 * typical, line)) - typical)
        return super().steady(desk, request, leg, typical, blend)


def build(client, world, level: int, now: int, params: Params, kinds: Kinds):
    if params.windows and "driver_late" not in desk_module.WAKE_ON:
        desk_module.WAKE_ON.append("driver_late")  # as dispatch.play.new_desk does for the usual desk: the practice clock stops at the notice
    desk = Desk(world, level, now, KindsPolicy(params, kinds), Geo(client.map()))
    desk.meet(world.roster())
    return desk


def make(client, world, level: int, now: int, params: Params):
    return build(client, world, level, now, params, Kinds())
