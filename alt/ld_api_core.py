"""API line of the leaders/ swarm (leaders/api/AUDIT.md): a car that can no longer be on time, and a pair that comes back.

Sentences of RULES.md that version 7 does not act on:

1. "A driver books a gig only when they can reach every stop inside its window ... Thus a gig can get no driver
   before any of its windows ends." A gig posted while the car could still be on time keeps the order's windows, so
   from the minute after `lastPickupAt` no driver can book it. It then sits dead in the app until the pickup site
   closes and `gig_expired` comes. Measured on version 7's 60 weeks (leaders/api/deadtime.py): 451 of 456 bookings
   after the last pickup were on a gig posted after it; 6.9 cars a week lose 2.5 hours on average, the long drives 5
   to 8 hours of the afternoon in which drivers plan the next day, and 54 to 82% of those arrive more than 24 hours late.
   -> `repost`: in the minute after the last pickup, withdraw the gig and post it again without windows ("when no
      driver can still reach every stop inside the order's windows, the stops without a window of their own run to
      the end of the world").

2. The account's table of refunds is a staircase: a quarter of the price up to 24 hours late, half up to two
   business days, then all of it. Version 7's fees for a late car climb with the hours since the repost (1.0 typical
   fees, 1.3 a day later, 1.8 after 36 hours), whatever step the car stands before, and where the pickup site
   closes before the drive runs out it still pays the urgent ladder (1.8 to 2.4) for a car that is late already.
   -> `by_last`: a car is late, for its fees, from the minute after its last pickup.
   -> `bands`: a late car is a new car against its next step: its last pickup for "24 hours late" (or "two business
      days late"), a fee that opens at the late opening fee and rises, when drivers plan that day, to at most what
      the step is worth (`share` of the refund it saves). When that last pickup passes too, the fee goes DOWN again
      ("a reprice ... its fees may be lower than the fee in the app") and aims at the next step.
   -> `windows`: "At other stops [a stop's own window] may end after the order's window, so a late car can still be
      collected and delivered." The late gig's pickup window ends at the last pickup for the step and its delivery
      window at the step itself: the fee that buys the step is paid only to a driver who plans to make it. Without
      them the stops run to the end of the world, and a driver may book the car for any later day.

3. A bug of version 7, found from the account line `undelivered_penalty` (leaders/api/orphans.py). The desk forgets
   that a gig is a pair once a driver books it. When that driver gives it back, "the gig is open again in the app":
   an open gig with two cars that the desk takes for a single car. The next order that makes a round trip with its
   first car takes the gig out and posts a new pair, and the second car is left without any gig for the rest of the
   week: 35 cars in 60 weeks, each never delivered (no price, twice the price as penalty, a late order).
   -> `pair_fix`: a pair that comes back after a drop or a no-show is a pair again: it is taken apart when its time
      comes, as before it was booked, and no new order can take one of its cars.

`Parts` chooses the pieces; the modules ld_api_* set them. Everything else is version 7."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from spread import starter as kit

from dispatch.desk import Desk
from dispatch.geo import DAY, HOUR, PLATES_MINUTES, Geo, last_pickup
from dispatch.notes import apply
from dispatch.policy import Params, Policy

WORLD_END = 9 * DAY + 22 * HOUR  # the second Wednesday at 22:00


@dataclass(frozen=True)
class Parts:
    repost: bool = True  # post a gig again, without windows, in the minute after its car's last pickup
    by_last: bool = True  # the fees of a late car from the minute after its last pickup, not only when the drive no longer fits
    bands: bool = False  # the fees of a late car aim at the next step of the refund table
    share: float = 0.8  # ... and never pay more of the refund that the step saves than this
    windows: bool = False  # ... and the gig carries windows of its own that end with that step, so only a driver who makes it can book
    pair_fix: bool = False  # a pair that a driver gives back is known as a pair again
    keep_count: bool = False  # the guard sees a warning at the repost, as it sees the world's second warning when version 7's gig expires
    final_open: float = 1.5  # past the last step (the whole price is back already): what is left is the penalty for a car never delivered


def business_days_after(minute: int, days: int) -> int:
    day = minute // DAY
    while days:
        day += 1
        if day % 7 < 5:
            days -= 1
    return day * DAY + minute % DAY


class ApiPolicy(Policy):
    def __init__(self, params: Params, parts: Parts):
        super().__init__(params)
        self.parts = parts

    def late(self, desk: "ApiDesk", order: dict) -> bool:
        """Whether the car can no longer be on time: its last pickup has passed (ours, as the note changes it, or the
        world's), or the drive no longer fits before the deadline (version 7's own test)."""
        return desk.now > desk.late_from(order) or desk.now + desk.geo.drive(order["legs"][0]) > order["deadline"]

    def fees(self, desk: "ApiDesk", order: dict, cars: int, urgent: bool) -> list[dict]:
        if not (self.parts.by_last or self.parts.bands) or desk.level < 2 or len(order["legs"]) != 1 or cars != 1 or not self.late(desk, order):
            return super().fees(desk, order, cars, urgent)
        typical = self.steady(desk, desk.requests[order["id"]], order["legs"][0], desk.typical(order), self.p.road_fee_blend)
        if self.parts.bands and not order["legs"][0]["pickup"]["privateAddress"]:
            return self.band_fees(desk, order, typical)
        p = self.p  # version 7's fees for a late car, from now
        path = ((0, p.late_open), (6, (2 * p.late_open + p.late_top) / 3), (12, (p.late_open + 2 * p.late_top) / 3), (24, p.late_top), (36, p.late_fee), (48, p.urgent_top))
        return self.settle([{"at": desk.now + hours * HOUR, "feeCents": max(1, round(typical * fee))} for hours, fee in path], hold=False)

    def band_fees(self, desk: "ApiDesk", order: dict, typical: float) -> list[dict]:
        """Fees for a late car: against the next step of the refund table that a driver can still make."""
        p, now, leg = self.p, desk.now, order["legs"][0]
        drive = desk.geo.drive(leg)

        def step(at: float, fee: float) -> dict:
            return {"at": int(at), "feeCents": max(1, round(typical * fee))}

        target = desk.next_band(order)
        desk.aim[order["id"]] = target[0] if target else WORLD_END
        if target is None:  # every step is behind it: only a car never delivered costs more now
            top = max(p.urgent_top, self.parts.final_open)
            return self.settle([step(now + hours * HOUR, self.parts.final_open + (top - self.parts.final_open) * k / 3) for k, hours in enumerate((0, 6, 12, 24))], hold=False)
        last, saved = target[0], target[1]  # the last pickup that still makes the step, and the share of the price it saves
        cap = min(p.late_fee, max(p.late_top, p.late_open + self.parts.share * saved * order["priceCents"] / max(1.0, typical)))
        middle = p.late_open + 0.6 * (cap - p.late_open)
        warning = last - int(p.late_lead * HOUR)
        if now >= warning:
            return [step(now, cap)]
        early = p.early_long if p.early_long and drive >= p.long_hours * HOUR else p.early_hour
        if last % DAY < early * HOUR:  # a pickup before lunch, or a long drive: drivers plan it the evening before
            top_at = last // DAY * DAY - DAY + p.evening_hour * HOUR
        else:
            top_at = warning - (p.lead_hours - 3) * HOUR
        top_at = min(max(top_at, now), warning)
        # As for a new car: the opening fee stands, rises to the middle by the time drivers plan that day, and to the
        # cap three hours before the last pickup. A step that is days away (a weekend between) costs nothing until its last day.
        steps = [step(now, p.late_open if top_at - now >= HOUR else middle)]
        if top_at - now >= HOUR:
            ramp_from = max(now + p.hold * (top_at - now), top_at - DAY)
            steps += [step(ramp_from + (top_at - ramp_from) * k / 4, p.late_open + (middle - p.late_open) * k / 4) for k in range(1, 5)]
        if warning - top_at >= HOUR:
            steps += [step(top_at + (warning - top_at) * k / 4, middle + (cap - middle) * k / 4) for k in range(1, 5)]
        else:
            steps.append(step(warning, cap))
        return self.settle(steps)


class ApiDesk(Desk):
    def __init__(self, world, level: int, now: int, policy: ApiPolicy, geo: Geo):
        super().__init__(world, level, now, policy, geo)
        self.parts = policy.parts
        self.posted_at: dict[str, int] = {}  # gig -> the minute we posted it
        self.aim: dict[str, int] = {}  # order -> the last pickup its late fees aim at (`bands`)
        self.aimed: dict[str, int] = {}  # gig -> the same, for the schedule the gig carries now
        self.pair_starts: dict[str, int] = {}  # pair gig -> the last minute to start it, kept while a driver holds it

    # What the policy asks.

    def late_from(self, order: dict) -> int:
        """The last minute to collect the car and still be on time: the world's, or earlier when the note says so."""
        return min(order["lastPickupAt"], self.last_pickup.get(order["id"], order["lastPickupAt"]))

    def next_band(self, order: dict) -> Optional[tuple[int, float, int]]:
        """The next step of the refund table that a driver booked now can still make: (the last pickup for it, the
        share of the price it saves, the step's own minute). 24 hours late costs a quarter of the price, two business
        days half, later the whole price."""
        request = self.requests[order["id"]]
        facts, stated = self.facts(request), order["legs"][0]
        due = min(order["deadline"], facts.deadline or order["deadline"])
        drive = self.geo.drive(stated) + (PLATES_MINUTES if facts.plates else 0)
        for line, saved in ((due + DAY, 0.25), (business_days_after(due, 2), 0.5)):
            leg = apply(stated, facts)
            leg = {**leg, "pickup": {**leg["pickup"], "window": {"from": leg["pickup"]["window"]["from"], "to": line}}}
            last = last_pickup(leg, line, drive)
            if last is not None and last > self.now + 30:
                return last, saved, line
        return None

    # A pair that comes back.

    def post_pair(self, order: dict) -> bool:
        before = set(self.pairs)
        done = super().post_pair(order)
        for gig in set(self.pairs) - before:
            self.pair_starts[gig] = self.pairs[gig]
        return done

    def handle(self, event: dict) -> None:
        super().handle(event)
        if self.parts.pair_fix and event["kind"] in ("gig_dropped", "no_show") and self.is_pair(event["gigId"]) and event["gigId"] not in self.pairs:
            # Open again with both cars: known as a pair, it is split when its time comes and no new order takes one car out of it.
            self.pairs[event["gigId"]] = self.pair_starts.get(event["gigId"], self.now)
            self.stats["pairs_reopened"] += 1

    # The gig of a late car.

    def single_open(self, order_id: str, order: dict) -> Optional[str]:
        """The gig of a single car that no driver holds; None for every other order."""
        if len(order["legs"]) != 1 or None not in order["deliveredAt"] or order["legs"][0]["pickup"]["privateAddress"]:
            return None  # a private seller's slot never extends: the dealer books a new one, and `order_changed` comes
        gigs = self.gigs_of(order_id)
        if len(gigs) != 1 or gigs[0] in self.booked or gigs[0] not in self.posts or self.is_pair(gigs[0]):
            return None
        return gigs[0]

    def last_call(self) -> None:
        for order_id, order in list(self.orders.items()):
            gig = self.single_open(order_id, order)
            if gig is None:
                continue
            dead_from = order["lastPickupAt"]  # the world's own: from the next minute the order's windows admit no driver
            if self.parts.repost and self.now > dead_from and self.posted_at.get(gig, 0) <= dead_from:
                self.post_again(order, gig)
            elif self.parts.bands and not self.parts.windows and self.now > self.late_from(order) and self.now > self.aimed.get(gig, WORLD_END):
                # the step this gig's fees aimed at is lost: start again, lower, for the next one
                schedule = self.fees_for(order, 1)
                self.outbox.append({"type": "reprice", "gigId": gig, "schedule": schedule})
                self.aimed[gig] = self.aim.get(order_id, WORLD_END)
                self.stats["band_reprices"] += 1

    def post_again(self, order: dict, gig: str) -> None:
        """The gig was posted while the car could be on time, so its windows end with the deadline and no driver can
        book it now. Take it out and post the car again."""
        self.send()  # the world must have every earlier action first
        if gig in self.booked or self.world.act([{"type": "withdraw", "gigId": gig}])[0]["ok"] is not True:
            self.posted_at[gig] = self.now  # a driver has just taken it: leave it
            return
        action = self.posts[gig]
        self.forget(gig)
        if self.post_late(order, action):
            self.stats["last_calls"] += 1
            if self.parts.keep_count:
                # The world warns again when a late car's gig expires, and version 7's guard counts that warning too
                # (1.7 warnings a warned car). Without the expiry the guard would see a third of what it sees now:
                # a lighter brake by accident. Keep its count as it is.
                self.warnings.append(self.now)

    def post_late(self, order: dict, action: dict) -> bool:
        """Posts a late car's gig again from the post that made it: without the old windows (they then run to the end
        of the world), at a late car's fees, and with `windows` inside the next step of the refund table."""
        stops = kit.without_windows(action["stops"], float("inf"))
        target = self.next_band(order) if self.parts.bands and self.parts.windows else None
        if target is not None:
            last, _, line = target
            leg = order["legs"][0]
            stops = [{**stop, "window": {"from": leg[stop["kind"]]["window"]["from"], "to": last if stop["kind"] == "pickup" else line}} for stop in stops]
        again = {"type": "post", "stops": stops, "audience": action["audience"], "schedule": self.fees_for(order, 1)}
        result = self.world.act([again])[0]
        if result["ok"] is not True and target is not None:  # the world does not take our windows: without them, as version 7 posts a late car
            self.refused[f"late windows: {result['reason'][:80]}"] += 1
            again = {**again, "stops": kit.without_windows(stops, float("inf"))}
            result = self.world.act([again])[0]
        if result["ok"] is not True:
            self.refused[f"post again: {result['reason'][:80]}"] += 1
            self.post(order, kit.undelivered(order))  # as after `gig_expired`
            return False
        self.carry(again, result["id"])
        return True

    def repost(self, gig_id: str) -> None:
        """A late gig with windows of our own has expired: the step it aimed at is lost. Post it for the next one."""
        action = self.posts.get(gig_id)
        orders = list(dict.fromkeys(stop["orderId"] for stop in action["stops"])) if action else []
        order = self.orders.get(orders[0]) if len(orders) == 1 else None
        if (self.parts.bands and self.parts.windows and order is not None and len(order["legs"]) == 1 and None in order["deliveredAt"]
                and not order["legs"][0]["pickup"]["privateAddress"] and self.leg_gigs.get(order["id"], {}).get(0) == gig_id
                and gig_id not in self.booked and self.now > order["lastPickupAt"]):
            self.send()
            self.forget(gig_id)
            if self.post_late(order, action):
                self.stats["band_reposts"] += 1
            return
        super().repost(gig_id)

    def carry(self, action: dict, gig_id: str) -> None:
        super().carry(action, gig_id)
        self.posted_at[gig_id] = self.now
        orders = list(dict.fromkeys(stop["orderId"] for stop in action["stops"]))
        if len(orders) == 1 and orders[0] in self.aim:
            self.aimed[gig_id] = self.aim[orders[0]]

    def read_results(self, actions: list, results: list) -> None:
        super().read_results(actions, results)
        for action in actions:  # a reprice by the deadline warning or after a drop: the gig's fees now aim where the policy last aimed
            if action["type"] == "reprice" and action["gigId"] in self.posts:
                orders = list(dict.fromkeys(stop["orderId"] for stop in self.posts[action["gigId"]]["stops"]))
                if len(orders) == 1 and orders[0] in self.aim:
                    self.aimed[action["gigId"]] = self.aim[orders[0]]

    def rejoin(self, snapshot: dict, history: list) -> None:
        super().rejoin(snapshot, history)
        for gig in snapshot["gigs"]:  # after a restart: when each open gig was posted; a late car's fees are set again at the first tick
            if gig["id"] in self.posts:
                self.posted_at[gig["id"]] = gig["postedAt"]
                if self.parts.bands and gig["status"] == "open":
                    self.aimed[gig["id"]] = 0

    def tick(self) -> None:
        super().tick()
        self.last_call()

    def next_timer(self) -> Optional[int]:
        """The next minute at which a car without a driver passes its last pickup, or the step its fees aim at."""
        best = None
        for order_id, order in self.orders.items():
            gig = self.single_open(order_id, order)
            if gig is None:
                continue
            moments = [order["lastPickupAt"] + 1] if self.parts.repost and self.posted_at.get(gig, 0) <= order["lastPickupAt"] else []
            if self.parts.bands and not self.parts.windows and gig in self.aimed:
                moments.append(self.aimed[gig] + 1)
            for at in moments:
                if at > self.now and (best is None or at < best):
                    best = at
        return best


def wake_on_time(world, desk: ApiDesk) -> None:
    """A practice world stands still until `advance`, which stops at events only. The desk also acts at minutes of
    its own (a last pickup passes), so the lab's advance stops there too. The final's clock moves by itself and the
    runner ticks every second: nothing to do there."""
    plain = getattr(world, "plain_advance", None) or world.advance  # a second desk on the same world (a restart) replaces the first
    world.plain_advance = plain

    def advance(to=None, by=None, until=None, max=None, actions=()):
        at = desk.next_timer()
        if at is not None:
            if until is not None:
                max = at if max is None else min(max, at)
            elif to is not None:
                to = min(to, at)
        return plain(to=to, by=by, until=until, max=max, actions=actions)

    world.advance = advance


def build(client, world, level: int, now: int, params: Params, parts: Parts) -> ApiDesk:
    desk = ApiDesk(world, level, now, ApiPolicy(params, parts), Geo(client.map()))
    desk.meet(world.roster())
    wake_on_time(world, desk)
    return desk
