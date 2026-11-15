"""leaders/bigcars: a long drive is charged for its length only when the driver must be found at short notice.

Reason in one line: on version 10's 80 saved weeks a plain car with a drive of 4 to 7 hours and 48 hours and more to a
weekday last pickup is paid 0.90 to 0.97 typical fees and comes late 3 to 5% of the time (real cost with 86 euros a
late car: 0.95 to 1.02 typical fees, 568 cars), what a short car costs, while the price charges it 1.12 to 1.28
(`cost_drive`); under 48 hours the charge is right (1.04 to 1.25 measured), and from 7 hours of drive it is right or
low at any notice (1.12 to 1.60). So the quote of a later option falls, the dealer of a long car moves to it, and the
same-day and next-morning cars stay as dear as they are. Tables: leaders/bigcars/out/classes.txt and quote.txt.

Everything else is version 10's code: only `Policy.cost` sees a different `cost_drive` for these cars. With the rule
off (`Rule(on=False)`) the desk sends exactly version 10's actions (python -X utf8 leaders/bigcars/check_off.py)."""
from __future__ import annotations

from dataclasses import dataclass, replace

from dispatch import desk as desk_module
from dispatch.desk import Desk
from dispatch.geo import DAY, HOUR, Geo
from dispatch.policy import Params, Policy


@dataclass(frozen=True)
class Rule:
    on: bool = True
    notice: float = 48.0  # hours from the answer to the last pickup from which a long drive is no dearer than a short one
    week_rate: float = 0.0  # the share of `cost_drive` that stays at that notice when the last pickup is on a weekday
    after_rate: float = 1.0  # ... and when it falls after Friday: that Monday carries no cap, and its long cars are late 5 to 10%
    far: float = 7.0  # a drive of this many hours and more keeps the whole charge at any notice: late 11 to 28%
    flat_from: float = 0.0  # under the notice, a drive over this many hours (and under `far`) is charged as this many; 0 is off


class BigPolicy(Policy):
    def __init__(self, params: Params, rule: Rule):
        super().__init__(params)
        self.rule = rule
        self.repriced: dict[float, Params] = {}

    def drive_rate(self, desk: Desk, request: dict, last: int) -> float:
        """What an hour of driving over three costs for this car on an option with this last pickup, in typical fees."""
        p, r = self.p, self.rule
        if not r.on or not self.plain_leg(request):
            return p.cost_drive
        hours = desk.geo.drive(request["legs"][0]) / HOUR
        if hours <= 3 or hours >= r.far:
            return p.cost_drive
        if (last - request["respondBy"]) / HOUR >= r.notice:
            return p.cost_drive * (r.after_rate if last // DAY >= 5 else r.week_rate)
        if r.flat_from and hours > r.flat_from:
            return p.cost_drive * (r.flat_from - 3) / (hours - 3)
        return p.cost_drive

    def cost(self, desk: Desk, request: dict, option: dict, last: int) -> float:
        rate = self.drive_rate(desk, request, last)
        if rate == self.p.cost_drive:
            return super().cost(desk, request, option, last)
        if rate not in self.repriced:
            self.repriced[rate] = replace(self.p, cost_drive=rate)
        kept, self.p = self.p, self.repriced[rate]
        try:
            return super().cost(desk, request, option, last)  # version 10's cost, with this car's charge for length
        finally:
            self.p = kept


def build(client, world, level: int, now: int, params: Params, rule: Rule):
    if params.windows and "driver_late" not in desk_module.WAKE_ON:
        desk_module.WAKE_ON.append("driver_late")  # as dispatch.play.new_desk does for the usual desk
    desk = Desk(world, level, now, BigPolicy(params, rule), Geo(client.map()))
    desk.meet(world.roster())
    return desk


def make(client, world, level: int, now: int, params: Params):
    return build(client, world, level, now, params, Rule(on=False))
