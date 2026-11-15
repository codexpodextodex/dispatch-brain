"""On-time line, the part that is not in the base yet: pickup windows of our own, and an answer to `driver_late`.
Nothing else. The pairing fix and the cheap late fees are base settings now, and this desk is played on top of them:

    --set design=ld_ontime_win5 pair_safe=1 late_by_pickup=1        against        --set pair_safe=1 late_by_pickup=1

Why. A booked driver plans the pickup anywhere inside the pickup stop's window and tells us (`driver_late`) only when the
plan leaves that window. The base posts no pickup window, so the window is the order's and runs to the deadline: a driver
who plans to fetch the car after the last minute that can still be on time says nothing and delivers late (141 of 769 late
cars in version 7's 60 weeks; a driver who does another gig of ours first collects after the last pickup 2.06% of the
time, any other driver 0.15%).

What.
- `stops`: a single car at a dealer site gets a pickup window that ends exactly at its last pickup. Nothing changes for a
  driver who comes in time; one who plans to come later must say so. Without a driver the gig now leaves the app the
  minute after the last pickup and is posted again without windows, as the base does at the deadline; the base's
  `late_by_pickup=1` then gives it the cheap late fees (without that setting such a car is posted at the steep fees:
  14 cars a week at 1.6 typical fees in the first runs of this design).
- `post_pair`: the base's own, with one line added: the pair's first pickup gets a window that ends at the pair's last start.
- `late_driver`: the answer to the notice. The driver is released (free after the notice) and the car posted again when
  a new driver can still come: at least 3 hours and at least the car's own drive time before the window ends. Otherwise
  the driver is kept. A notice that only says the dealer moved the deadline a day (snow) and the driver follows is ignored.

Restart. The desk keeps NO book of its own, so a restart loses nothing:
- the windows live in the world: every gig in the snapshot carries its stops with their windows, and the starter's
  `rejoin` puts them back into `self.posts`;
- `late_driver` reads the end of the window from `self.posts` (the last minute a new driver could collect the car), the
  order from `self.orders`, and nothing else; for a pair the window's end is the pair's last start;
- a notice that came while the desk was down is answered by `rejoin`: the newest `driver_late` in the history of every gig
  that the snapshot still shows as booked by that driver (not yet left) goes through `late_driver` again. The rule depends
  only on the clock, so answering twice gives the same answer or, later, keeps the driver;
- the practice clock wakes on `driver_late` because `build` adds it to the desk module's wake list each time a desk is
  made, also after a restart; the final's live stream brings the event by itself.
The earlier versions' books are gone with what needed them: `buffered` and `full` belonged to the window that ended BEFORE
the last pickup (dropped: it cost more in give-backs than it saved), `mute` to the warning that such a window repeated,
`pair_last` is the first stop's window, and with `pair_safe=1` also the base's own `Desk.pairs`.
After a restart `Desk.last_pickup` (the base's book of note-tightened last pickups) is empty, as in the base: a car posted
again then gets its window from the world's `lastPickupAt`, which is never earlier than the note's.
"""
from __future__ import annotations

from spread import starter as kit

from dispatch import desk as desk_module
from dispatch.desk import Desk
from dispatch.geo import HOUR, Geo, needs_charging
from dispatch.policy import Params, Policy

MIN_LEFT = 3 * HOUR  # a late driver is released only with this long to the end of the window, and the car's own drive time


class WindowDesk(Desk):
    window = True  # pickup windows that end at the last pickup
    act = True  # answer `driver_late`
    mirror = False  # the offline check only: run our copy of `post_pair` without its added line, to compare it with the base's

    def stops(self, order: dict, legs: list[int], retry: kit.Retry, facts) -> list[dict]:
        stops = super().stops(order, legs, retry, facts)
        if not self.window or len(legs) != 1 or len(order["legs"]) != 1 or order["legs"][0]["pickup"]["privateAddress"]:
            return stops  # a private seller's slot is the window already
        last = self.last_pickup.get(order["id"], order["lastPickupAt"])
        window = stops[0].get("window") or dict(order["legs"][0]["pickup"]["window"])
        if last <= max(window["from"], self.now) or last >= window["to"]:
            return stops  # too late to be on time (any driver may take it), or the note's window is the tighter one
        stops[0] = {**stops[0], "window": {"from": window["from"], "to": last}}
        self.stats["windows"] += 1
        return stops

    def post_pair(self, order: dict) -> bool:
        """`Desk.post_pair` as it stands with `pair_safe`, and one line more: the window on the first pickup."""
        if not (self.window or self.mirror):
            return super().post_pair(order)
        if not self.plain(order):
            return False
        best = None
        for other in self.orders.values():
            gigs = self.gigs_of(other["id"])
            if other["id"] == order["id"] or len(gigs) != 1 or gigs[0] in self.booked or gigs[0] in self.pairs or not self.plain(other):
                continue
            if self.policy.p.pair_safe and self.is_pair(gigs[0]):
                continue
            for first, second in ((order, other), (other, order)):
                start = self.pair_start(first, second)
                if start is not None and (best is None or start > best[0]):
                    best = (start, first, second, gigs[0])
        if best is None:
            return False
        start, first, second, old_gig = best
        slack = self.policy.p.pair_urgent_first
        if slack and self.last_pickup.get(second["id"], second["lastPickupAt"]) < self.last_pickup.get(first["id"], first["lastPickupAt"]):
            reverse = self.pair_start(second, first)
            if reverse is not None and reverse >= start - slack:
                start, first, second = reverse, second, first
        self.send()
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
        if self.window and start >= max(opens, self.now) + HOUR:  # the added line: the driver starts by the pair's last start, or says so
            stops[0]["window"] = {"from": opens, "to": start}
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
        self.stats["pairs_posted"] += 1
        return True

    def handle(self, event: dict) -> None:
        super().handle(event)
        if event["kind"] == "driver_late":
            self.late_driver(event)

    def late_driver(self, event: dict) -> None:
        """The booked driver will collect the first car at `pickupAt`, after its window: the car will be late. Release the
        driver and post the car again while a new driver can still come; otherwise keep the driver."""
        gig_id, post = event["gigId"], self.posts.get(event["gigId"])
        self.stats["late_notices"] += 1
        if not self.act or post is None or gig_id not in self.booked:
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
        if last - self.now < max(MIN_LEFT, self.geo.drive(first["legs"][0]) if single else 0):
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
                    self.urgent.add(order_id)  # inside the world's warning already: the steep fees at once
                self.post(order, kit.undelivered(order))

    def rejoin(self, snapshot: dict, history: list) -> None:
        """After a restart: also answers the `driver_late` notices that came while the desk was down."""
        super().rejoin(snapshot, history)
        if not self.act:
            return
        holder = {gig["id"]: gig.get("driverId") for gig in snapshot["gigs"] if gig["status"] == "booked"}  # booked, not yet left
        newest = {event["gigId"]: event for event in history if event["kind"] == "driver_late"}
        for gig_id, event in newest.items():
            if holder.get(gig_id) == event["driverId"]:
                self.late_driver(event)


def build(client, world, level: int, now: int, params: Params, window: bool = True, act: bool = True, mirror: bool = False) -> WindowDesk:
    if act and "driver_late" not in desk_module.WAKE_ON:
        desk_module.WAKE_ON.append("driver_late")  # the practice clock stops at the notice, as the live stream delivers it
    desk = WindowDesk(world, level, now, Policy(params), Geo(client.map()))
    desk.window, desk.act, desk.mirror = window, act, mirror
    desk.meet(world.roster())
    return desk


def make(client, world, level: int, now: int, params: Params) -> WindowDesk:
    return build(client, world, level, now, params)
