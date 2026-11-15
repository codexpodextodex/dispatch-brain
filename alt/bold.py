"""Bolder rules for which cars to win, each one bet on the shape of the week, played on version 6's desk or on
the holding desk (alt/pairhold.py). The settings of the week are in `Bold`; each variant is a small module.

- `by_day`: what a car costs us depends on the day it is won. Cars won Monday and Tuesday are due before the
  hard end of the week and come late a fraction as often as cars won later, so they are priced to win many
  more; cars won from Wednesday are priced to win fewer.
- `no_same_day`: never quote the same-day option. Same-day cars earn 39.5 a car against 45.6 for next day.
- `stop`: no new car for a day once this many of our cars due that day have no driver, per 100 drivers in the
  list: a hard stop instead of version 6's smooth cap, so a desk priced for volume cannot overfill a day.
- `refuse_drive`: never take a car with more than this many minutes of driving to a town with fewer than 10
  drivers within 30 km: in version 6's weeks 10% of the cars (at 180 minutes), 27% of the late ones and 31% in
  the hard weeks, for 2,832 euros a week. Meant with a lower cost: the drivers it frees carry cheaper cars."""
from __future__ import annotations

from dataclasses import dataclass

from dispatch.desk import Desk
from dispatch.geo import DAY, Geo
from dispatch.policy import Params, Policy


@dataclass(frozen=True)
class Bold:
    by_day: tuple = (1.0, 1.0, 1.0, 1.0, 1.0)  # cost multiplier for a request that arrives Monday .. Friday
    no_same_day: bool = False
    stop: float = 0.0  # unbooked cars due on one day, per 100 drivers, at which that day takes no new car; 0 is off
    refuse_drive: int = 0  # minutes of driving over which a car to a town with few drivers is declined; 0 is off


class BoldPolicy(Policy):
    def __init__(self, params: Params, bold: Bold):
        super().__init__(params)
        self.bold = bold

    def quote(self, desk: Desk, request: dict) -> dict[str, int]:
        leg = request["legs"][0]
        if self.bold.refuse_drive and desk.near.get(leg["delivery"]["placeId"], 0) < 10 and desk.geo.drive(leg) > self.bold.refuse_drive:
            return {request["options"][0]["kind"]: round(request["options"][0]["listPriceCents"] * self.p.decline)}
        if self.bold.no_same_day:
            later = [o for o in request["options"] if o["kind"] != "same_day"]
            if not later:  # a dealer who wants it today only: decline, a losing quote costs nothing
                return {request["options"][0]["kind"]: round(request["options"][0]["listPriceCents"] * self.p.decline)}
            request = {**request, "options": later}
        return super().quote(desk, request)

    def cost(self, desk: Desk, request: dict, option: dict, last: int) -> float:
        cost = super().cost(desk, request, option, last) * self.bold.by_day[min(4, request["arrivedAt"] // DAY)]
        if self.bold.stop and self.unbooked(desk, last // DAY) >= self.bold.stop * desk.drivers / 100:
            cost *= 10.0  # the day is full: decline
        return cost

    def unbooked(self, desk: Desk, day: int) -> int:
        """Our posted cars due on a day (last pickup) that no driver holds now. A car held back for a partner is
        waiting by choice and does not count. Version 6's 60 weeks peak at 1.2 to 2.5 per 100 drivers in easy
        weeks and 2.7 to 3.9 in most hard ones."""
        held = getattr(desk, "held", {})
        return sum(1 for order_id, order in desk.orders.items()
                   if order_id not in held and None in order["deliveredAt"] and desk.last_pickup.get(order_id, order["lastPickupAt"]) // DAY == day
                   and not any(gig in desk.booked for gig in desk.gigs_of(order_id)))


def make(client, world, level: int, now: int, params: Params, bold: Bold = Bold(), hold=None):
    policy = BoldPolicy(params, bold)
    if hold is None:
        desk = Desk(world, level, now, policy, Geo(client.map()))
    else:
        from alt.pairhold import HoldDesk
        desk = HoldDesk(world, level, now, policy, Geo(client.map()), hold=hold)
    desk.meet(world.roster())
    return desk
