"""leaders/chains, second rule: tell the drivers who already hold a gig of ours about the car that has waited.

The first rule (alt/ld_chains_core.py) offered the car that is a holder's way home at a fee well under the app's.
Played for real: 792 offers in 12 weeks, 53% read, 6 accepted (1.4% of the read ones). A driver who holds the
adjacent gig does not take the car for less than the app shows.

What is left of the idea is the offer as a notification. Measured on version 7's 60 weeks
(leaders/chains/s1d_planning.py): 116 single cars a week are still open an hour after they came into the app;
the app shows 0.94 typical then, they are paid 1.02 in the end and 6.6% arrive late. 91 of them have, at that
minute, drivers who hold a gig of ours that ends within 30 road minutes of the car's pickup in time to do the car
after it (5.6 drivers a car). Those drivers work that day, so they read an offer (55 to 67% against 21% of
others), and of everyone who ever said yes to an offer at or over the app's fee, 97% had driven for us that day.
The app does not notify a driver where our gigs take him.

The rule. A single plain car that has been in the app for `age` minutes without a driver is offered, three
drivers at a time, to the drivers who hold a gig of ours that the car can follow that day (pickup within `reach`
road minutes of where their gig ends), at the fee the app shows at that minute (less `discount`, 0 by default).
First the drivers it takes home, then those whose gig ends nearest. Each driver is asked once for a car. The
gig stays in the app: nothing is held back, and nobody is paid more than the app pays.

The lab wakes this desk also on `gig_booked` and `offer_answered` and at the minutes it has work."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from dispatch.desk import Desk
from dispatch.geo import DAY, HOUR, Geo, open_span
from dispatch.policy import Params, Policy
from spread import starter as kit


@dataclass(frozen=True)
class Tell:
    age: int = 45  # minutes a car has been in the app without a driver before the holders are told
    reach: int = 60  # road minutes from where a holder's gig ends to the car, at most
    wait: int = 120  # a holder does not wait longer than this for the car to be ready after his gig
    slack: int = 15  # minutes added to his gig's planned end
    discount: float = 0.0  # the offer's fee is the app's fee less this share
    share: float = -9.0  # only holders with at least this way-home share (-9: everyone within reach)
    seen_last: bool = True  # drivers who have looked at the gig in the app go last
    active: bool = True  # False sends nothing (the control: the same wakes)


class TellDesk(Desk):
    def __init__(self, world, level: int, now: int, policy: Policy, geo: Geo, rule: Tell = Tell()):
        super().__init__(world, level, now, policy, geo)
        self.rule = rule
        self.homes: dict[str, str] = {}
        self.licence: dict[str, str] = {}
        self.live: dict[str, dict] = {}  # gig a driver holds -> who, the minute of its first pickup, cars still to deliver
        self.first_posted: dict[str, int] = {}  # order -> the minute its first single-car gig came into the app
        self.fees: dict[str, list] = {}  # gig -> the fee schedule the app has now (a reprice replaces it)
        self.fresh: list[str] = []  # orders in the app that are not old enough yet
        self.pool: dict[str, list] = {}  # order old enough -> the holders still to ask, best last
        self.asked: set[tuple[str, str]] = set()  # (order, driver) pairs that have been asked
        self.new_holds: list[str] = []
        self.open_offers: dict[tuple[str, str], dict] = {}
        self.wakes: set[int] = set()  # minutes at which the desk wants to look again
        self.told: set[str] = set()  # gigs booked through one of these offers

    def meet(self, roster: list) -> None:
        super().meet(roster)
        self.homes = {driver["id"]: driver["homePlaceId"] for driver in roster}
        self.licence = {driver["id"]: driver["licence"] for driver in roster}

    # What the desk sees.

    def carry(self, action, gig_id: str) -> None:
        super().carry(action, gig_id)
        self.fees[gig_id] = action["schedule"]
        if kit.pickups(action) == 1:
            order_id = action["stops"][0]["orderId"]
            self.first_posted.setdefault(order_id, self.now)
            if order_id not in self.pool and order_id not in self.fresh:
                self.fresh.append(order_id)
                self.wakes.add(max(self.now + 1, self.first_posted[order_id] + self.rule.age))

    def read_results(self, actions: list, results: list) -> None:
        super().read_results(actions, results)
        for action, result in zip(actions, results):
            if action["type"] == "reprice" and result["ok"] is True:
                self.fees[action["gigId"]] = action["schedule"]
            if action["type"] == "offer" and result["ok"] is not True and self.open_offers.pop((action["gigId"], action["driverId"]), None):
                self.stats["tell_refused"] += 1

    def handle(self, event: dict) -> None:
        kind, gig = event["kind"], event.get("gigId")
        if kind == "gig_booked":
            self.live[gig] = {"driver": event["driverId"], "picked": None, "left": kit.pickups(self.posts[gig]) if gig in self.posts else 1}
            self.new_holds.append(gig)
        elif kind in ("gig_dropped", "no_show"):
            self.live.pop(gig, None)
            if gig in self.told:
                self.told.discard(gig)
                self.stats["tell_dropped"] += 1
            if gig in self.posts and kit.pickups(self.posts[gig]) == 1:  # open again: the holders are told again
                order_id = self.posts[gig]["stops"][0]["orderId"]
                if order_id not in self.pool and order_id not in self.fresh:
                    self.fresh.append(order_id)
                    self.wakes.add(event["at"] + 1)
        elif kind == "picked_up" and gig in self.live:
            if self.live[gig]["picked"] is None:
                self.live[gig]["picked"] = event["at"]
        elif kind == "delivered" and gig in self.live:
            self.live[gig]["left"] -= 1
            if self.live[gig]["left"] <= 0:
                del self.live[gig]
        elif kind == "order_cancelled":
            for gone in event["gigs"]:
                self.live.pop(gone["gigId"], None)
        elif kind == "offer_answered":
            offer = self.open_offers.pop((gig, event["driverId"]), None)
            if offer is not None:
                self.stats[f"tell_{event['answer']}"] += 1
                self.stats[f"tell_{event['answer']}_{offer['kind']}"] += 1
                if event["answer"] == "accepted":
                    self.told.add(gig)
                    for name in ("fee", "typical", "age", "left"):
                        self.stats[f"tell_{name}"] += offer[name]
        super().handle(event)

    # The geometry of a chain (as in alt/ld_chains_core.py).

    def minutes(self, a: str, b: str) -> int:
        return 0 if a == b else self.geo.minutes.get((a, b), 10 ** 6)

    def shape(self, gig_id: str) -> Optional[tuple]:
        """A held gig: its first pickup stop, where it ends, its minutes on the road, and from when to when its
        first car can be collected."""
        post = self.posts.get(gig_id)
        if post is None:
            return None
        legs, first_from = [], 0
        for stop in post["stops"]:
            if stop["kind"] == "pickup":
                order = self.orders.get(stop["orderId"])
                if order is None:
                    return None
                if not legs:
                    first_from = stop.get("window", {}).get("from", 0)
                legs.append((order, order["legs"][stop["leg"]]))
        if not legs:
            return None
        road = sum(self.geo.drive(leg) for _, leg in legs)
        road += sum(self.minutes(a["delivery"]["placeId"], b["pickup"]["placeId"]) for (_, a), (_, b) in zip(legs, legs[1:]))
        start = max(first_from, legs[0][1]["pickup"]["window"]["from"])
        last = min(self.last_pickup.get(order["id"], order["lastPickupAt"]) for order, _ in legs)
        return legs[0][1]["pickup"], legs[-1][1]["delivery"]["placeId"], road, start, last

    def after(self, shape: tuple, picked: Optional[int], order: dict, gig_c: str, hop: int) -> bool:
        """Whether the holder of a gig can collect the car after that gig, on the same day, without a long wait."""
        first_pickup, _, road, start, last = shape
        pickup = order["legs"][0]["pickup"]
        own = self.posts[gig_c]["stops"][0].get("window", {})
        c_from = max(pickup["window"]["from"], own.get("from", 0))
        c_last = min(self.last_pickup.get(order["id"], order["lastPickupAt"]), own.get("to", 10 ** 9))

        def fits(early: int, late: int) -> bool:
            span = open_span(pickup, early // DAY)
            return span is not None and max(c_from, early, span[0]) <= min(c_last, span[1]) and c_from <= late + self.rule.wait

        tail = road + hop + self.rule.slack
        if picked is not None:
            there = max(self.now, picked + tail)
            return fits(there, there)
        for day in range(max(self.now, start) // DAY, last // DAY + 1):
            span = open_span(first_pickup, day)
            if span is None:
                continue
            low, high = max(self.now, start, span[0]), min(last, span[1])
            if low <= high and fits(low + tail, high + tail):
                return True
        return False

    def open_car(self, order_id: str) -> Optional[str]:
        """The gig of a single plain car that waits for a driver, or None."""
        order, gigs = self.orders.get(order_id), self.gigs_of(order_id)
        if order is None or len(gigs) != 1 or gigs[0] in self.booked or gigs[0] not in self.posts or self.is_pair(gigs[0]):
            return None
        if len(order["legs"]) != 1 or None not in order["deliveredAt"] or order["legs"][0]["car"]["premium"]:
            return None
        return gigs[0]

    def candidate(self, order_id: str, gig_h: str) -> Optional[tuple]:
        """(rank, driver, kind) when the holder of `gig_h` could do the car after it; a higher rank is asked first."""
        rule, hold, gig_c = self.rule, self.live.get(gig_h), self.open_car(order_id)
        if hold is None or gig_c is None or gig_c == gig_h or hold["driver"] not in self.homes:
            return None
        shape = self.shape(gig_h)
        if shape is None:
            return None
        order, home, driver = self.orders[order_id], self.homes[hold["driver"]], hold["driver"]
        leg = order["legs"][0]
        hop = self.minutes(shape[1], leg["pickup"]["placeId"])
        if hop > rule.reach:
            return None
        saved = self.minutes(shape[1], home) - self.minutes(leg["delivery"]["placeId"], home) - hop
        share = saved / max(1, self.geo.drive(leg))
        if share < rule.share:
            return None
        if self.posts[gig_c]["audience"].get("manualLicence") and self.licence.get(driver) != "manual":
            return None
        if not self.after(shape, hold["picked"], order, gig_c, hop):
            return None
        home_end = self.minutes(leg["delivery"]["placeId"], home)
        kind = "home" if share >= 0.5 else "ends" if home_end <= 30 else "near" if hop <= 30 else "far"
        klass = {"home": 3, "ends": 2, "near": 1, "far": 0}[kind]
        seen = 1 if rule.seen_last and driver in self.viewers.get(gig_c, {}) else 0
        return (-seen, klass, -hop), driver, kind

    def fee_now(self, gig: str) -> int:
        schedule = self.fees.get(gig) or self.posts[gig]["schedule"]
        return max((step["feeCents"] for step in schedule if step["at"] <= self.now), default=schedule[0]["feeCents"])

    def add_to_pool(self, order_id: str, found: Optional[tuple]) -> None:
        if found is not None and (order_id, found[1]) not in self.asked and all(found[1] != other[1] for other in self.pool[order_id]):
            self.pool[order_id].append(found)

    def tell(self) -> None:
        rule, day, minute = self.rule, self.now // DAY, self.now % DAY
        holds, self.new_holds = list(dict.fromkeys(self.new_holds)), []
        self.wakes = {at for at in self.wakes if at > self.now}
        for order_id in list(self.fresh):  # cars that are old enough now: who could take them?
            if self.open_car(order_id) is None:
                self.fresh.remove(order_id)
            elif self.now - self.first_posted[order_id] >= rule.age:
                self.fresh.remove(order_id)
                self.pool[order_id] = []
                for gig in list(self.live):
                    self.add_to_pool(order_id, self.candidate(order_id, gig))
        for order_id in list(self.pool):
            if self.open_car(order_id) is None:
                del self.pool[order_id]  # it has a driver, or rides in a pair now
        for gig in holds:  # a new holder: the waiting cars his gig leads to
            if gig in self.live:
                for order_id in self.pool:
                    self.add_to_pool(order_id, self.candidate(order_id, gig))
        if not rule.active:
            return
        if not 7 * HOUR <= minute < 23 * HOUR - 10:  # no driver reads an offer at night
            if any(self.pool.values()):
                self.wakes.add((day if minute < 7 * HOUR else day + 1) * DAY + 7 * HOUR)
            return
        order_of = lambda order_id: self.last_pickup.get(order_id, self.orders[order_id]["lastPickupAt"])
        for order_id in sorted(self.pool, key=order_of):  # the car with the least time left first
            gig, waiting = self.open_car(order_id), self.pool[order_id]
            if gig is None or not waiting:
                continue
            sent = self.offered.setdefault(gig, {})
            free = 3 - sum(1 for at in sent.values() if at > self.now - 10)
            waiting.sort()
            while free > 0 and waiting:
                _, driver, kind = waiting.pop()
                if (order_id, driver) in self.asked or self.offers_on[driver, day] >= 3:
                    continue
                again = [c for c in (self.candidate(order_id, g) for g, hold in list(self.live.items()) if hold["driver"] == driver) if c]
                if not again:
                    continue  # he no longer holds a gig the car can follow
                app = self.fee_now(gig)
                fee = max(1, round(app * (1 - rule.discount)))
                order = self.orders[order_id]
                self.outbox.append({"type": "offer", "gigId": gig, "driverId": driver, "feeCents": fee})
                sent[driver] = self.now
                self.offers_on[driver, day] += 1
                self.asked.add((order_id, driver))
                typical = self.policy.steady(self, self.requests[order_id], order["legs"][0], self.typical(order), self.policy.p.road_fee_blend)
                self.open_offers[gig, driver] = {"kind": kind, "fee": fee, "typical": round(typical), "age": self.now - self.first_posted[order_id], "left": order_of(order_id) - self.now}
                self.stats["tell_offers"] += 1
                self.stats[f"tell_sent_{kind}"] += 1
                free -= 1

    def tick(self) -> None:
        super().tick()
        self.tell()


def wake_more(world, desk: TellDesk) -> None:
    """The lab steps a practice week from one event that needs an answer to the next. This desk also answers a
    booking and an offer's answer, and wants to be called at the minute a car has waited long enough."""
    plain = world.advance

    def advance(to=None, by=None, until=None, max=None, actions=()):
        if until is not None:
            until = list(dict.fromkeys(list(until) + ["gig_booked", "offer_answered"]))
            due = min((at for at in desk.wakes if at > desk.now), default=None)
            if due is not None:
                max = due if max is None else min(max, due)
        return plain(to=to, by=by, until=until, max=max, actions=actions)

    world.advance = advance


def make(client, world, level: int, now: int, params: Params, rule: Tell = Tell()):
    desk = TellDesk(world, level, now, Policy(params), Geo(client.map()), rule)
    desk.meet(world.roster())
    wake_more(world, desk)
    return desk
