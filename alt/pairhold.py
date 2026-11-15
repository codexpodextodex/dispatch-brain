"""Design A: hold a car back for a partner, so that two cars go as one round trip.

The bet: a round trip is driven for 0.8 of two single fees and takes one driver instead of two, but nine in ten
round trips are lost today because the first car is booked (median 18 minutes after the win) before its partner
is won (median 4.9 hours later; alt/analysis/pairing_window.py). So a plain car with time to spare is not posted
at once: it waits up to `hold_hours`, never past 18:00 of the day it was won, and goes out as soon as a partner is
won, or alone when the wait is over.

Everything else is version 6: the price, the fees, the pairs with gigs that no driver has taken yet."""
from __future__ import annotations

from dataclasses import dataclass

from spread import starter as kit

from dispatch.desk import Desk
from dispatch.geo import DAY, HOUR, Geo, needs_charging
from dispatch.policy import Params, Policy


@dataclass(frozen=True)
class Hold:
    hours: float = 4.0  # how long a car may wait for a partner
    until: float = 18.0  # ... and never past this hour of the day it was won: the last requests come at 18:00
    spare: float = 16.0  # only a car with at least this many hours to its last pickup waits at all
    max_drive: int = 0  # only a car with at most this many minutes of driving waits; 0: any car
    calm: int = 0  # 1: hold only while the policy's guard does not find the week going badly (version 7's `guard`)
    evening: float = 0.0  # a car due two or more days later waits to this hour of the working day before it; 0 is off


class HoldDesk(Desk):
    def __init__(self, *args, hold: Hold = Hold(), **kwargs):
        super().__init__(*args, **kwargs)
        self.hold = hold
        self.held: dict[str, int] = {}  # order id -> the minute it goes out alone

    def post(self, order: dict, legs: list[int], retry: kit.Retry = kit.Retry()) -> None:
        leg = order["legs"][0]
        private = leg["pickup"]["privateAddress"] or leg["delivery"]["privateAddress"]  # a booked slot: never wait
        if retry != kit.Retry() or not self.plain(order) or order["id"] in self.held or private:
            return super().post(order, legs, retry)
        if self.pair_held(order):
            return
        last = self.last_pickup.get(order["id"], order["lastPickupAt"])
        release = min(self.now + int(self.hold.hours * HOUR), self.now // DAY * DAY + int(self.hold.until * HOUR))
        if self.hold.evening and last // DAY >= self.now // DAY + 2:
            release = self.evening_before(last)
        long = bool(self.hold.max_drive) and self.geo.drive(leg) > self.hold.max_drive
        careful = bool(self.hold.calm) and self.policy.p.guard and self.policy.careful(self)
        if last - self.now < self.hold.spare * HOUR or release <= self.now or long or careful:
            return super().post(order, legs, retry)  # no time to wait: version 6 posts it, in a pair if it can
        if not self.post_pair(order):  # a round trip with a car whose gig no driver has taken yet, as version 6
            self.held[order["id"]] = release
            self.stats["held"] += 1

    def pairable(self, request: dict, last: int) -> bool:
        """Whether a request, once won, would make a round trip with a car of ours: one whose gig no driver has
        taken (version 6), or one we hold back. With `pair_bonus` the price of such a request is lower, because
        its driver costs 0.8 of two single fees; holding makes many more such partners."""
        if super().pairable(request, last):
            return True
        new = {"id": request["id"], "legs": request["legs"], "lastPickupAt": last, "deliveredAt": [None] * len(request["legs"])}
        if not self.policy.p.pairs or not self.plain(new):
            return False
        held = [self.orders[order_id] for order_id in self.held if order_id in self.orders]
        return any(self.pair_start(new, other) is not None or self.pair_start(other, new) is not None for other in held if self.plain(other))

    def evening_before(self, last: int) -> int:
        """The evening before a car's last pickup day, when drivers plan it; Friday's for a Monday pickup. Until
        then the car waits for a partner, and does not compete with the cars due sooner for drivers' attention
        (sim/FINDINGS_FOR_MAIN.md: views fall with our open gigs to the power -0.39)."""
        day = last // DAY - 1
        day -= {5: 1, 6: 2}.get(day % 7, 0)
        return day * DAY + int(self.hold.evening * HOUR)

    def pair_held(self, order: dict) -> bool:
        """Posts a new car with a held car as one round trip, the one that leaves the latest start."""
        best = None
        for other_id in self.held:
            other = self.orders.get(other_id)
            if other is None or not self.plain(other):  # held cars are never private: see `post`
                continue
            for first, second in ((order, other), (other, order)):
                start = self.pair_start(first, second)
                if start is not None and (best is None or start > best[0]):
                    best = (start, first, second, other_id)
        if best is None:
            return False
        start, first, second, other_id = best
        stops = []
        for each in (first, second):
            leg = each["legs"][0]
            km = self.geo.km[(leg["pickup"]["placeId"], leg["delivery"]["placeId"])]
            stops += [{"orderId": each["id"], "leg": 0, "kind": "pickup", "withPlates": False, "withCharging": needs_charging(leg, km)},
                      {"orderId": each["id"], "leg": 0, "kind": "delivery"}]
        typical = (self.typical(first) + self.typical(second)) * self.policy.p.pair_fee
        manual = any(self.facts(self.requests[each["id"]]).manual for each in (first, second))
        action = {"type": "post", "stops": stops, "audience": {"experienced": False, "manualLicence": manual}, "schedule": self.policy.schedule(self, typical, start, False)}
        self.send()
        result = self.world.act([action])[0]
        if result["ok"] is not True:
            self.refused[f"pair: {result['reason'][:80]}"] += 1
            return False
        del self.held[other_id]
        self.carry(action, result["id"])
        self.pairs[result["id"]] = start
        self.stats["pairs_posted"] += 1
        self.stats["pairs_from_hold"] += 1
        return True

    def tick(self) -> None:
        for order_id, release in list(self.held.items()):
            order = self.orders.get(order_id)
            if order is None or None not in order["deliveredAt"]:
                del self.held[order_id]
            elif self.now >= release:
                del self.held[order_id]
                super().post(order, kit.undelivered(order))
        super().tick()

    def withdraw(self, order_id: str) -> bool:
        self.held.pop(order_id, None)  # a changed order is posted again from scratch
        return super().withdraw(order_id)


def make(client, world, level: int, now: int, params: Params, hold: Hold = Hold()):
    desk = HoldDesk(world, level, now, Policy(params), Geo(client.map()), hold=hold)
    desk.meet(world.roster())
    return desk
