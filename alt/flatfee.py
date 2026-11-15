"""Design B: one fee per gig, from the first minute to the deadline warning.

The bet: drivers learn from our gigs how far a fee rises and how long it stays open (rules, "Drivers"), and a
driver who expects a raise waits for it. Version 6 opens at 0.85 typical fees and climbs to 1.2: a fifth of its
bookings come from a driver who saw the gig cheaper and waited for the raise (EXPERIMENTS.md 10). A desk whose
fees never rise before the warning teaches every driver that waiting pays nothing, so a driver whom the fee pays
books at first look. This only shows if every gig of the week follows it, pairs included.

`fee` is the one fee, in noise-free typical fees. With `top` set, the fee steps once to `top` at the moment
version 6 reaches its top fee (the evening before an early pickup, otherwise 6 hours before the last pickup):
one raise, at the time drivers plan the day. With `thin` set, a car going to a town with fewer than 30 drivers
within 30 km opens at `thin` instead of `fee`: there a driver who books at first look needs more (version 6's
cars to such towns are booked at a p75 of 1.08 against 0.85 elsewhere; alt/analysis/fee_levels.py).
After the deadline warning, as version 6."""
from __future__ import annotations

from dataclasses import dataclass, replace

from dispatch.desk import Desk
from dispatch.geo import DAY, HOUR, Geo
from dispatch.policy import Params, Policy


@dataclass(frozen=True)
class Flat:
    fee: float = 0.95
    top: float = 0.0  # 0: no raise at all before the warning
    thin: float = 0.0  # 0: the same fee for every car


class FlatPolicy(Policy):
    def __init__(self, params: Params, flat: Flat):
        super().__init__(replace(params, open_fee=flat.fee))  # the one fee is the opening fee, pairs included
        self.flat = flat

    def opening(self, desk: Desk, order: dict) -> float:
        thin = desk.near.get(order["legs"][0]["delivery"]["placeId"], 0) < 30
        return self.flat.thin if self.flat.thin and thin else self.flat.fee

    def rising(self, now: int, last: int, warning: int, step, opening: float) -> list[dict]:
        steps = [step(now, opening)]
        if self.flat.top:
            p = self.p
            top_at = last // DAY * DAY - DAY + p.evening_hour * HOUR if last % DAY < p.early_hour * HOUR else last - p.lead_hours * HOUR
            if now < top_at < warning:
                steps.append(step(top_at, self.flat.top))
        return steps


def make(client, world, level: int, now: int, params: Params, flat: Flat = Flat()):
    desk = Desk(world, level, now, FlatPolicy(params, flat), Geo(client.map()))
    desk.meet(world.roster())
    return desk
