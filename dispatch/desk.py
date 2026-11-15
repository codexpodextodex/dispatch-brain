"""The desk: the kit starter's plumbing (posting, retries after failed visits, reposts, restarts) with our
decisions in place of its own. The starter quotes the list price and pays the typical fee; we ask the policy."""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Optional

from spread import starter as kit
from spread.client import World

from .geo import DAY, HOUR, PLATES_MINUTES, Geo, last_pickup, needs_charging, neighbours, open_span
from .notes import Facts, apply, read
from .policy import Policy

# The events that need an answer. The rest arrive with the next event that does.
WAKE_ON = ["price_request", "order_won", "order_changed", "order_cancelled", "visit_failed", "gig_expired", "deadline_close"]


class Desk(kit.Desk):
    def __init__(self, world: World, level: int, now: int, policy: Policy, geo: Geo):
        super().__init__(world, level, now)
        self.policy, self.geo = policy, geo
        self.drivers = 800  # how many drivers the week has; `meet` reads the driver list
        self.near: dict[str, int] = {}  # place -> the drivers who live within 30 km of it
        self.reach: dict[str, int] = {}  # ... and within 60 km: a thin town beside a city borrows the city's drivers
        self.around: dict[str, int] = {}  # ... within the policy's own radius
        self.longer: dict[str, int] = {}  # order id -> a typical fee for the place the dealer moved its car to
        self.asked: dict[str, dict[str, int]] = {}  # request id -> the prices we quoted
        self.read: dict[str, Facts] = {}  # request id -> what its note says
        self.last_pickup: dict[str, int] = {}  # order id -> the last minute to collect it on time, as the note changes it
        self.pairs: dict[str, int] = {}  # gig id of a round trip -> the last minute to start it
        self.alone: set[str] = set()  # orders that go alone from now on: their pair found no driver, or was taken apart
        self.forecasts: list[dict] = []
        self.viewers: dict[str, dict[str, int]] = {}  # gig -> driver -> the minute of their last look at it
        self.offered: dict[str, dict[str, int]] = {}  # gig -> driver -> the minute we sent them a direct offer
        self.offers_on: Counter = Counter()  # (driver, day) -> direct offers sent: the rules allow three
        self.holder: dict[str, str] = {}  # gig -> the driver who has booked it
        self.rescued: set[str] = set()  # orders whose gig we raised on the morning of their last pickup
        self.night_drops: Counter = Counter()  # day -> bookings for that day given back in its first hour
        self.flu_day = -1  # the day we take for the flu day, once its sign has shown
        self.warnings: list[int] = []  # the minutes at which a deadline warning came: an order had no driver 3 hours before its last pickup
        self.warned: set[str] = set()  # the orders that have had one
        self.held: dict[str, int] = {}  # order -> the minute it goes out alone: cars that wait for a round-trip partner (`pair_hold`).
        # Not a book to rebuild: the minute comes from the request, so after a restart the same car is held to the same minute
        self.stats: Counter = Counter()  # what happened, for the lab's tables
        self.ledger: dict[str, int] = defaultdict(int)  # account lines by kind, in cents
        self.refused: Counter = Counter()  # why the world refused an action

    # The decisions: the policy makes them.

    def quote(self, request: dict) -> None:
        self.requests[request["id"]] = request
        prices = self.policy.quote(self, request)
        if request["id"] in self.policy.quoted:  # a real quote, not a decline
            self.stats[f"quoted_day{request['arrivedAt'] // 1440}"] += 1
        if prices:
            self.asked[request["id"]] = prices
            self.outbox.append({"type": "quote", "requestId": request["id"], "prices": prices})

    def fees_for(self, order: dict, cars: int) -> list[dict]:
        return self.policy.fees(self, order, cars, urgent=order["id"] in self.urgent)

    # What the policy asks the desk.

    def meet(self, roster: list) -> None:
        """Reads the driver list, public from the first minute: how many drivers the week has and where they live."""
        homes = Counter(driver["homePlaceId"] for driver in roster)
        self.drivers = len(roster)
        self.near = {place: sum(homes[other] for other in neighbours(self.geo, place)) for place in self.geo.at}
        self.reach = {place: sum(homes[other] for other in neighbours(self.geo, place, 60)) for place in self.geo.at}
        self.around = {place: sum(homes[other] for other in neighbours(self.geo, place, self.policy.p.thin_km)) for place in self.geo.at}

    def thin(self, place: str) -> float:
        """How thin the drivers are around a place: 1 with nobody near it, 0.5 with 30, towards 0 with hundreds."""
        return 1 / (1 + self.around.get(place, 100) / 30)

    def thinness(self, leg: dict) -> float:
        """How thin the drivers are at a car's two ends, from 0 to 2. It says more about whether a car arrives
        on time than how busy the day is: the driver comes from near one end, and goes home from the other."""
        return self.thin(leg["pickup"]["placeId"]) + self.thin(leg["delivery"]["placeId"])

    def typical(self, order: dict) -> float:
        """The typical fee of an order: the request's, or more when the dealer has sent the car further since."""
        return max(self.requests[order["id"]]["referenceFeeCents"], self.longer.get(order["id"], 0))

    def due(self, day: int, thin_only: bool = False) -> float:
        """Our cars that must be collected on a day and are not delivered yet. With `thin_only`, each car counts by
        how few drivers live near its two ends."""
        return sum(min(1.0, self.thinness(order["legs"][0]) / 0.8) if thin_only else 1 for order_id, order in self.orders.items()
                   if None in order["deliveredAt"] and self.last_pickup.get(order_id, order["lastPickupAt"]) // DAY == day)

    def strain(self) -> float:
        """The share of our cars that had no driver 3 hours before their last pickup, over the last 24 hours.
        Three in four such cars arrive late, so this is the first hard sign that drivers are short today."""
        since = self.now - DAY
        warned = sum(1 for at in self.warnings if at > since)
        at_risk = sum(1 for order_id, order in self.orders.items() if since < self.last_pickup.get(order_id, order["lastPickupAt"]) - 3 * HOUR <= self.now)
        return (warned + 1) / (at_risk + 30)  # starts at the 3% of a healthy week

    def driver_hours(self, leg: dict) -> float:
        """The hours a car takes a driver: the trip to the car, the drive and the trip home. Over 14,800 delivered
        cars the two trips are 54% of it, and they are long where few drivers live (swarm/portfolio)."""
        def trip(place: str, table: tuple) -> int:
            near = self.near.get(place, 0)
            return next(minutes for under, minutes in table if near < under)
        to_car = trip(leg["pickup"]["placeId"], ((10, 115), (30, 112), (100, 100), (300, 84), (10 ** 9, 56)))
        home = trip(leg["delivery"]["placeId"], ((10, 101), (30, 78), (100, 55), (300, 60), (10 ** 9, 22)))
        return (to_car + self.geo.minutes[leg["pickup"]["placeId"], leg["delivery"]["placeId"]] + home) / 60

    def pairable(self, request: dict, last: int) -> bool:
        """Whether a request, once won, would make a round trip with one of our cars that still waits for a driver."""
        if not self.policy.p.pairs:
            return False
        new = {"id": request["id"], "legs": request["legs"], "lastPickupAt": last, "deliveredAt": [None] * len(request["legs"])}
        if not self.plain(new):
            return False
        for other in self.orders.values():
            gigs = self.gigs_of(other["id"])
            if len(gigs) != 1 or gigs[0] in self.booked or gigs[0] in self.pairs or not self.plain(other):
                continue
            if self.pair_start(new, other) is not None or self.pair_start(other, new) is not None:
                return True
        held = [self.orders[order_id] for order_id in self.held if order_id in self.orders]
        return any(self.pair_start(new, other) is not None or self.pair_start(other, new) is not None for other in held if self.plain(other))

    def snow_on(self, leg: dict, day: int) -> bool:
        """Whether snow is forecast at the pickup or the delivery place of a leg at some hour of a day."""
        places = {leg["pickup"]["placeId"], leg["delivery"]["placeId"]}
        return any(f["from"] < (day + 1) * DAY and f["to"] > day * DAY and not places.isdisjoint(f["placeIds"]) for f in self.forecasts)

    def facts(self, request: dict) -> Facts:
        if request["id"] not in self.read:
            self.read[request["id"]] = read(request["note"], request["arrivedAt"])
        return self.read[request["id"]]

    # Posting: one car, as its note says.

    def post(self, order: dict, legs: list[int], retry: kit.Retry = kit.Retry()) -> None:
        """Posts an order's legs. With `pair_hold`, a newly won plain car first looks for a partner among the cars that
        wait, and otherwise waits itself for a while when it has the time."""
        p, leg = self.policy.p, order["legs"][0]
        if (not p.pair_hold or not p.pairs or p.notes != "ours" or retry != kit.Retry() or order["id"] in self.held or not self.plain(order)
                or leg["pickup"]["privateAddress"] or leg["delivery"]["privateAddress"]):
            return self.post_now(order, legs, retry)
        if self.pair_held(order):
            return
        last = self.last_pickup.get(order["id"], order["lastPickupAt"])
        won = self.requests[order["id"]]["respondBy"] if order["id"] in self.requests else self.now
        release = min(won + int(p.pair_hold * HOUR), won // DAY * DAY + int(p.hold_until * HOUR))
        if p.hold_after and last // DAY >= 5:  # due after Friday: the partner may still be won on Friday
            release = max(release, 4 * DAY + int(p.hold_after * HOUR))
        if last - self.now < p.hold_spare * HOUR or release <= self.now or self.geo.drive(leg) > p.hold_drive:
            return self.post_now(order, legs, retry)  # no time to wait, or a long drive
        if not self.post_pair(order):  # a round trip with a car whose gig no driver has taken yet
            self.held[order["id"]] = release
            self.stats["held"] += 1

    def pair_held(self, order: dict) -> bool:
        """Posts a new car with a car that waits as one round trip: the one that leaves the latest start."""
        best = None
        for other_id in self.held:
            other = self.orders.get(other_id)
            if other is None or not self.plain(other):
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
        opens = first["legs"][0]["pickup"]["window"]["from"]
        if self.policy.p.windows and start >= max(opens, self.now) + HOUR:
            stops[0]["window"] = {"from": opens, "to": start}
        typical = self.policy.pair_typical(self, first, second)
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

    def post_now(self, order: dict, legs: list[int], retry: kit.Retry = kit.Retry()) -> None:
        if self.policy.p.notes != "ours":
            return self.post_as_kit(order, legs, retry)
        if self.policy.p.pairs and retry == kit.Retry() and self.post_pair(order):
            return
        facts = self.facts(self.requests[order["id"]])
        # A premium car needs an experienced driver (the fine is 150 a car), a manual car a manual licence.
        audience = {"experienced": any(leg["car"]["premium"] for leg in order["legs"]), "manualLicence": retry.manual_licence or facts.manual}
        stops = kit.without_windows(self.stops(order, legs, retry, facts), self.now)
        self.outbox.append({"type": "post", "stops": stops, "audience": audience, "schedule": self.fees_for(order, len(legs))})
        if len(legs) > 1:  # a trade-in over the 12-hour limit for a gig with two cars goes as one gig per car
            self.send()
            if not self.gigs_of(order["id"]):
                for leg in legs:
                    self.post_now(order, [leg], retry)

    def stops(self, order: dict, legs: list[int], retry: kit.Retry, facts: Facts) -> list[dict]:
        """A pickup and a delivery for each leg. A stop gets its own window only where the note makes it
        narrower than the order's: the car is ready later, a site keeps shorter hours, or the car is due earlier."""
        stops = []
        deadline = min(order["deadline"], facts.deadline or order["deadline"])
        for index in legs:
            stated = order["legs"][index]
            leg = apply(stated, facts)
            plates = retry.plates or facts.plates
            km = self.geo.km[(stated["pickup"]["placeId"], stated["delivery"]["placeId"])]
            last = last_pickup(leg, deadline, self.geo.drive(stated) + (PLATES_MINUTES if plates else 0))
            start = max(leg["pickup"]["window"]["from"], retry.pickup_from)
            end = stated["pickup"]["window"]["to"]
            if last is not None and len(legs) == 1:
                self.last_pickup[order["id"]] = min(order["lastPickupAt"], last)
                if leg["pickup"]["hours"] != stated["pickup"]["hours"]:  # shorter hours than stated: keep the visit inside one real day
                    span = open_span(leg["pickup"], last // DAY)
                    start, end = max(start, span[0]), min(end, span[1])
            if self.policy.p.pickup_buffer and last is not None and len(legs) == 1 and not stated["pickup"]["privateAddress"]:
                # A driver plans to collect by the window's end. Ending it before lastPickupAt leaves slack for a slow
                # drive or an earlier gig that runs late: 26 of 40 'arrived late' cars in the hard weeks were collected
                # in the last hour before lastPickupAt and missed the deadline by minutes.
                slack = int(self.policy.p.pickup_buffer + 0.1 * self.geo.drive(stated))
                if min(order["lastPickupAt"], last) - slack >= start + HOUR:  # never squeeze the window under an hour
                    end = min(end, min(order["lastPickupAt"], last) - slack)
            due = deadline
            if leg["delivery"]["hours"] != stated["delivery"]["hours"]:
                span = open_span(leg["delivery"], deadline // DAY)
                due = min(due, span[1]) if span else due
            pickup = {"orderId": order["id"], "leg": index, "kind": "pickup", "withPlates": plates, "withCharging": needs_charging(stated, km)}
            delivery = {"orderId": order["id"], "leg": index, "kind": "delivery"}
            base = {"from": stated["delivery"]["window"]["from"], "to": max(stated["delivery"]["window"]["from"], order["deadline"])}
            stops += [kit.narrower(pickup, {"from": start, "to": max(start, end)}, stated["pickup"]["window"]),
                      kit.narrower(delivery, {"from": base["from"], "to": max(base["from"], due)}, base)]
        if self.policy.p.windows and len(legs) == 1 and len(order["legs"]) == 1 and not order["legs"][0]["pickup"]["privateAddress"]:
            # A booked driver plans the pickup anywhere inside its window and tells us only when the plan leaves it. With
            # the order's own window, which runs to the deadline, a driver who will collect the car too late says nothing.
            last = self.last_pickup.get(order["id"], order["lastPickupAt"])
            window = stops[0].get("window") or dict(order["legs"][0]["pickup"]["window"])
            if max(window["from"], self.now) < last < window["to"]:
                stops[0] = {**stops[0], "window": {"from": window["from"], "to": last}}
                self.stats["windows"] += 1
        return stops

    def post_as_kit(self, order: dict, legs: list[int], retry: kit.Retry = kit.Retry()) -> None:
        before = len(self.outbox)
        super().post(order, legs, retry)
        # The starter plans a charging stop for every electric car under 30%. The rule asks for one only over 200 km.
        for action in self.outbox[before:]:
            for stop in action.get("stops", []):
                if stop.get("withCharging"):
                    leg = order["legs"][stop["leg"]]
                    stop["withCharging"] = needs_charging(leg, self.geo.km[(leg["pickup"]["placeId"], leg["delivery"]["placeId"])])

    # Posting: two cars as a round trip. A driver's trip home costs them a ticket bought on the day and hours of
    # their time. A second car that goes back the way the first came pays for that trip, so the pair needs less
    # than the two cars alone.

    def plain(self, order: dict) -> bool:
        """An order that can ride in a pair: one car that any driver may take, with a note that changes nothing."""
        if len(order["legs"]) != 1 or None not in order["deliveredAt"] or order["legs"][0]["car"]["premium"]:
            return False
        if order["id"] in self.urgent or order["id"] in self.alone:
            return False
        facts = self.facts(self.requests[order["id"]])
        return not (facts.plates or facts.pickup_from or facts.deadline or facts.pickup_opens is not None or facts.pickup_closes is not None
                    or facts.delivery_opens is not None or facts.delivery_closes is not None)

    def pair_start(self, first: dict, second: dict) -> Optional[int]:
        """The last minute to collect the first car of a round trip so that both cars are on time. None when
        the two cars do not make a round trip that one driver can do in one day."""
        p, a, b = self.policy.p, first["legs"][0], second["legs"][0]
        hop = self.geo.minutes[(a["delivery"]["placeId"], b["pickup"]["placeId"])]
        back = self.geo.minutes[(b["delivery"]["placeId"], a["pickup"]["placeId"])]
        drive = self.geo.drive(a)
        if hop > p.pair_hop or back > p.pair_back or drive + hop + self.geo.drive(b) > 12 * HOUR:
            return None
        last_b = self.last_pickup.get(second["id"], second["lastPickupAt"])
        start = min(self.last_pickup.get(first["id"], first["lastPickupAt"]), last_b - drive - hop)
        opens = open_span(a["pickup"], start // DAY)
        if opens is None or start < max(opens[0], a["pickup"]["window"]["from"]) or start // DAY != last_b // DAY:
            return None
        if b["pickup"]["window"]["from"] > start + drive + hop + 2 * HOUR:  # the driver would wait hours for the second car
            return None
        if start - self.now < (p.pair_split_hours + 2) * HOUR:  # too little time to look for a driver for the pair
            return None
        return start

    def post_pair(self, order: dict) -> bool:
        """Posts a new order as a round trip with an order whose gig no driver has taken yet, in place of that
        gig. False when there is no such order, or a driver took that gig in this very minute."""
        if not self.plain(order):
            return False
        best = None
        for other in self.orders.values():
            gigs = self.gigs_of(other["id"])
            if other["id"] == order["id"] or len(gigs) != 1 or gigs[0] in self.booked or gigs[0] in self.pairs or not self.plain(other):
                continue
            if self.policy.p.pair_safe and self.is_pair(gigs[0]):
                continue  # a pair that came back from its driver: taking one car out of it would leave the other without a gig
            for first, second in ((order, other), (other, order)):
                start = self.pair_start(first, second)
                if start is not None and (best is None or start > best[0]):
                    best = (start, first, second, gigs[0])
        if best is None:
            return False
        start, first, second, old_gig = best
        slack = self.policy.p.pair_urgent_first
        if slack and self.last_pickup.get(second["id"], second["lastPickupAt"]) < self.last_pickup.get(first["id"], first["lastPickupAt"]):
            reverse = self.pair_start(second, first)  # the tighter car first, if the pair then starts little earlier
            if reverse is not None and reverse >= start - slack:
                start, first, second = reverse, second, first
        self.send()  # the world must have every earlier action before we take the other gig out
        if self.world.act([{"type": "withdraw", "gigId": old_gig}])[0]["ok"] is not True:
            return False
        self.forget(old_gig)
        stops = []
        for each in (first, second):
            leg = each["legs"][0]
            km = self.geo.km[(leg["pickup"]["placeId"], leg["delivery"]["placeId"])]
            stops += [{"orderId": each["id"], "leg": 0, "kind": "pickup", "withPlates": False, "withCharging": needs_charging(leg, km)},
                      {"orderId": each["id"], "leg": 0, "kind": "delivery"}]
        opens = first["legs"][0]["pickup"]["window"]["from"]
        if self.policy.p.windows and start >= max(opens, self.now) + HOUR:  # the driver starts by the pair's last start, or says so
            stops[0]["window"] = {"from": opens, "to": start}
        typical = self.policy.pair_typical(self, first, second)
        manual = any(self.facts(self.requests[each["id"]]).manual for each in (first, second))
        action = {"type": "post", "stops": stops, "audience": {"experienced": False, "manualLicence": manual}, "schedule": self.policy.schedule(self, typical, start, False)}
        result = self.world.act([action])[0]
        if result["ok"] is not True:  # the world does not accept the pair: both cars go alone
            self.refused[f"pair: {result['reason'][:80]}"] += 1
            self.alone.update((first["id"], second["id"]))
            other = second if first["id"] == order["id"] else first
            self.post(other, [0])
            return False
        self.carry(action, result["id"])
        self.pairs[result["id"]] = start
        self.stats["pairs_posted"] += 1
        return True

    def raise_after_drop(self, gig_id: str) -> None:
        """A driver gave a single car back with time left. Most such drops come at the start of the pickup day (the
        driver does not work it), and the gig then sits at the fee that had already found a driver once, while the
        drivers who saw it learned to wait: the late ones are booked at 1.6 to 2.6 after the warning. Start its fees
        again at `drop_rescue` typical fees and rise as usual to the late fee at the warning."""
        orders = [order_id for order_id, legs in self.leg_gigs.items() if gig_id in legs.values()]
        if len(orders) != 1 or self.is_pair(gig_id) or gig_id in self.booked or orders[0] in self.urgent:
            return
        order = self.orders.get(orders[0])
        if order is None or len(order["legs"]) != 1 or None not in order["deliveredAt"]:
            return
        last = self.last_pickup.get(order["id"], order["lastPickupAt"])
        if last - self.now < 4 * HOUR:
            return  # the deadline warning comes soon and does this
        steps = self.policy.fees(self, order, 1, urgent=False)
        floor = round(self.policy.steady(self, self.requests[order["id"]], order["legs"][0], self.typical(order), self.policy.p.road_fee_blend) * self.policy.p.drop_rescue)
        top = 0
        for step in steps:  # never a falling fee: the world refuses a schedule whose fees fall
            top = max(top, step["feeCents"], floor)
            step["feeCents"] = top
        self.outbox.append({"type": "reprice", "gigId": gig_id, "schedule": steps})
        self.stats["drop_rescues"] += 1

    def is_pair(self, gig_id: str) -> bool:
        return gig_id in self.posts and len({stop["orderId"] for stop in self.posts[gig_id]["stops"]}) > 1

    def forget(self, gig_id: str) -> list[str]:
        """A gig that has left the app carries nothing now. Returns the orders that it carried."""
        orders = [order_id for order_id, legs in self.leg_gigs.items() if gig_id in legs.values()]
        for order_id in orders:
            self.leg_gigs[order_id] = {leg: gig for leg, gig in self.leg_gigs[order_id].items() if gig != gig_id}
        self.pairs.pop(gig_id, None)
        return orders

    def alone_again(self, gig_id: str) -> None:
        """Posts each undelivered car of a pair that has left the app as a gig of its own."""
        for order_id in self.forget(gig_id):
            self.alone.add(order_id)
            order = self.orders.get(order_id)
            if order is not None and None in order["deliveredAt"]:
                self.post(order, kit.undelivered(order))

    def split(self, gig_id: str) -> None:
        """Takes apart a pair that no driver has taken: each car alone is easier to place when time runs short."""
        self.send()
        if gig_id in self.booked or self.world.act([{"type": "withdraw", "gigId": gig_id}])[0]["ok"] is not True:
            self.pairs.pop(gig_id, None)  # a driver has just taken it
            return
        self.stats["pairs_split"] += 1
        self.alone_again(gig_id)

    def chain(self, driver: Optional[str], place: str) -> None:
        """A driver has just delivered one of our cars at `place`. Cars of ours that wait for a driver within reach
        of it are offered to that driver directly: no trip to the car, so the fee can be low (handbook, "The typical
        fee": a driver who is near the pickup after another gig needs much less)."""
        p, day = self.policy.p, self.now // DAY
        if driver is None or not 7 * HOUR <= self.now % DAY < 23 * HOUR - 10:
            return
        near = []
        for order_id, order in self.orders.items():
            gigs = self.gigs_of(order_id)
            if len(gigs) != 1 or gigs[0] in self.booked or len(order["legs"]) != 1 or self.is_pair(gigs[0]):
                continue
            leg = order["legs"][0]
            hop = 0 if leg["pickup"]["placeId"] == place else self.geo.minutes.get((place, leg["pickup"]["placeId"]), 10 ** 6)
            last = self.last_pickup.get(order_id, order["lastPickupAt"])
            if hop <= p.chain_reach and leg["pickup"]["window"]["from"] <= self.now + 2 * HOUR and self.now + hop <= last and driver not in self.offered.get(gigs[0], {}):
                near.append((hop, order_id, gigs[0]))
        for hop, order_id, gig in sorted(near)[:max(0, 3 - self.offers_on[driver, day])]:
            sent = self.offered.setdefault(gig, {})
            if sum(1 for at in sent.values() if at > self.now - 10) >= 3:
                continue
            order = self.orders[order_id]
            typical = self.policy.steady(self, self.requests[order_id], order["legs"][0], self.typical(order), p.road_fee_blend)
            self.outbox.append({"type": "offer", "gigId": gig, "driverId": driver, "feeCents": round(typical * p.chain_fee)})
            sent[driver] = self.now
            self.offers_on[driver, day] += 1
            self.stats["chain_offers"] += 1

    def offer(self) -> None:
        """A gig that is still without a driver a few hours before its last pickup goes, as a direct offer, to the
        drivers who looked at it lately and did not take it. In the app a driver may hold out for a raise; an offer
        is ten minutes, yes or no, at a fee that already has the raise in it (rules, "Direct offers")."""
        p, day = self.policy.p, self.now // DAY
        if not 7 * HOUR <= self.now % DAY < 23 * HOUR - 10:  # no driver reads an offer at night
            return
        for order_id, order in self.orders.items():
            gigs = self.gigs_of(order_id)
            if len(gigs) != 1 or gigs[0] in self.booked or len(order["legs"]) != 1 or self.is_pair(gigs[0]):
                continue
            left = self.last_pickup.get(order_id, order["lastPickupAt"]) - self.now
            if not 0 < left <= p.offer_lead * HOUR:
                continue
            sent, seen = self.offered.setdefault(gigs[0], {}), self.viewers.get(gigs[0], {})
            free = 3 - sum(1 for at in sent.values() if at > self.now - 10)  # at most three open offers a gig
            drivers = sorted((d for d in seen if d not in sent and self.offers_on[d, day] < 3), key=lambda d: -seen[d])[:max(0, free)]
            typical = self.policy.steady(self, self.requests[order_id], order["legs"][0], self.typical(order), p.road_fee_blend)
            fee = round(typical * (p.late_fee if left <= 3 * HOUR else p.offer_fee))
            for driver in drivers:
                self.outbox.append({"type": "offer", "gigId": gigs[0], "driverId": driver, "feeCents": fee})
                sent[driver] = self.now
                self.offers_on[driver, day] += 1
                self.stats["offers"] += 1

    def flu_sign(self, event: dict) -> None:
        """The flu day gives itself away just after midnight: the drivers who are ill give back the bookings they
        hold for that day. Four such drops in the day's first hour happened on 42 of 45 flu days and on none of
        135 other days (swarm/early_days). Drops at night are otherwise rare (rules)."""
        day = event["at"] // DAY
        if event["at"] % DAY >= HOUR or self.flu_day == day:
            return
        orders = [order_id for order_id, legs in self.leg_gigs.items() if event["gigId"] in legs.values()]
        if any(self.last_pickup.get(o, self.orders[o]["lastPickupAt"]) // DAY == day for o in orders if o in self.orders):
            self.night_drops[day] += 1
            if self.night_drops[day] >= 4:
                self.flu_day = day
                self.stats["flu_days"] += 1
                self.rescued.clear()  # cars raised on an ordinary morning rule may be raised again today

    def rescue(self) -> None:
        """On the morning of a car's last pickup, a gig that still has no driver is raised at once. Measured on 60
        weeks: a car without a driver at 08:00 on that day comes late three times in ten, at noon six in ten, a car
        with a driver 1.5%; and these cars are six in ten of all late ones. The world's own warning comes three
        hours before the last pickup, when most of them are lost."""
        p, today = self.policy.p, self.now // DAY
        flu = bool(p.flu) and self.flu_day == today  # the flu day: every open gig of today, from the hour drivers wake
        if flu and p.budget and self.policy.headroom(self) >= p.budget:
            flu = False  # with a budget, the rescue is bought only in a week that needs it
        clock = bool(p.rescue_hour) and self.now % DAY >= p.rescue_hour * HOUR and not (p.guard and not self.policy.careful(self))
        if not (flu or clock):
            return
        since = max(self.now, today * DAY + 5 * HOUR) if flu and not clock else self.now
        for order_id, order in self.orders.items():
            gigs = self.gigs_of(order_id)
            last = self.last_pickup.get(order_id, order["lastPickupAt"])
            if (order_id in self.rescued or order_id in self.urgent or len(order["legs"]) != 1 or len(gigs) != 1 or gigs[0] in self.booked
                    or self.is_pair(gigs[0]) or last // DAY != today or last - self.now <= 3 * HOUR or gigs[0] not in self.posts):
                continue
            if flu and not clock and p.flu == 2 and self.geo.drive(order["legs"][0]) < p.long_hours * HOUR:
                continue  # flu 2: only the long drives, which no driver can still take once the morning is gone
            self.rescued.add(order_id)
            typical = self.policy.steady(self, self.requests[order_id], order["legs"][0], self.typical(order), p.road_fee_blend)
            standing = max((step["feeCents"] for step in self.posts[gigs[0]]["schedule"] if step["at"] <= self.now), default=0)
            start, top, warning = max(standing, round(typical * p.rescue_fee)), round(typical * p.late_fee), last - 3 * HOUR
            top, until = max(top, start), max(since, min(warning, since + 4 * HOUR))
            steps = {int(since + (until - since) * k / 4): round(start + (top - start) * k / 4) for k in range(5)}
            if since > self.now:
                steps[self.now] = max(standing, 1)  # until the drivers wake, the fee stays where it stands
            self.outbox.append({"type": "reprice", "gigId": gigs[0], "schedule": [{"at": at, "feeCents": fee} for at, fee in sorted(steps.items())]})
            self.stats["rescues"] += 1

    def tick(self) -> None:
        """After each batch of events: take apart the pairs that have waited long enough for a driver."""
        for order_id, release in list(self.held.items()):  # cars that waited for a partner and found none go out alone
            order = self.orders.get(order_id)
            if order is None or None not in order["deliveredAt"]:
                del self.held[order_id]
            elif self.now >= release:
                del self.held[order_id]
                self.post_now(order, kit.undelivered(order))
        if self.policy.p.rescue_hour or (self.policy.p.flu and self.flu_day == self.now // DAY):
            self.rescue()
        if self.policy.p.offer_lead:
            self.offer()
        for gig_id, start in list(self.pairs.items()):
            if gig_id in self.booked:
                if not self.policy.p.pair_safe:
                    del self.pairs[gig_id]  # with pair_safe it stays listed: its driver may give it back
            elif self.now >= start - self.policy.p.pair_split_hours * HOUR:
                self.split(gig_id)

    # The starter's plumbing, where a gig with two orders needs more care than the starter takes.

    def raise_fees(self, order_id: str) -> None:
        for gig_id in self.gigs_of(order_id):
            if self.is_pair(gig_id) and gig_id not in self.booked:
                self.urgent.add(order_id)
                return self.split(gig_id)  # the car goes alone, at the steep fees of an order with a deadline warning
        super().raise_fees(order_id)

    def repost(self, gig_id: str) -> None:
        if self.is_pair(gig_id):
            return self.alone_again(gig_id)  # an expired pair: each car again, alone
        super().repost(gig_id)

    def withdraw(self, order_id: str) -> bool:
        self.held.pop(order_id, None)  # a changed order is posted again from scratch
        self.send_post_of(order_id)
        pairs = [gig_id for gig_id in self.gigs_of(order_id) if self.is_pair(gig_id)]
        done = super().withdraw(order_id)
        if done:
            self.alone.add(order_id)
            for gig_id in pairs:  # the other car of the pair has lost its gig too
                self.alone_again(gig_id)
        return done

    def rejoin(self, snapshot: dict, history: list) -> None:
        self.relast(snapshot)
        super().rejoin(snapshot, history)
        for gig in snapshot["gigs"]:  # an open pair: take it apart when its time comes, as before the restart
            if (gig["status"] == "open" or (gig["status"] == "booked" and self.policy.p.pair_safe)) and self.is_pair(gig["id"]):
                first, second = (self.orders.get(order_id) for order_id in dict.fromkeys(stop["orderId"] for stop in gig["stops"]))
                self.pairs[gig["id"]] = (self.pair_start(first, second) if first and second else None) or self.now
        if self.policy.p.windows:  # answer the newest late notice of every gig its driver still holds and has not left for
            holder = {gig["id"]: gig.get("driverId") for gig in snapshot["gigs"] if gig["status"] == "booked"}
            for gig_id, event in {e["gigId"]: e for e in history if e["kind"] == "driver_late"}.items():
                if holder.get(gig_id) == event["driverId"]:
                    self.late_driver(event)

    def relast(self, snapshot: dict) -> None:
        """After a restart: each waiting car's own last pickup minute, as `stops` worked it out from the note when the
        car was posted. Without it the new desk believes the order's stated minute, which the note can make too late."""
        for order in snapshot["orders"]:
            request = self.requests.get(order["id"])
            if request is None or len(order["legs"]) != 1 or order["status"] == "cancelled" or None not in order["deliveredAt"]:
                continue
            facts, stated = self.facts(request), order["legs"][0]
            deadline = min(order["deadline"], facts.deadline or order["deadline"])
            last = last_pickup(apply(stated, facts), deadline, self.geo.drive(stated) + (PLATES_MINUTES if facts.plates else 0))
            if last is not None:
                self.last_pickup[order["id"]] = min(order["lastPickupAt"], last)

    def read_results(self, actions: list, results: list) -> None:
        super().read_results(actions, results)
        for action, result in zip(actions, results):
            if result["ok"] is not True:
                self.refused[f"{action['type']}: {result['reason'][:80]}"] += 1

    def relearn(self, history: list) -> None:
        """After a restart: reads the week's events again in order, so the policy knows what it knew before.
        It decides each past quote again, to know what the dealers answered to, and sends nothing."""
        now = self.now
        for event in history:
            self.now = event["at"]
            if self.policy.p.snow_cost and event["kind"] == "forecast":
                self.forecasts.append(event)
            if event["kind"] == "gig_viewed":
                self.viewers.setdefault(event["gigId"], {})[event["driverId"]] = event["at"]
            if event["kind"] == "gig_booked":
                self.holder[event["gigId"]] = event["driverId"]
            if event["kind"] == "price_request":
                self.requests[event["request"]["id"]] = event["request"]
                self.policy.quote(self, event["request"])
            elif event["kind"] == "order_won":  # the cars we held at each moment count in the price of the next quote
                self.orders[event["order"]["id"]] = event["order"]
            elif event["kind"] == "delivered" and event["orderId"] in self.orders:
                self.orders[event["orderId"]]["deliveredAt"][event["leg"]] = event["at"]
                self.arrived(self.orders[event["orderId"]])
            elif event["kind"] == "order_cancelled":
                self.orders.pop(event["orderId"], None)
            elif event["kind"] == "deadline_close":
                self.warn(event)
            self.policy.observe(self, event)
        self.now = now

    def warn(self, event: dict) -> None:
        """Notes a deadline warning for the guard: every one, or with `guard_once` the first of each order."""
        if not (self.policy.p.guard_once and event["orderId"] in self.warned):
            self.warnings.append(event["at"])
        self.warned.add(event["orderId"])

    def handle(self, event: dict) -> None:
        kind = event["kind"]
        if self.policy.p.snow_cost and kind == "forecast":
            self.forecasts.append(event)
        self.stats[kind] += 1
        if kind == "gig_viewed":
            self.viewers.setdefault(event["gigId"], {})[event["driverId"]] = event["at"]
        elif kind == "offer_answered":
            self.stats[f"offer_{event['answer']}"] += 1
        elif kind == "gig_booked":
            self.holder[event["gigId"]] = event["driverId"]
        elif kind == "gig_dropped" and (self.policy.p.flu or self.policy.p.budget):
            self.flu_sign(event)
        elif kind == "delivered" and self.policy.p.chain_fee:
            self.chain(self.holder.get(event["gigId"]), event["placeId"])
        self.policy.observe(self, event)
        if kind == "deadline_close":
            self.warn(event)
        if kind == "ledger":
            self.ledger[event["line"]["kind"]] += event["line"]["cents"]
        elif kind == "order_won":
            order, request = event["order"], self.requests.get(event["order"]["id"])
            if request:
                self.stats["won_price"] += order["priceCents"]
                self.stats["won_list"] += next(o["listPriceCents"] for o in request["options"] if o["kind"] == order["option"])
                self.stats["won_typical"] += request["referenceFeeCents"]
                self.stats[f"won_{order['option']}"] += 1
                self.stats[f"won_day{request['arrivedAt'] // 1440}"] += 1
                self.stats[f"price_day{request['arrivedAt'] // 1440}"] += order["priceCents"]
                self.stats[f"list_day{request['arrivedAt'] // 1440}"] += next(o["listPriceCents"] for o in request["options"] if o["kind"] == order["option"])
        elif kind == "gig_booked" and self.is_pair(event["gigId"]):
            self.stats["pairs_booked"] += 1
            self.stats["pair_fee"] += event["feeCents"]
            self.stats["pair_typical"] += sum(self.requests[order_id]["referenceFeeCents"] for order_id in {stop["orderId"] for stop in self.posts[event["gigId"]]["stops"]})
        if kind == "order_changed" and self.policy.p.relane and event["order"]["id"] in self.orders:
            # The dealer sent the car elsewhere and pays the same price: drivers want the fee of the new drive.
            leg = event["order"]["legs"][0]
            minutes = self.geo.minutes[(leg["pickup"]["placeId"], leg["delivery"]["placeId"])]
            self.longer[event["order"]["id"]] = round((15.7 + 0.386 * minutes) * 100)
        # A cancelled order takes an unbooked gig out of the app. When that gig was a pair, the other car needs a gig again.
        orphaned = [gone["gigId"] for gone in event["gigs"] if gone["outcome"] == "withdrawn" and self.is_pair(gone["gigId"])] if kind == "order_cancelled" else []
        super().handle(event)
        for gig_id in orphaned:
            self.alone_again(gig_id)
        if kind in ("gig_dropped", "no_show") and self.policy.p.drop_rescue:
            self.raise_after_drop(event["gigId"])
        if kind == "delivered" and event["orderId"] in self.orders:
            self.arrived(self.orders[event["orderId"]])
        if kind == "driver_late" and self.policy.p.windows:
            self.late_driver(event)

    def late_driver(self, event: dict) -> None:
        """The booked driver will collect the first car after its window: the car will be late. Release the driver, which
        is free after this notice, and post the car again while a new driver can still come: with at least 3 hours and
        the drive time of the car to the end of the window. Otherwise keep the driver. The desk keeps no book for this:
        the window is in the post, and a restart reads the posts back from the world."""
        gig_id, post = event["gigId"], self.posts.get(event["gigId"])
        self.stats["late_notices"] += 1
        if post is None or gig_id not in self.booked:
            return
        orders = [self.orders.get(order_id) for order_id in dict.fromkeys(stop["orderId"] for stop in post["stops"])]
        if any(order is None for order in orders):
            return
        first, single = orders[0], len(orders) == 1
        last = (post["stops"][0].get("window") or {}).get("to") or self.last_pickup.get(first["id"], first["lastPickupAt"])
        if single and first["lastPickupAt"] - last > 12 * HOUR:  # the dealer moved the deadline (snow) after the booking
            last = first["lastPickupAt"]
            if event["pickupAt"] <= last:
                self.stats["late_kept_in_time"] += 1
                return
        if last - self.now < max(3 * HOUR, self.geo.drive(first["legs"][0]) if single else 0):
            self.stats["late_kept_no_time"] += 1  # nobody else comes in time either
            return
        self.send()
        result = self.world.act([{"type": "release", "gigId": gig_id}])[0]
        if result["ok"] is not True:
            self.refused[f"release: {result['reason'][:80]}"] += 1
            return
        self.stats["late_released"] += 1
        self.booked.discard(gig_id)
        for order_id in self.forget(gig_id):
            self.alone.add(order_id)  # no time to wait for a partner
            order = self.orders[order_id]
            if None in order["deliveredAt"]:
                if self.last_pickup.get(order_id, order["lastPickupAt"]) - self.now <= 3 * HOUR:
                    self.urgent.add(order_id)  # inside the warning of the world already: the steep fees at once
                self.post(order, kit.undelivered(order))

    def arrived(self, order: dict) -> None:
        """When the last car of an order is delivered: tell the policy whether the dealer got it on time."""
        if None not in order["deliveredAt"]:
            due = min(order["deadline"], self.facts(self.requests[order["id"]]).deadline or order["deadline"])
            self.policy.delivered(order["dealerId"], max(order["deliveredAt"]) <= due)
