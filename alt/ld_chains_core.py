"""leaders/chains: the chain offer at booking time. Version 7 in everything else (prices, fee schedules, pairs).

The handbook: "For a driver who already has one of your gigs, a second gig costs only the extra time and
tickets", and a direct offer "reaches a driver whom a notification does not, for example a driver who finishes
one of your gigs far from home". Measured on version 7's 60 weeks (leaders/chains/s1b_return.py): 53 cars a week
(drive of 45 minutes or more) start within an hour's road of where a gig that some driver already HOLDS will
end, in time, and lead that driver at least half of the way back to his home town. He sees such a car in the
app one time in five (the app does not notify him there) and takes it 3 times in 100; someone else takes it at
0.93 typical fees. Drivers plan a day's second gig beforehand (95% of second gigs are booked before the day's
first gig starts), so the moment to ask is when the car comes into the app or when he books the gig it
continues, not when he delivers.

The rule. A single plain car C is open. A driver holds a booked gig H of ours such that
  - C's pickup is at most `reach` road minutes from where H ends, and C can be collected after H that day;
  - way-home share = (road from H's end to his home - road from C's delivery to his home - road from H's end
    to C's pickup) / C's drive  is at least `share`.
He gets a direct offer for C at  typical x (1 - discount x share): the discount is the first of `levels`; after
a "declined" (he read it and said no) the next level goes out at once; after an "expired" (not read) the same
level goes once more at the next planning hour (17:00, or 07:00). The gig stays in the app at version 7's
fees for everyone else: nothing is held back.

The lab wakes this desk also on `gig_booked` and `offer_answered` (the final's live stream delivers every
event at once anyway), and at the minutes it wants to send an offer again."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from dispatch.desk import Desk
from dispatch.geo import DAY, HOUR, Geo, open_span
from dispatch.policy import Params, Policy
from spread import starter as kit


@dataclass(frozen=True)
class Chain:
    levels: tuple = (0.45, 0.30)  # the discount ladder for a car that is all of the driver's way home
    share: float = 0.5  # the least share of the car's drive that lies on the driver's way home
    reach: int = 60  # road minutes from where his gig ends to the car, at most
    wait: int = 120  # he does not wait longer than this for the car to be ready after his gig
    min_gain: int = 400  # cents under the app's fee that an offer must save to be worth one of his three a day
    retry: int = 1  # how often an unread offer is sent again at a planning hour
    slack: int = 15  # minutes added to his gig's planned end
    on_post: bool = True  # ask when the car comes into the app
    on_book: bool = True  # ask when he books the gig that the car continues


class ChainDesk(Desk):
    def __init__(self, world, level: int, now: int, policy: Policy, geo: Geo, rule: Chain = Chain()):
        super().__init__(world, level, now, policy, geo)
        self.rule = rule
        self.homes: dict[str, str] = {}  # driver -> home town
        self.licence: dict[str, str] = {}
        self.live: dict[str, dict] = {}  # gig a driver holds -> who, the minute of its first pickup, cars still to deliver
        self.new_cars: list[str] = []  # orders whose gig came into the app since the last look
        self.new_holds: list[str] = []  # gigs booked since the last look
        self.open_offers: dict[tuple[str, str], dict] = {}  # (gig, driver) -> the chain offer that is open
        self.tried: set[tuple[str, str]] = set()  # (order, driver) pairs that have had their first offer
        self.later: list[tuple] = []  # (minute, order, driver, level, tries): offers to send at that minute
        self.chained: set[str] = set()  # gigs booked through a chain offer

    def meet(self, roster: list) -> None:
        super().meet(roster)
        self.homes = {driver["id"]: driver["homePlaceId"] for driver in roster}
        self.licence = {driver["id"]: driver["licence"] for driver in roster}

    # What the desk sees.

    def carry(self, action, gig_id: str) -> None:
        super().carry(action, gig_id)
        if kit.pickups(action) == 1:
            self.new_cars.append(action["stops"][0]["orderId"])

    def read_results(self, actions: list, results: list) -> None:
        super().read_results(actions, results)
        for action, result in zip(actions, results):
            if action["type"] == "offer" and result["ok"] is not True and self.open_offers.pop((action["gigId"], action["driverId"]), None):
                self.stats["chain_refused"] += 1

    def handle(self, event: dict) -> None:
        kind, gig = event["kind"], event.get("gigId")
        if kind == "gig_booked":
            self.live[gig] = {"driver": event["driverId"], "picked": None, "left": kit.pickups(self.posts[gig]) if gig in self.posts else 1}
            self.new_holds.append(gig)
        elif kind in ("gig_dropped", "no_show"):
            self.live.pop(gig, None)
            if gig in self.chained:
                self.chained.discard(gig)
                self.stats["chain_dropped"] += 1
            if gig in self.posts and kit.pickups(self.posts[gig]) == 1:
                self.new_cars.append(self.posts[gig]["stops"][0]["orderId"])  # open again: ask again
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
            self.answered(event)
        super().handle(event)

    def answered(self, event: dict) -> None:
        offer = self.open_offers.pop((event["gigId"], event["driverId"]), None)
        if offer is None:
            return
        rule, answer, tag = self.rule, event["answer"], f"{round(100 * self.rule.levels[offer['level']])}"
        self.stats[f"chain_{answer}"] += 1
        self.stats[f"chain_{answer}_{tag}"] += 1
        if answer == "accepted":
            self.chained.add(event["gigId"])
            for name in ("fee", "app", "typical", "reference"):
                self.stats[f"chain_{name}"] += offer[name]
            self.stats[f"chain_fee_{tag}"] += offer["fee"]
            self.stats[f"chain_typical_{tag}"] += offer["typical"]
        elif answer == "declined" and offer["level"] + 1 < len(rule.levels):
            self.later.append((self.now, offer["order"], event["driverId"], offer["level"] + 1, offer["tries"]))
        elif answer == "expired" and offer["tries"] < rule.retry:
            self.later.append((self.planning_minute(), offer["order"], event["driverId"], offer["level"], offer["tries"] + 1))

    def planning_minute(self) -> int:
        """The next hour at which drivers plan: 17:00 today, else 07:00 tomorrow."""
        day, minute = self.now // DAY, self.now % DAY
        if minute < 7 * HOUR - 5:
            return day * DAY + 7 * HOUR
        if minute < 17 * HOUR - 30:
            return day * DAY + 17 * HOUR
        return (day + 1) * DAY + 7 * HOUR

    # The geometry of a chain.

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

    def minutes(self, a: str, b: str) -> int:
        return 0 if a == b else self.geo.minutes.get((a, b), 10 ** 6)

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

    def candidate(self, order_id: str, gig_h: str) -> Optional[tuple[int, float, str]]:
        """(road minutes saved, way-home share, driver) when the holder of `gig_h` is a natural driver for the car."""
        rule, hold, gig_c = self.rule, self.live.get(gig_h), self.open_car(order_id)
        if hold is None or gig_c is None or gig_c == gig_h or hold["driver"] not in self.homes:
            return None
        shape = self.shape(gig_h)
        if shape is None:
            return None
        order, home = self.orders[order_id], self.homes[hold["driver"]]
        leg = order["legs"][0]
        hop = self.minutes(shape[1], leg["pickup"]["placeId"])
        if hop > rule.reach:
            return None
        saved = self.minutes(shape[1], home) - self.minutes(leg["delivery"]["placeId"], home) - hop
        share = saved / max(1, self.geo.drive(leg))
        if share < rule.share:
            return None
        if self.posts[gig_c]["audience"].get("manualLicence") and self.licence.get(hold["driver"]) != "manual":
            return None
        if not self.after(shape, hold["picked"], order, gig_c, hop):
            return None
        return saved, min(1.0, share), hold["driver"]

    # The offers.

    def send_offer(self, order_id: str, driver: str, share: float, level: int, tries: int) -> bool:
        rule, day, gig = self.rule, self.now // DAY, self.open_car(order_id)
        if gig is None or (gig, driver) in self.open_offers:
            return False
        if not 7 * HOUR <= self.now % DAY < 23 * HOUR - 10:  # no driver reads an offer at night: at 07:00
            self.later.append(((day if self.now % DAY < 7 * HOUR else day + 1) * DAY + 7 * HOUR, order_id, driver, level, tries))
            return False
        sent = self.offered.setdefault(gig, {})
        if self.offers_on[driver, day] >= 3 or sum(1 for at in sent.values() if at > self.now - 10) >= 3:
            self.stats["chain_no_room"] += 1
            return False
        order = self.orders[order_id]
        typical = self.policy.steady(self, self.requests[order_id], order["legs"][0], self.typical(order), self.policy.p.road_fee_blend)
        fee = round(typical * (1 - rule.levels[level] * share))
        schedule = self.posts[gig]["schedule"]
        app = max((step["feeCents"] for step in schedule if step["at"] <= self.now), default=schedule[0]["feeCents"])
        if app - fee < rule.min_gain:
            self.stats["chain_small"] += 1
            return False
        self.outbox.append({"type": "offer", "gigId": gig, "driverId": driver, "feeCents": fee})
        sent[driver] = self.now
        self.offers_on[driver, day] += 1
        self.open_offers[gig, driver] = {"order": order_id, "level": level, "tries": tries, "fee": fee, "app": app, "typical": round(typical), "reference": self.requests[order_id]["referenceFeeCents"]}
        self.stats["chain_offers"] += 1
        self.stats[f"chain_sent_{round(100 * rule.levels[level])}"] += 1
        if tries:
            self.stats["chain_again"] += 1
        return True

    def best_for(self, order_id: str, driver: str) -> Optional[tuple[int, float, str]]:
        found = [c for c in (self.candidate(order_id, gig) for gig, hold in list(self.live.items()) if hold["driver"] == driver) if c]
        return max(found) if found else None

    def chains(self) -> None:
        """Looks for natural drivers for the cars that have just come into the app and for the gigs that have just
        been booked, and sends the offers that are due."""
        rule = self.rule
        cars, self.new_cars = list(dict.fromkeys(self.new_cars)), []
        holds, self.new_holds = list(dict.fromkeys(self.new_holds)), []
        due = [item for item in self.later if item[0] <= self.now]
        self.later = [item for item in self.later if item[0] > self.now]
        wanted: dict[tuple[str, str], tuple] = {}

        def want(order_id: str, found: Optional[tuple], level: int = 0, tries: int = 0, first: bool = True) -> None:
            if found is None or (first and (order_id, found[2]) in self.tried):
                return
            key = (order_id, found[2])
            if key not in wanted or found[0] > wanted[key][0]:
                wanted[key] = (found[0], found[1], level, tries)

        if rule.on_post:
            for order_id in cars:
                if self.open_car(order_id):
                    for gig in list(self.live):
                        want(order_id, self.candidate(order_id, gig))
        if rule.on_book:
            for gig in holds:
                if gig in self.live:
                    for order_id in list(self.orders):
                        if self.open_car(order_id):
                            want(order_id, self.candidate(order_id, gig))
        for _, order_id, driver, level, tries in due:
            want(order_id, self.best_for(order_id, driver), level, tries, first=False)
        for (order_id, driver), (saved, share, level, tries) in sorted(wanted.items(), key=lambda item: -item[1][0]):
            self.tried.add((order_id, driver))
            self.send_offer(order_id, driver, share, level, tries)

    def tick(self) -> None:
        super().tick()
        self.chains()


def wake_more(world, desk: ChainDesk) -> None:
    """The lab steps a practice week from one event that needs an answer to the next. This desk also answers a
    booking and an offer's answer, and wants to be called at the minute an offer is due again."""
    plain = world.advance

    def advance(to=None, by=None, until=None, max=None, actions=()):
        if until is not None:
            until = list(dict.fromkeys(list(until) + ["gig_booked", "offer_answered"]))
            due = min((item[0] for item in desk.later), default=None)
            if due is not None and due > desk.now:
                max = due if max is None else min(max, due)
        return plain(to=to, by=by, until=until, max=max, actions=actions)

    world.advance = advance


def make(client, world, level: int, now: int, params: Params, rule: Chain = Chain(), wake: bool = True):
    desk = ChainDesk(world, level, now, Policy(params), Geo(client.map()), rule)
    desk.meet(world.roster())
    if wake:
        wake_more(world, desk)
    return desk
