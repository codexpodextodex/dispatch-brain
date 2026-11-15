"""Per-car fees (leaders/fees): the opening fee of a gig follows what THAT car needs, not one share of the typical fee.

Measured on matched cars (the same request under opening fees 0.60 to 0.95, leaders/fees/REPORT.md):
- A car that goes to a place where drivers live is taken by a driver on the way home, who needs about 0.75 typical
  fees. Opened at 0.75 instead of 0.85 it is booked as fast and as punctually, 0.06 to 0.08 typical fees cheaper.
- A car that goes where few drivers live is not: opened lower it sits, drivers who saw it low wait, and the fee
  finally paid is higher. It keeps 0.85.
- A car won with 5 to 7 hours to its last pickup opens at the top fee (1.2) in version 7 and is booked at once;
  the same kind of car with 7 to 8 hours opens at 0.85, rises within the hour, and is paid 1.01 with no more late cars.

`Rule` holds the numbers; a variant module sets them and calls `build`. Everything else is version 7."""
from __future__ import annotations

from dataclasses import dataclass

from spread import starter as kit

from dispatch.desk import Desk
from dispatch.geo import DAY, HOUR, Geo, open_span
from dispatch.notes import apply
from dispatch.policy import Params, Policy


@dataclass(frozen=True)
class Rule:
    easy_open: float = 0.0  # the opening fee of a car that goes where drivers live, in typical fees; 0 keeps the usual one
    easy_drivers: int = 30  # ... at least this many drivers live within 30 km of the delivery,
    easy_hours: float = 5.0  # ... and the drive is shorter than this,
    easy_min_fee: int = 0  # ... and its typical fee is at least this many cents: a small gig is a driver's fixed trouble, it gains nothing from a lower fee
    easy_open_many: float = 0.0  # a still lower opening fee where very many drivers live (`many_drivers`); 0 is off
    many_drivers: int = 300
    short_ramp: int = 0  # 1: a car won at short notice opens at its usual opening fee and reaches the top fee fast, instead of opening at the top fee
    short_min: int = 120  # ... only with at least this many minutes left to the moment of the late fee
    short_reach: int = 80  # ... the top fee comes after a third of that time, at most this many minutes
    evening_ramp: int = 0  # 1: the same for a car won on the evening before an early last pickup (it opens at the top fee in version 7)
    evening_minutes: int = 30  # ... which reaches the top fee after this many minutes
    cost_easy: float = 0.0  # typical fees off the cost of an easy car in the quote: it costs us less to move; 0 is off
    cost_hard: float = 0.0  # typical fees more for a car that goes where fewer than `hard_drivers` live, with a drive of `hard_hours` or more
    hard_drivers: int = 10
    hard_hours: float = 4.0
    tomorrow: int = 0  # 1: a car that is ready today but not due today, won late in the day, is posted with a pickup from tomorrow morning.
    # A driver prices a gig by the day it takes: collected this afternoon it ends with an evening trip home. The same car with the
    # same deadline that is only ready tomorrow is booked at once twice as often and paid 0.07 typical fees less (leaders/fees/ready.py)
    tomorrow_from: float = 11.0  # ... from this hour for a drive of `tomorrow_drive` hours or more,
    tomorrow_drive: float = 2.0
    tomorrow_late: float = 15.0  # ... and from this hour for every drive


class FeePolicy(Policy):
    def __init__(self, params: Params, rule: Rule):
        super().__init__(params)
        self.rule = rule
        self.posting = None  # the order whose fees are being set: `rising` needs to know the car

    def plain_leg(self, order_or_request: dict) -> bool:
        legs = order_or_request["legs"]
        leg = legs[0]
        return len(legs) == 1 and not leg["car"]["premium"] and not leg["pickup"]["privateAddress"] and not leg["delivery"]["privateAddress"]

    def easy(self, desk: Desk, order_or_request: dict) -> bool:
        """A car that a driver on the way home takes: many drivers live where it goes, and the drive is not long."""
        leg, r = order_or_request["legs"][0], self.rule
        if not self.plain_leg(order_or_request) or desk.near.get(leg["delivery"]["placeId"], 0) < r.easy_drivers or desk.geo.drive(leg) >= r.easy_hours * HOUR:
            return False
        if r.easy_min_fee:
            request = desk.requests.get(order_or_request["id"], order_or_request)
            return self.steady(desk, request, leg, request["referenceFeeCents"], self.p.road_fee_blend) >= r.easy_min_fee
        return True

    def opening(self, desk: Desk, order: dict) -> float:
        r = self.rule
        if r.easy_open and self.easy(desk, order):
            if r.easy_open_many and desk.near.get(order["legs"][0]["delivery"]["placeId"], 0) >= r.many_drivers:
                return r.easy_open_many
            return r.easy_open
        return super().opening(desk, order)

    def fees(self, desk: Desk, order: dict, cars: int, urgent: bool) -> list[dict]:
        self.posting = order if cars == 1 and self.plain_leg(order) else None
        try:
            return super().fees(desk, order, cars, urgent)
        finally:
            self.posting = None

    def rising(self, now: int, last: int, warning: int, step, opening: float, drive: float = 0) -> list[dict]:
        p, r = self.p, self.rule
        if self.posting is None or p.schedule == "plan" or not (r.short_ramp or r.evening_ramp):
            return super().rising(now, last, warning, step, opening, drive)
        early = p.early_long if p.early_long and drive >= p.long_hours * HOUR else p.early_hour
        evening = last % DAY < early * HOUR
        top_at = last // DAY * DAY - DAY + p.evening_hour * HOUR if evening else warning - (p.lead_hours - 3) * HOUR
        top_at = min(max(top_at, now), warning)
        if top_at - now >= HOUR:  # the usual case: time enough to open low
            return super().rising(now, last, warning, step, opening, drive)
        if evening and r.evening_ramp and warning - now >= 3 * HOUR:
            reach = now + r.evening_minutes
        elif not evening and r.short_ramp and warning - now >= r.short_min:
            reach = now + min(r.short_reach, (warning - now) / 3)
        else:
            return super().rising(now, last, warning, step, opening, drive)
        ramp_from = now + p.hold * (reach - now)
        steps = [step(now, opening)]
        steps += [step(ramp_from + (reach - ramp_from) * k / 6, opening + (p.top_fee - opening) * k / 6) for k in range(1, 7)]
        if warning - reach >= HOUR:
            steps += [step(reach + (warning - reach) * k / 6, p.top_fee + (p.late_fee - p.top_fee) * k / 6) for k in range(1, 7)]
        return steps

    def cost(self, desk: Desk, request: dict, option: dict, last: int) -> float:
        cost, r = super().cost(desk, request, option, last), self.rule
        if not (r.cost_easy or r.cost_hard) or not self.plain_leg(request):
            return cost
        leg = request["legs"][0]
        typical = self.steady(desk, request, leg, request["referenceFeeCents"], self.p.road_cost_blend) / option["listPriceCents"]
        if r.cost_easy and self.easy(desk, request):
            cost -= r.cost_easy * typical
        if r.cost_hard and desk.near.get(leg["delivery"]["placeId"], 0) < r.hard_drivers and desk.geo.drive(leg) >= r.hard_hours * HOUR:
            cost += r.cost_hard * typical
        return cost


class FeeDesk(Desk):
    def stops(self, order: dict, legs: list[int], retry: kit.Retry, facts) -> list[dict]:
        stops = super().stops(order, legs, retry, facts)
        r = self.policy.rule
        if not r.tomorrow or len(legs) != 1 or retry != kit.Retry() or not self.policy.plain_leg(order):
            return stops
        today, minute = self.now // DAY, self.now % DAY
        if today % 7 > 3:  # on a Friday the next working day is Monday, and Saturday is open at short hours: leave it
            return stops
        leg, pickup = order["legs"][0], stops[0]
        last = self.last_pickup.get(order["id"], order["lastPickupAt"])
        window = pickup.get("window", leg["pickup"]["window"])
        if window["from"] // DAY > today or last // DAY <= today:
            return stops  # not ready today, or due today
        if not (minute >= r.tomorrow_late * HOUR or (minute >= r.tomorrow_from * HOUR and self.geo.drive(leg) >= r.tomorrow_drive * HOUR)):
            return stops
        span = open_span(apply(leg, facts)["pickup"], today + 1)
        if span is None or last - max(window["from"], span[0]) < 2 * HOUR:
            return stops
        start = max(window["from"], span[0])
        stops[0] = {**pickup, "window": {"from": start, "to": max(start, window["to"])}}
        self.stats["posted_for_tomorrow"] += 1
        return stops


def build(client, world, level: int, now: int, params: Params, rule: Rule) -> Desk:
    desk = FeeDesk(world, level, now, FeePolicy(params, rule), Geo(client.map()))
    desk.meet(world.roster())
    return desk
