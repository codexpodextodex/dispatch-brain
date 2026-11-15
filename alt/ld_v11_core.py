"""leaders/lead: version 11's desk (dispatch/trade.py) with ONE of two small changes, for testing on version 11.

  hope    how much an unanswered quote counts as a car already due on its day. Version 11 counts it by its chance to be
          won (`Policy.hoped`), so inside a batch every later car is quoted against a fuller day. In the 20:00 live test
          final we won 46% of plain requests in a batch of five or more against 53% for the nine teams above us, and 47%
          against 44% alone (leaders/juhus/out/who_wins_2000.txt); in our own 80 saved weeks the sixth and later cars
          of a batch earn 51.3 a car against 41.7 for the first five and are late 4.1% against 7.5%
          (leaders/bulkbrake/REPORT.md). `hope` scales that count: 1 is version 11, 0.5 half, 0 none.
  trade   other edges for the trade-in fit test (dispatch/trade.py `Trade`): version 11 quotes 8.3 of 22 trade-in
          requests a week and wins 4.7 at 74 euros a car, 6.1% late.

  flat    what a car pays for its place on a full day. Version 11 multiplies the car's OWN cost by the day's load term, so
          on the same day a car with a typical fee of 25 euros pays 16 and one of 87 euros pays 57, though one more car
          under 4 hours of drive costs the day's other cars the same lateness whatever its size (leaders/capgigs/out/
          counts_table.txt: 8 more short cars +0.19 points late, 8 more of 2 to 4 hours +0.22; long cars are the
          different case and keep version 11's charge). `flat_ref` (euros) makes every car under `flat_hours` of drive
          pay load term x flat_ref: the smallest cars pay more for a place, the middle ones less. The teams above us
          carry fewer of the smallest cars and more of the middle ones (leaders/juhus/out/who_wins_*.txt). 0 is off.

With `hope=1`, `flat_ref=0` and version 11's `Trade` this module builds exactly version 11's desk.
"""
from __future__ import annotations

from dataclasses import replace

from dispatch import desk as desk_module
from dispatch.geo import DAY, HOUR, Geo
from dispatch.policy import Params
from dispatch.trade import Trade, TradeDesk, TradePolicy

V11 = dict(on=True, line=True, evening=True)


def build(client, world, level: int, now: int, params: Params, hope: float = 1.0, flat_ref: float = 0.0, flat_hours: float = 4.0, **trade):
    class LeadPolicy(TradePolicy):
        slot = None  # while one car's cost is asked: what its place costs against its own cost

        def cost(self, desk, request, option, last):
            p, leg = self.p, request["legs"][0]
            capped = p.day_cap and not (p.cap_week_only and last // DAY >= 5)
            if not flat_ref or not capped or len(request["legs"]) != 1 or desk.geo.drive(leg) >= flat_hours * HOUR:
                return super().cost(desk, request, option, last)
            self.p = replace(p, day_cap=0.0)  # the car's own cost, without the day's load
            try:
                own = super().cost(desk, request, option, last)
            finally:
                self.p = p
            self.slot = 100 * flat_ref / option["listPriceCents"] / own if own > 0 else None
            try:
                return super().cost(desk, request, option, last)  # version 11's cost, the load term on flat_ref
            finally:
                self.slot = None

        def cap_weight(self, desk, leg):
            weight = super().cap_weight(desk, leg)
            return weight * self.slot if self.slot is not None else weight

        def quote(self, desk, request):
            out = super().quote(desk, request)
            waiting = self.hoped.get(request["id"])
            if hope != 1.0 and waiting is not None:
                self.hoped[request["id"]] = (waiting[0], waiting[1] * hope)
            return out

    if params.windows and "driver_late" not in desk_module.WAKE_ON:
        desk_module.WAKE_ON.append("driver_late")  # as dispatch.play.new_desk does
    desk = TradeDesk(world, level, now, LeadPolicy(params, Trade(**{**V11, **trade})), Geo(client.map()))
    desk.meet(world.roster())
    return desk


def make(client, world, level: int, now: int, params: Params):
    return build(client, world, level, now, params)  # version 11 through this module: the check
