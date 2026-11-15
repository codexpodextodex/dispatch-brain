"""leaders/trade: trade-ins (the new car out to a customer, the customer's old car back; one price, one gig), quoted
and posted so that the new car reaches the customer inside the booked hour. With `Trade()` (everything off) this desk
sends exactly version 10's actions.

Why ours came late (1,692 trade-ins won in 136 saved weeks, leaders/trade/causes.py: 47% late):

- The order's deadline is 20:00, but the new car is due at the end of the customer's hour plus 30 minutes (rule 5).
  A delivery stop without a window of its own runs to the order's deadline, so the world lets a driver book who will
  reach the customer hours after the hour: 38% of the late ones were booked 3 hours or more before the last pickup by
  such a driver (evening drivers, drivers with another gig first). `hour` gives the new car's delivery the customer's
  hour as its window: only a driver who plans to be there in the hour can book. The first pickup's window ends at the
  last start that reaches the end of the hour, so a booked driver whose day slips says so (`driver_late`) and version
  10's rule for late notices releases them while another can come.
- The quote measured the time to find a driver to the 20:00 deadline, 5.5 hours (median) after the true last pickup.
  The price is now asked with the new car's real deadline: the 14-hour rule and the day's cap see the true last pickup.
- 16% went as two gigs (over 12 hours of driving) or had to be collected the day before the customer's hour: 14% and
  0% on time, -54 and -85 euros a car. Not quoted (`round_trip`, `same_day`).
- A trade-in starts and ends at the dealer: it is a round trip for a driver who lives there. Where fewer than 100
  drivers live within 60 km of the dealer, 31 to 47% found no driver in time; where 100 and more do, 7% (`reach`).
- A customer's hour that starts before 11:00 needs the driver at the dealer's door when it opens: 27% on time
  (`first_hour`).
- The typical fee of a trade-in is the fee of ONE car (0.96 of the road line of the way out) and drivers took it at
  1.3 to 1.4: `cost` puts that in the price.

Played (12 screen weeks each, leaders/trade/played.py): posted as version 10 posts them (`ld_trade_nohour`) 55% of the
trade-ins were on time and earned 49 euros each; with the hour (`ld_trade_hour`) 80% and 59; with the hour, the road
line and the top fee on the evening before (`ld_trade_eve`) 84% and 66. Half of the late ones had their hour on a
Friday (`friday`; `ld_trade_nofri` leaves those out). The first 11 weeks of `ld_trade_hour` were played before the
rule "no windows once nobody can reach the hour" took its present form in `TradeDesk.stops` (a repost in the last hour).
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional

from dispatch import desk as desk_module
from dispatch.desk import Desk
from dispatch.geo import DAY, HOUR, PLATES_MINUTES, Geo, last_pickup, last_private_pickup
from dispatch.notes import apply
from dispatch.policy import ROAD_BASE, ROAD_MINUTE, Params, Policy
from spread import starter as kit

GRACE = 30  # rule 5: a private delivery is due at the end of its booked hour plus 30 minutes


@dataclass(frozen=True)
class Trade:
    on: bool = False  # quote trade-ins; off is version 10
    cost: float = 0.5  # more cost than a plain car, in typical fees: the typical fee is one car's, the work is two
    round_trip: float = 12.0  # at most this many hours of driving out and back: over 12 the world wants two gigs
    same_day: bool = True  # only when the new car can be collected on the day of the customer's hour
    reach: int = 100  # only where at least this many drivers live within 60 km of the dealer
    first_hour: float = 11.0  # only a customer's hour that starts at this hour or later
    friday: bool = True  # also a customer's hour on a Friday. There a miss costs half the price (the next business day is Monday) and the
    # week's drivers are at their scarcest: given back or without a driver 21% against 0 to 11% on the other days (777 saved trade-ins)
    calm: bool = True  # none while the week goes badly (`Policy.careful`)
    hour: bool = True  # the customer's hour as the window of the new car's delivery, and the last start as the end of its pickup's
    line: bool = False  # the road line in place of the typical fee's draw, in the price and the fees (as for plain cars)
    evening: bool = False  # the top fee on the evening before the last pickup, whatever its hour: a round trip is planned the day before
    top_fee: float = 0.0  # the top fee of a trade-in, in typical fees; 0 keeps top_fee


def hour_last(desk: Desk, request: dict, grace: int = GRACE) -> Optional[int]:
    """The last minute to collect the new car and reach the customer by the end of the booked hour plus `grace`. With the
    30 minutes of rule 5 it is the world's `lastPickupAt` (the same minute on 1,888 of 1,898 won trade-ins, the rest within
    14 minutes: there the old car's way back to the dealer by 20:00 is the tighter limit)."""
    new, facts = request["legs"][0], desk.facts(request)
    drive = desk.geo.drive(new) + (PLATES_MINUTES if facts.plates else 0)
    due = min(new["delivery"]["window"]["to"] + grace, facts.deadline or 10 ** 9)
    leg = apply(new, facts)
    return last_private_pickup(leg, due, drive) if leg["pickup"]["privateAddress"] else last_pickup(leg, due, drive)


class TradePolicy(Policy):
    def __init__(self, params: Params, trade: Trade):
        super().__init__(params)
        self.t = trade

    def fits(self, desk: Desk, request: dict) -> bool:
        """A trade-in that one driver who lives near the dealer can do as a round trip on the day of the customer's hour."""
        t, (new, old) = self.t, request["legs"]
        slot = new["delivery"]["window"]
        if desk.geo.drive(new) + desk.geo.drive(old) > t.round_trip * HOUR or desk.reach.get(new["pickup"]["placeId"], 0) < t.reach:
            return False
        if slot["from"] % DAY < t.first_hour * HOUR or (t.calm and self.careful(desk)) or (not t.friday and slot["from"] // DAY % 7 == 4):
            return False
        last = hour_last(desk, request)
        return last is not None and (not t.same_day or last // DAY == slot["from"] // DAY)

    def quote(self, desk: Desk, request: dict) -> dict[str, int]:
        t, base = self.t, self.p
        if not t.on or len(request["legs"]) != 2 or not self.fits(desk, request):
            return super().quote(desk, request)
        # Version 10's own quote, asked with the deadline of the new car: the end of the customer's hour plus 30 minutes.
        due = request["legs"][0]["delivery"]["window"]["to"] + GRACE
        asked = {**request, "options": [{**option, "deadline": min(option["deadline"], due)} for option in request["options"]]}
        self.p = replace(base, trade_in=1, cost_trade_in=t.cost, private_find_hours=base.min_find_hours)
        try:
            return super().quote(desk, asked)
        finally:
            self.p = base

    def steady(self, desk: Desk, request: dict, leg: dict, typical: float, blend: float) -> float:
        if self.t.line and blend and len(request["legs"]) == 2:  # the draw around the road line of the way out, as for a plain car
            line = ROAD_BASE + ROAD_MINUTE * desk.geo.minutes[leg["pickup"]["placeId"], leg["delivery"]["placeId"]]
            return typical + blend * (min(1.25 * typical, max(0.8 * typical, line)) - typical)
        return super().steady(desk, request, leg, typical, blend)

    def fees(self, desk: Desk, order: dict, cars: int, urgent: bool) -> list[dict]:
        t, base = self.t, self.p
        if len(order["legs"]) != 2 or not (t.evening or t.top_fee):
            return super().fees(desk, order, cars, urgent)
        self.p = replace(base, early_hour=24.0 if t.evening else base.early_hour, early_long=24.0 if t.evening else base.early_long, top_fee=t.top_fee or base.top_fee)
        try:
            return super().fees(desk, order, cars, urgent)
        finally:
            self.p = base


class TradeDesk(Desk):
    def stops(self, order: dict, legs: list[int], retry: kit.Retry, facts) -> list[dict]:
        stops = super().stops(order, legs, retry, facts)
        if len(order["legs"]) != 2 or 0 not in legs or not self.policy.t.hour or not self.windowed:
            return stops
        new = order["legs"][0]
        slot = new["delivery"]["window"]
        start = hour_last(self, {**self.requests[order["id"]], "legs": order["legs"]}, grace=0)  # the last start that reaches the end of the hour
        if start is None or start < self.now:
            return stops  # nobody reaches the customer inside the hour any more: the car goes without windows, as any late car
        for index, stop in enumerate(stops):
            if stop["leg"] != 0:
                continue
            own = stop.get("window") or {}
            if stop["kind"] == "delivery":
                stops[index] = {**stop, "window": {"from": slot["from"], "to": min(slot["to"], own.get("to", slot["to"]))}}
            elif not new["pickup"]["privateAddress"]:
                # When this window ends without a driver the gig leaves the app (`gig_expired`) and the desk posts it again
                # without windows: from then on a driver who comes after the hour is better than none.
                opens = own.get("from", new["pickup"]["window"]["from"])
                if start >= opens:
                    stops[index] = {**stop, "window": {"from": opens, "to": min(start, own.get("to", start))}}
        self.stats["trade_hours"] += 1
        return stops

    windowed, trying = True, False  # only while one trade-in is being posted; nothing to rebuild after a restart

    def post_now(self, order: dict, legs: list[int], retry: kit.Retry = kit.Retry()) -> None:
        """A trade-in goes out with the customer's hour as a window. Should the world refuse that gig, the cars go out
        as version 10 posts them (one gig, or one for each car over 12 hours): no order may be left without a gig."""
        if len(order["legs"]) != 2 or not self.policy.t.hour or not self.windowed:
            return super().post_now(order, legs, retry)
        if self.trying:
            return  # version 10's own fallback for a refused gig: the second try below does it, without our windows
        self.send()
        self.trying = True
        try:
            super().post_now(order, legs, retry)
            self.send()
        finally:
            self.trying = False
        if any(leg not in self.leg_gigs.get(order["id"], {}) for leg in legs):
            self.stats["trade_refused"] += 1
            self.windowed = False
            try:
                super().post_now(order, legs, retry)
                self.send()
            finally:
                self.windowed = True

    def late_driver(self, event: dict) -> None:
        """A booked driver of a trade-in who starts after the pickup's window but still reaches the customer inside the 30
        minutes of rule 5 is on time: keep them."""
        post = self.posts.get(event["gigId"])
        order = self.orders.get(post["stops"][0]["orderId"]) if post else None
        if order is not None and len(order["legs"]) == 2 and None in order["deliveredAt"][:1]:
            new = order["legs"][0]
            if event["pickupAt"] + self.geo.drive(new) <= new["delivery"]["window"]["to"] + GRACE:
                self.stats["trade_late_kept"] += 1
                return
        super().late_driver(event)


def build(client, world, level: int, now: int, params: Params, trade: Trade):
    if params.windows and "driver_late" not in desk_module.WAKE_ON:
        desk_module.WAKE_ON.append("driver_late")  # as dispatch.play.new_desk does for the usual desk
    desk = TradeDesk(world, level, now, TradePolicy(params, trade), Geo(client.map()))
    desk.meet(world.roster())
    return desk


def make(client, world, level: int, now: int, params: Params):
    return build(client, world, level, now, params, Trade())
