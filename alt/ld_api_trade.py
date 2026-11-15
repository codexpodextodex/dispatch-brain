"""API line (leaders/api/AUDIT.md): trade-ins, priced and paid for what they are.

RULES.md: "A trade-in request has two legs: the new car out, and the customer's old car back. One price covers
both." "In a trade-in gig, put the old car's pickup right after the new car's delivery." A week has 20 such
requests and version 7 quotes none of them: taken at a plain car's cost and fees they were 83% on time and earned 23
euros each (80 saved weeks, 1,116 trade-ins, leaders/api/out/tradein.txt).

Why: drivers want more for a trade-in than its typical fee says (the handbook lists trade-ins and private
addresses among a driver's extras). Only a third of them was booked under 1.1 typical fees; a third found a driver
only at 1.6 and more, after 28 to 34 hours on a schedule that opens at 0.85, and those came late 30 to 55% of the time.

Priced dearer but still paid on a plain car's schedule (`cost_trade_in=0.5`, 12 saved fast weeks,
leaders/api/tradein_cars.py), 9.8 trade-ins a week sell at 1.48 list prices and earn 46 euros each, yet only 76% are
on time: the first booking comes 24 hours after the win, 39% get a deadline warning, the fee finally paid is 1.60
typical fees anyway, and the week as a whole ends 132 +- 237 lower. The drivers' price is paid either way; paid late
it also costs the refund and the dealer's trust.

This desk quotes trade-ins (not premium cars) with
- a cost of 1.5 typical fees in the price, as in that saved test, so the price side is the same;
- at least 18 hours to find the driver;
- a fee schedule of their own: it opens at 1.0 typical fees, reaches 1.6 when drivers plan the day and 2.1 at the
  moment a plain car reaches its late fee.
Everything else is version 7."""
from __future__ import annotations

from dataclasses import replace

from dispatch.desk import Desk
from dispatch.geo import Geo
from dispatch.policy import Params, Policy

COST_MORE = 0.5  # typical fees over a plain car's cost
FIND_HOURS = 18.0
FEES = dict(open_fee=1.0, top_fee=1.6, late_fee=2.1, urgent_top=2.6, open_easy=0.0, open_hard=0.0)


class TradePolicy(Policy):
    def __init__(self, params: Params):
        super().__init__(replace(params, trade_in=1, cost_trade_in=COST_MORE))
        self.two_cars = Policy(replace(params, **FEES))  # only its fee schedule is used

    def find_hours(self, desk: Desk, request: dict) -> float:
        hours = super().find_hours(desk, request)
        return max(hours, FIND_HOURS) if len(request["legs"]) == 2 else hours

    def fees(self, desk: Desk, order: dict, cars: int, urgent: bool) -> list[dict]:
        if len(order["legs"]) == 2:
            self.two_cars.arrivals = self.arrivals  # the brake reads how the week goes
            return self.two_cars.fees(desk, order, cars, urgent)
        return super().fees(desk, order, cars, urgent)


def make(client, world, level: int, now: int, params: Params):
    desk = Desk(world, level, now, TradePolicy(params), Geo(client.map()))
    desk.meet(world.roster())
    return desk
