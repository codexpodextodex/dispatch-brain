"""API line (leaders/api/AUDIT.md): trade-ins as alt/ld_api_trade.py, without the two kinds that lose money however
they are paid (leaders/api/tradein_kinds.py, 588 trade-ins on a plain car's fees):

- a first leg of 5 hours and more: the two legs pass the 12-hour limit of a gig with two cars, the old car then
  goes alone and must be collected inside the customer's hour (63% on time, -109 euros a car);
- a last pickup at 18:00 or later, an evening hour at the customer's (62% on time, -77 euros a car).

Everything else as ld_api_trade: a cost of 1.5 typical fees in the price, 18 hours to find the driver, fees that open
at 1.0 typical fees and reach 1.6 when drivers plan the day."""
from __future__ import annotations

from alt.ld_api_trade import TradePolicy
from dispatch.desk import Desk
from dispatch.geo import DAY, HOUR, Geo
from dispatch.policy import Params

LONGEST_DRIVE = 5 * HOUR
EVENING = 18 * HOUR


class SelectPolicy(TradePolicy):
    geo: Geo

    def wanted(self, request: dict) -> bool:
        if not super().wanted(request):
            return False
        if len(request["legs"]) != 2:
            return True
        leg = request["legs"][0]
        drive = self.geo.drive(leg)
        booked_end = leg["delivery"]["window"]["to"]  # the customer's hour ends; the new car is due 30 minutes later
        return drive < LONGEST_DRIVE and (booked_end + 30 - drive) % DAY < EVENING


def make(client, world, level: int, now: int, params: Params):
    policy = SelectPolicy(params)
    policy.geo = Geo(client.map())
    desk = Desk(world, level, now, policy, policy.geo)
    desk.meet(world.roster())
    return desk
