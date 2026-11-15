"""leaders/routes: which cars go in one gig, treated as a route. Version 7 with the parts named in `Routes`.
Prices are version 7's to the cent; only gigs and their fees differ. The modules ld_routes_* set the parts.

What the saved two-car gigs say (leaders/routes/q2_take.py, 7,900 gigs under nine pair settings):

1. Drivers answer to the fee over the ROUTE, not over the cars' typical fees. Route line (cents) =
   1604 + 38.44 x (road minutes of the cars' drives + 0.5 x (road minutes between the cars + from the last delivery
   back to the first pickup)). A gig that opens at 0.60 to 0.65 of that line is driven 89% of the time (cars on
   time 95.0%), at 0.70 to 0.75 it is driven 95% (97.4%), at 0.75 to 0.80 97% (97.5%). Version 7 opens every pair
   at 0.68 of the two typical fees, which is 0.50 to 0.95 of the route line: a third of its pairs open under 0.65.
   The typical fee's noise is in it too: pairs whose typical fees lie 10% under their road lines are driven 83%.
   -> `geo_fee`: the pair's fees are `k` x route line (the schedule then opens at 0.85 of that).
2. With the fee on the route, a wider pair is paid for its extra trip, so the limit can be the money:
   -> `gate`: a pair is posted only when its route line is at most `gate` x the two cars' own lines
      (its fee then stays about a tenth under the two cars alone); `hop`, `back` are the outer limits.
3. The one loss of holding is the first look. A car's only certain partner within minutes is a request of ours
   that is still waiting for its answer (15 minutes at most):
   -> `wait`: a new car is held only while such a quote is open, and goes out the minute it is answered.
4. -> `cars`: a new car may also join a gig of two that no driver has taken yet (same rules, 12 hours of road).
5. Version 7 forgets a booked pair; when its driver gives it back, a new order can take one of its cars and
   leave the other without a gig (leaders/api/orphans.py). -> `pair_fix`: a returned gig is known again.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional

from spread import starter as kit

from dispatch.desk import Desk
from dispatch.geo import DAY, HOUR, PLATES_MINUTES, Geo, last_pickup, needs_charging, open_span
from dispatch.notes import apply
from dispatch.policy import ROAD_BASE, ROAD_MINUTE, Params, Policy


@dataclass(frozen=True)
class Routes:
    geo_fee: bool = True  # a gig of two or more cars is paid by its route line, not by the cars' typical fees
    k: float = 0.82  # ... its fees are this share of the route line (the opening fee is 0.85 of that: 0.70)
    share: float = 0.5  # a road minute between cars, or back to the start, counts this much of a minute at the wheel
    hop: int = 0  # the most road minutes from one car's delivery to the next car's pickup; 0 keeps version 7's 60
    back: int = 0  # ... and from the last delivery back to the first pickup; 0 keeps version 7's 90
    gate: float = 0.0  # post a gig only when its route line is at most this many times its cars' own lines; 0 is off
    cars: int = 2  # the most cars in one gig
    wait: bool = False  # hold a new car while a quote of ours that would make a gig with it awaits its answer
    spare: float = 16.0  # ... only a car with at least this many hours to its last pickup
    chance: float = 0.15  # ... and only for a quote with at least this chance to win
    until: float = 17.5  # ... and never after this hour: the last answers come at 18:15
    pair_fix: bool = True  # a gig of two or more that a driver gives back is known as such again


class RoutesDesk(Desk):
    def __init__(self, world, level: int, now: int, policy: Policy, geo: Geo, routes: Routes = Routes()):
        super().__init__(world, level, now, policy, geo)
        self.r = routes
        self.starts: dict[str, int] = {}  # gig of two or more cars -> its last start, kept while a driver holds it
        self.held: dict[str, int] = {}  # order id -> the minute it goes out alone
        self.let_go: set[str] = set()  # orders that have waited once

    # The route of a gig.

    def road(self, a: str, b: str) -> int:
        return 0 if a == b else self.geo.minutes[(a, b)]

    def route_line(self, seq: list[dict]) -> float:
        """What the work of a gig is worth by the road, in cents: the typical fee's own line for one car alone."""
        legs = [o["legs"][0] for o in seq]
        drives = sum(self.geo.minutes[(leg["pickup"]["placeId"], leg["delivery"]["placeId"])] for leg in legs)
        between = sum(self.road(legs[i]["delivery"]["placeId"], legs[i + 1]["pickup"]["placeId"]) for i in range(len(legs) - 1))
        back = self.road(legs[-1]["delivery"]["placeId"], legs[0]["pickup"]["placeId"]) if len(legs) > 1 else drives
        return ROAD_BASE + ROAD_MINUTE * (drives + (self.r.share * (between + back) if len(legs) > 1 else 0))

    def own_lines(self, seq: list[dict]) -> float:
        return sum(self.route_line([o]) for o in seq)

    def worth(self, seq: list[dict]) -> bool:
        return not self.r.gate or self.route_line(seq) <= self.r.gate * self.own_lines(seq)

    def pair_start(self, first: dict, second: dict) -> Optional[int]:
        start = super().pair_start(first, second)
        return start if start is not None and self.worth([first, second]) else None

    def route_start(self, seq: list[dict]) -> Optional[int]:
        """`pair_start` for a string of cars: the last minute to collect the first one so that every car is on time."""
        if len(seq) == 2:
            return self.pair_start(seq[0], seq[1])
        p, legs = self.policy.p, [o["legs"][0] for o in seq]
        hops = [self.road(legs[i]["delivery"]["placeId"], legs[i + 1]["pickup"]["placeId"]) for i in range(len(legs) - 1)]
        drives = [self.geo.drive(leg) for leg in legs]
        if max(hops) > p.pair_hop or self.road(legs[-1]["delivery"]["placeId"], legs[0]["pickup"]["placeId"]) > p.pair_back:
            return None
        if sum(drives) + sum(hops) > 12 * HOUR or not self.worth(seq):
            return None
        lasts = [self.last_pickup.get(o["id"], o["lastPickupAt"]) for o in seq]
        start = lasts[-1]
        for i in range(len(seq) - 2, -1, -1):
            start = min(lasts[i], start - drives[i] - hops[i])
        opens = open_span(legs[0]["pickup"], start // DAY)
        if opens is None or start < max(opens[0], legs[0]["pickup"]["window"]["from"]) or start // DAY != lasts[-1] // DAY:
            return None
        at = start
        for i in range(1, len(seq)):  # the driver's day from the last start: no long wait for a car, every site open
            arrive = at + drives[i - 1] + hops[i - 1]
            span = open_span(legs[i]["pickup"], arrive // DAY)
            ready = max(legs[i]["pickup"]["window"]["from"], span[0] if span else 10 ** 9)
            if span is None or ready > arrive + 2 * HOUR or max(arrive, ready) > min(lasts[i], span[1]):
                return None
            at = max(arrive, ready)
        if start - self.now < (p.pair_split_hours + 2) * HOUR:
            return None
        return start

    # Posting.

    def post(self, order: dict, legs: list[int], retry: kit.Retry = kit.Retry()) -> None:
        leg = order["legs"][0]
        if (not self.r.wait or retry != kit.Retry() or order["id"] in self.let_go or order["id"] in self.held or not self.plain(order)
                or leg["pickup"]["privateAddress"] or leg["delivery"]["privateAddress"]):
            return super().post(order, legs, retry)
        if self.join_held(order) or self.post_pair(order):
            return
        until = self.partner_due(order)
        last = self.last_pickup.get(order["id"], order["lastPickupAt"])
        if until is None or last - self.now < self.r.spare * HOUR or self.now % DAY >= self.r.until * HOUR:
            return super().post(order, legs, retry)
        self.held[order["id"]] = until
        self.stats["held"] += 1

    def partner_due(self, order: dict) -> Optional[int]:
        """The minute by which every open quote of ours that would make a gig with this car is answered; None when there is none."""
        due = None
        for request_id, (_, chance) in self.policy.hoped.items():
            request, markups = self.requests.get(request_id), self.policy.quoted.get(request_id)
            if request is None or not markups or request_id in self.orders or request["respondBy"] < self.now or chance < self.r.chance:
                continue
            last = self.quoted_last(request, markups)
            if last is None:
                continue
            new = {"id": request_id, "legs": request["legs"], "lastPickupAt": last, "deliveredAt": [None] * len(request["legs"])}
            if self.plain(new) and (self.pair_start(order, new) is not None or self.pair_start(new, order) is not None):
                due = max(due or 0, request["respondBy"])
        return due

    def quoted_last(self, request: dict, markups: dict) -> Optional[int]:
        """The last pickup of a request on the first option we quoted: the one a dealer most often takes."""
        facts = self.facts(request)
        leg = apply(request["legs"][0], facts)
        option = next((o for o in request["options"] if o["kind"] in markups), None)
        if option is None or leg["pickup"]["privateAddress"]:
            return None
        deadline = min(option["deadline"], facts.deadline or option["deadline"])
        return last_pickup(leg, deadline, self.geo.drive(request["legs"][0]) + (PLATES_MINUTES if facts.plates else 0))

    def join_held(self, order: dict) -> bool:
        """Posts a new car with a car we hold as one gig: the pair with the latest start."""
        best = None
        for other_id in self.held:
            other = self.orders.get(other_id)
            if other is None or not self.plain(other):
                continue
            for first, second in ((order, other), (other, order)):
                start = self.pair_start(first, second)
                if start is not None and (best is None or start > best[0]):
                    best = (start, [first, second], other_id)
        if best is None:
            return False
        start, seq, other_id = best
        del self.held[other_id]
        self.let_go.add(other_id)
        if self.post_route(seq, start, None, order):
            self.stats["pairs_from_wait"] += 1
            return True
        return False

    def post_pair(self, order: dict) -> bool:
        """Version 7's rule, with the route's fee: a new order and an order whose gig no driver has taken yet go as
        one gig in place of that gig. With `cars` over 2 the new order may also join an open gig of two."""
        if not self.plain(order):
            return False
        best = None
        for other in self.orders.values():
            gigs = self.gigs_of(other["id"])
            if other["id"] == order["id"] or len(gigs) != 1 or gigs[0] in self.booked or gigs[0] in self.pairs or not self.plain(other):
                continue
            if self.is_pair(gigs[0]):
                continue  # a returned gig of two that we no longer follow: never take one car out of it
            for first, second in ((order, other), (other, order)):
                start = self.pair_start(first, second)
                if start is not None and (best is None or start > best[0]):
                    best = (start, [first, second], gigs[0])
        if best is None and self.r.cars > 2:
            for gig_id in list(self.pairs):
                if gig_id in self.booked or gig_id not in self.posts:
                    continue
                members = [self.orders.get(i) for i in dict.fromkeys(stop["orderId"] for stop in self.posts[gig_id]["stops"])]
                if None in members or len(members) >= self.r.cars or order["id"] in (m["id"] for m in members) or not all(self.plain(m) for m in members):
                    continue
                for at in range(len(members) + 1):
                    seq = members[:at] + [order] + members[at:]
                    start = self.route_start(seq)
                    if start is not None and (best is None or start > best[0]):
                        best = (start, seq, gig_id)
        if best is None:
            return False
        start, seq, old_gig = best
        return self.post_route(seq, start, old_gig, order)

    def post_route(self, seq: list[dict], start: int, old_gig: Optional[str], new: dict) -> bool:
        """Posts a string of cars as one gig, in place of `old_gig` when given. False when the world refuses: every
        car but the new one then has a gig of its own again, and the caller posts the new one."""
        self.send()  # the world must have every earlier action before we take the other gig out
        if old_gig is not None:
            if self.world.act([{"type": "withdraw", "gigId": old_gig}])[0]["ok"] is not True:
                return False
            self.forget(old_gig)
        stops = []
        for each in seq:
            leg = each["legs"][0]
            km = self.geo.km[(leg["pickup"]["placeId"], leg["delivery"]["placeId"])]
            stops += [{"orderId": each["id"], "leg": 0, "kind": "pickup", "withPlates": False, "withCharging": needs_charging(leg, km)},
                      {"orderId": each["id"], "leg": 0, "kind": "delivery"}]
        if self.r.geo_fee:
            typical = self.r.k * self.route_line(seq)
        else:
            typical = sum(self.typical(each) for each in seq) * self.policy.p.pair_fee
        manual = any(self.facts(self.requests[each["id"]]).manual for each in seq)
        action = {"type": "post", "stops": stops, "audience": {"experienced": False, "manualLicence": manual}, "schedule": self.policy.schedule(self, typical, start, False)}
        result = self.world.act([action])[0]
        if result["ok"] is not True:  # the world does not accept the gig: every car goes alone
            self.refused[f"pair: {result['reason'][:80]}"] += 1
            self.alone.update(each["id"] for each in seq)
            for each in seq:
                if each["id"] != new["id"]:
                    self.let_go.add(each["id"])
                    self.post(each, [0])
            return False
        self.carry(action, result["id"])
        self.pairs[result["id"]] = self.starts[result["id"]] = start
        self.stats["pairs_posted"] += 1
        self.stats[f"gigs_of_{len(seq)}"] += 1
        self.stats["route_line"] += round(self.route_line(seq))
        self.stats["route_own"] += round(self.own_lines(seq))
        self.stats["route_open"] += action["schedule"][0]["feeCents"]
        return True

    # Plumbing.

    def tick(self) -> None:
        for order_id, until in list(self.held.items()):
            order = self.orders.get(order_id)
            if order is None or None not in order["deliveredAt"]:
                del self.held[order_id]
            elif self.now >= until:
                del self.held[order_id]
                self.let_go.add(order_id)
                super().post(order, kit.undelivered(order))
        super().tick()

    def withdraw(self, order_id: str) -> bool:
        self.held.pop(order_id, None)  # a changed order is posted again from scratch
        self.let_go.add(order_id)
        return super().withdraw(order_id)

    def handle(self, event: dict) -> None:
        super().handle(event)
        if self.r.pair_fix and event["kind"] in ("gig_dropped", "no_show") and self.is_pair(event["gigId"]) and event["gigId"] not in self.pairs:
            self.pairs[event["gigId"]] = self.starts.get(event["gigId"], self.now)
            self.stats["pairs_reopened"] += 1

    def rejoin(self, snapshot: dict, history: list) -> None:
        kit.Desk.rejoin(self, snapshot, history)
        for gig in snapshot["gigs"]:  # an open gig of two or more: take it apart when its time comes, as before the restart
            if gig["status"] == "open" and self.is_pair(gig["id"]):
                seq = [self.orders.get(order_id) for order_id in dict.fromkeys(stop["orderId"] for stop in gig["stops"])]
                self.pairs[gig["id"]] = (self.route_start(seq) if None not in seq else None) or self.now


def build(client, world, level: int, now: int, params: Params, routes: Routes):
    if routes.hop or routes.back:
        params = replace(params, pair_hop=routes.hop or params.pair_hop, pair_back=routes.back or params.pair_back)
    desk = RoutesDesk(world, level, now, Policy(params), Geo(client.map()), routes)
    desk.meet(world.roster())
    return desk
