"""On-time line of the leaders/ swarm: punctuality that costs no fee. Shared code, fourth version (ld_ontime_*4 use it): as
ld_ontime_w3, and a car whose last pickup has passed is posted at the cheap late fees at once (`OnTimePolicy.fees`). Version 7
tests "now + drive > deadline" for that, which misses a car whose pickup site has closed for the day: 2.5 such cars a week
are booked at 1.94 typical fees for a delivery that is late whatever we pay. With our own windows every car without a driver
leaves the app at its last pickup, so the windows turned that leak into 14 cars a week at 1.6 typical fees (versions 1 to 3).
Third version (ld_ontime_*3):
ld_ontime_w2 (a deadline warning that the world repeats because OUR window ran out is not counted twice by the guard), and a
late driver is released only when a new driver can realistically still come: with at least 3 hours to the last pickup AND
at least the car's own drive time (in the first 12 real weeks 4 of 6 long drives released found nobody and came a day late
at 25 to 50% back instead of minutes late at 10%; 10 of 10 shorter drives were on time).

What the 60 version 7 weeks show (leaders/ontime/REPORT.md):

1. A booked driver is free to plan the pickup anywhere inside the pickup stop's window, and tells us (`driver_late`) only
   when the plan leaves that window. Version 7 gives the pickup no window of its own, so the window is the order's and
   runs to the deadline: a driver who plans to collect the car after the last minute that can still be on time says
   nothing and brings it late. 140 of 769 late cars are such cars (a driver held them from before the warning and
   collected them after the last pickup); 90 more were collected in the last minutes and lost on the road.
   -> `window`: every single car at a dealer site gets a pickup window that ends a little before its last pickup; a pair
      gets one on its first pickup. The driver now plans inside it or tells us, hours ahead.
   -> `act`: on `driver_late` we keep a driver who still comes in time and release (free of charge) one who does not
      while a new driver can still be found; the car is posted again at once.

2. Three kinds of car are late far more often than their margin pays for, and all three are known at the quote:
   short-notice cars (under 6 hours to find a driver) quoted on a flu day (16.5% late, 10 euros a car) or while five or
   more of today's cars still have no driver (18.6%), and drives of 7 hours and more with under 30 hours of notice (37%).
   -> `select`: the short-notice exception is off on such a day, and a drive of 7 hours and more needs 30 hours.

3. A fault in version 7's pairing: when a driver gives a booked pair back, the pair gig is open again but the desk no longer
   lists it as a pair. The next new order that makes a round trip with ONE of its cars withdraws the whole gig and
   posts a new pair with that car; the other car is left without any gig and is never delivered: 36 cars in 60 weeks,
   each a late order and a penalty of twice its price (122 euros a week with the lost revenue).
   -> `fix`: an open pair is never a partner for a new order, and a pair that comes back is watched again, so it is
      taken apart in time like any pair without a driver.
"""
from __future__ import annotations

from dataclasses import dataclass

from spread import starter as kit

from dispatch import desk as desk_module
from dispatch.desk import Desk
from dispatch.geo import DAY, HOUR, Geo, needs_charging
from dispatch.policy import Params, Policy


@dataclass(frozen=True)
class Parts:
    window: bool = True  # own pickup windows that end before the last pickup
    act: bool = True  # answer `driver_late`
    select: bool = False  # the three quote rules
    fix: bool = False  # a pair that a driver gave back is not taken apart by a new pair (see `post_pair`)
    late_path: bool = False  # the cheap late fees from the minute the last pickup has passed, also without windows
    buffer: int = 10  # minutes, plus
    buffer_share: float = 0.10  # ... this share of the drive, by which a single car's pickup window ends before its last pickup
    pair_buffer: int = 20  # minutes by which a pair's first pickup window ends before the pair's last start
    keep_share: float = 0.03  # a late driver is kept when they still collect the car this share of the drive before the last pickup
    min_left: int = 180  # minutes to the last pickup under which a late driver is kept: too late to find another
    left_per_drive: float = 1.0  # ... and under this many times the car's drive: a long drive needs a driver with the day free
    long_hours: float = 7.0  # `select`: a drive this long ...
    long_notice: float = 30.0  # ... is quoted only with this many hours to find a driver
    open_today: int = 5  # `select`: with this many of today's cars still without a driver, no short-notice car is quoted


class OnTimePolicy(Policy):
    def __init__(self, params: Params, parts: Parts):
        super().__init__(params)
        self.parts = parts

    def fees(self, desk: "OnTimeDesk", order: dict, cars: int, urgent: bool) -> list[dict]:
        """A single car whose last pickup has passed cannot be on time: from here a fee buys only a smaller refund, so
        it starts low and climbs slowly (the base desk's own late path, entered at the right moment)."""
        p = self.p
        last = desk.last_pickup.get(order["id"], order["lastPickupAt"])
        if order["lastPickupAt"] - last > 12 * HOUR:  # the dealer moved the deadline after we read the note
            last = order["lastPickupAt"]
        if (self.parts.window or self.parts.late_path) and p.late_open and desk.level >= 2 and len(order["legs"]) == 1 and cars == 1                 and desk.now > last and desk.now + desk.geo.drive(order["legs"][0]) <= order["deadline"]:
            typical = desk.typical(order)
            typical = self.steady(desk, desk.requests[order["id"]], order["legs"][0], typical, p.road_fee_blend)
            path = ((0, p.late_open), (6, (2 * p.late_open + p.late_top) / 3), (12, (p.late_open + 2 * p.late_top) / 3), (24, p.late_top), (36, p.late_fee), (48, p.urgent_top))
            desk.stats["late_path_posts"] += 1
            return self.settle([{"at": desk.now + hours * HOUR, "feeCents": max(1, round(typical * fee))} for hours, fee in path], hold=False)
        return super().fees(desk, order, cars, urgent)

    def find_hours(self, desk: "OnTimeDesk", request: dict) -> float:
        base = super().find_hours(desk, request)
        if not self.parts.select:
            return base
        p, leg = self.p, request["legs"][0]
        if base < p.min_find_hours and not leg["pickup"]["privateAddress"]:  # the short-notice exception for an easy car
            if desk.flu_day == desk.now // DAY:
                desk.stats["select_flu"] += 1
                return p.min_find_hours
            if desk.open_today() >= self.parts.open_today:
                desk.stats["select_open"] += 1
                return p.min_find_hours
        if desk.geo.drive(leg) >= self.parts.long_hours * HOUR:
            return max(base, self.parts.long_notice)
        return base


class OnTimeDesk(Desk):
    def __init__(self, world, level, now, policy: OnTimePolicy, geo: Geo):
        super().__init__(world, level, now, policy, geo)
        self.parts = policy.parts
        self.full: set[str] = set()  # orders whose buffered window ran out without a driver: from then the window runs to the last pickup
        self.buffered: dict[str, str] = {}  # gig -> order, for gigs posted with a window that ends before the last pickup
        self.pair_last: dict[str, int] = {}  # pair gig -> the last minute to start it, kept after it is booked
        self.mute: dict[str, int] = {}  # order -> the minute at which a repeated deadline warning is ours to ignore (see `handle`)

    # What the policy asks.

    def open_today(self) -> int:
        """Our cars that must be collected today and have no driver yet."""
        today = self.now // DAY
        return sum(1 for order_id, order in self.orders.items()
                   if None in order["deliveredAt"] and self.last_pickup.get(order_id, order["lastPickupAt"]) // DAY == today
                   and self.now < self.last_pickup.get(order_id, order["lastPickupAt"])
                   and not any(gig in self.booked for gig in self.gigs_of(order_id)))

    # 1. Pickup windows of our own.

    def stops(self, order: dict, legs: list[int], retry: kit.Retry, facts) -> list[dict]:
        stops = super().stops(order, legs, retry, facts)
        if not self.parts.window or len(legs) != 1 or len(order["legs"]) != 1:
            return stops
        stated = order["legs"][0]
        if stated["pickup"]["privateAddress"]:
            return stops  # a private seller's slot is the window already
        last = self.last_pickup.get(order["id"], order["lastPickupAt"])
        if self.now >= last:
            return stops  # too late to be on time: no window, any driver may take it
        slack = 0 if order["id"] in self.full else int(self.parts.buffer + self.parts.buffer_share * self.geo.drive(stated))
        pickup = stops[0]
        window = pickup.get("window") or dict(stated["pickup"]["window"])
        start = max(window["from"], self.now)
        end = min(window["to"], last - slack)
        if end < start + HOUR:  # the buffer would squeeze the window under an hour: end it at the last pickup itself
            end, slack = min(window["to"], last), 0
        if end <= start or end >= window["to"]:
            return stops
        stops[0] = {**pickup, "window": {"from": window["from"], "to": end}}
        self.stats["windows"] += 1
        return stops

    def carry(self, action: dict, gig_id: str) -> None:
        super().carry(action, gig_id)
        orders = list(dict.fromkeys(stop["orderId"] for stop in action["stops"]))
        if len(orders) == 1 and "window" in action["stops"][0] and orders[0] in self.orders:
            order = self.orders[orders[0]]
            if action["stops"][0]["window"]["to"] < self.last_pickup.get(order["id"], order["lastPickupAt"]):
                self.buffered[gig_id] = order["id"]

    def repost(self, gig_id: str) -> None:
        """A buffered window ran out with no driver. The car can still be on time: post it again with the window to its last
        pickup, as the note says, instead of the starter's post without any window."""
        order_id = self.buffered.pop(gig_id, None)
        order = self.orders.get(order_id) if order_id else None
        if order is not None and self.leg_gigs.get(order_id, {}).get(0) == gig_id and gig_id not in self.booked \
                and self.now < self.last_pickup.get(order_id, order["lastPickupAt"]) and None in order["deliveredAt"]:
            self.leg_gigs[order_id].pop(0, None)
            self.full.add(order_id)
            self.alone.add(order_id)  # no time left to wait for a partner
            if order_id in self.urgent:
                self.mute[order_id] = self.now  # the world warns again when a gig leaves the app: the guard has this car already
            self.stats["window_reposts"] += 1
            return self.post(order, [0])
        super().repost(gig_id)

    def post_pair(self, order: dict) -> bool:
        """As the desk's own, with a window on the first pickup that ends `pair_buffer` minutes before the pair's last start."""
        if not self.parts.window and not self.parts.fix:
            return super().post_pair(order)
        if not self.plain(order):
            return False
        best = None
        for other in self.orders.values():
            gigs = self.gigs_of(other["id"])
            if other["id"] == order["id"] or len(gigs) != 1 or gigs[0] in self.booked or gigs[0] in self.pairs or not self.plain(other):
                continue
            if self.parts.fix and self.is_pair(gigs[0]):
                continue  # a pair that came back from a driver: taking one car out of it would leave the other without a gig
            for first, second in ((order, other), (other, order)):
                start = self.pair_start(first, second)
                if start is not None and (best is None or start > best[0]):
                    best = (start, first, second, gigs[0])
        if best is None:
            return False
        start, first, second, old_gig = best
        self.send()
        if self.world.act([{"type": "withdraw", "gigId": old_gig}])[0]["ok"] is not True:
            return False
        self.forget(old_gig)
        self.buffered.pop(old_gig, None)
        stops = []
        for each in (first, second):
            leg = each["legs"][0]
            km = self.geo.km[(leg["pickup"]["placeId"], leg["delivery"]["placeId"])]
            stops += [{"orderId": each["id"], "leg": 0, "kind": "pickup", "withPlates": False, "withCharging": needs_charging(leg, km)},
                      {"orderId": each["id"], "leg": 0, "kind": "delivery"}]
        opens = max(first["legs"][0]["pickup"]["window"]["from"], self.now)
        if self.parts.window and start - self.parts.pair_buffer >= opens + HOUR:
            stops[0]["window"] = {"from": first["legs"][0]["pickup"]["window"]["from"], "to": start - self.parts.pair_buffer}
        typical = (self.typical(first) + self.typical(second)) * self.policy.p.pair_fee
        manual = any(self.facts(self.requests[each["id"]]).manual for each in (first, second))
        action = {"type": "post", "stops": stops, "audience": {"experienced": False, "manualLicence": manual}, "schedule": self.policy.schedule(self, typical, start, False)}
        result = self.world.act([action])[0]
        if result["ok"] is not True:
            self.refused[f"pair: {result['reason'][:80]}"] += 1
            self.alone.update((first["id"], second["id"]))
            other = second if first["id"] == order["id"] else first
            self.post(other, [0])
            return False
        self.carry(action, result["id"])
        self.pairs[result["id"]] = start
        self.pair_last[result["id"]] = start
        self.stats["pairs_posted"] += 1
        return True

    def pairable(self, request: dict, last: int) -> bool:
        if not self.parts.fix:
            return super().pairable(request, last)
        if not self.policy.p.pairs:
            return False
        new = {"id": request["id"], "legs": request["legs"], "lastPickupAt": last, "deliveredAt": [None] * len(request["legs"])}
        if not self.plain(new):
            return False
        for other in self.orders.values():
            gigs = self.gigs_of(other["id"])
            if len(gigs) != 1 or gigs[0] in self.booked or gigs[0] in self.pairs or self.is_pair(gigs[0]) or not self.plain(other):
                continue
            if self.pair_start(new, other) is not None or self.pair_start(other, new) is not None:
                return True
        return False

    # 2. A driver who says they will be late.

    def handle(self, event: dict) -> None:
        if event["kind"] == "gig_dropped" and self.parts.select and not (self.policy.p.flu or self.policy.p.budget):
            self.flu_sign(event)  # the select rule needs to know the flu day
        repeat = event["kind"] == "deadline_close" and self.mute.get(event["orderId"], -10) >= event["at"] - 1
        super().handle(event)
        if repeat:  # the guard counts warnings as a sign of a hard week: one car, one warning, as before the windows
            self.mute.pop(event["orderId"], None)
            self.warnings.pop()
            self.stats["warnings_muted"] += 1
        if event["kind"] == "driver_late":
            self.late_driver(event)
        elif event["kind"] in ("gig_dropped", "no_show") and self.parts.fix and event["gigId"] in self.pair_last and self.is_pair(event["gigId"]):
            if any(event["gigId"] in legs.values() for legs in self.leg_gigs.values()):
                self.pairs[event["gigId"]] = self.pair_last[event["gigId"]]  # open again: `tick` takes it apart when its time comes
                self.stats["pairs_back"] += 1

    def late_driver(self, event: dict) -> None:
        """The booked driver will collect the first car at `pickupAt`, after its window. Keep them when that is still in
        time; otherwise release them, which is free after this notice, and post the car again while another driver can
        still be found. With less than `min_left` to the last pickup nobody else comes in time either: keep the driver,
        a car that is minutes late costs a tenth of its price, a car without a driver a quarter."""
        gig_id, at = event["gigId"], event["pickupAt"]
        self.stats["late_notices"] += 1
        if not self.parts.act or gig_id not in self.booked:
            return
        orders = [order_id for order_id, legs in self.leg_gigs.items() if gig_id in legs.values()]
        if not orders or any(order_id not in self.orders for order_id in orders):
            return
        if len(orders) == 1:
            order = self.orders[orders[0]]
            if len(order["legs"]) != 1:
                return
            last = self.last_pickup.get(order["id"], order["lastPickupAt"])
            if order["lastPickupAt"] - last > 12 * HOUR:  # the dealer moved the deadline (snow) after the car was booked
                last = order["lastPickupAt"]
            drive = self.geo.drive(order["legs"][0])
            in_time = at <= last - self.parts.keep_share * drive
        else:
            last = self.pair_last.get(gig_id)
            if last is None:
                return
            in_time, drive = at <= last, 0
        if in_time:
            self.stats["late_kept_in_time"] += 1
            return
        if last - self.now < max(self.parts.min_left, self.parts.left_per_drive * drive):
            self.stats["late_kept_no_time"] += 1
            return
        self.send()
        result = self.world.act([{"type": "release", "gigId": gig_id}])[0]
        if result["ok"] is not True:
            self.refused[f"release: {result['reason'][:80]}"] += 1
            return
        self.stats["late_released"] += 1
        self.booked.discard(gig_id)
        self.buffered.pop(gig_id, None)
        for order_id in self.forget(gig_id):
            self.alone.add(order_id)
            self.full.add(order_id)
            order = self.orders[order_id]
            if None in order["deliveredAt"]:
                if self.last_pickup.get(order_id, order["lastPickupAt"]) - self.now <= 3 * HOUR:
                    if order_id in self.urgent:
                        self.mute[order_id] = self.now
                    self.urgent.add(order_id)  # inside the warning already: the steep fees at once
                self.post(order, kit.undelivered(order))


def build(client, world, level: int, now: int, params: Params, parts: Parts) -> OnTimeDesk:
    if parts.act and "driver_late" not in desk_module.WAKE_ON:
        desk_module.WAKE_ON.append("driver_late")  # the practice clock must stop at the notice, as the live stream does
    policy = OnTimePolicy(params, parts)
    desk = OnTimeDesk(world, level, now, policy, Geo(client.map()))
    desk.meet(world.roster())
    return desk


def make(client, world, level: int, now: int, params: Params) -> OnTimeDesk:
    return build(client, world, level, now, params, Parts())
