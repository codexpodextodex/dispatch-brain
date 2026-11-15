"""leaders/kinds, the live notice rule: how much notice a same-day car needs depends on how today is going, not on the
weekday. With `Live()` (every rule off) this desk sends exactly version 8's actions (leaders/kinds/check.py).

Version 8 quotes an option that must be collected on the day of the request only for an "easy" car (4 hours of notice);
every other plain car needs 14 hours, so it is quoted on a later option or not at all: 156 requests a week, won 30%
where the easy cars are won 65%. Carried at short notice, such cars came late 0 to 3% on Monday and 10 to 22% from
Wednesday. It is not the weekday (leaders/kinds/out/live.txt, live2.txt: 9,714 short-notice cars, a model fitted on two
seed families and scored on the third): the weekday adds 3.9 points to what the car itself explains, one live number adds
11.0 and leaves the weekday nothing to add. The number: OUR CARS DUE TODAY THAT STILL HAVE NO DRIVER. On Monday morning
it is zero (93% of same-day requests arrive with none waiting); from Wednesday it is zero or one 42 to 48% of the time.

The desk counts the cars that are due today, have no driver, and whose gig has been in the app for `wait` minutes
("waiting"): a car just posted says nothing yet. Then, for a plain car's option that must be collected today:

`find`, `clear`:   while fewer than `clear` cars are waiting, ANY plain car is quoted with `find` hours of notice.
                   Cars that are not easy, with 6 hours and more: fewer than 2 waiting 3.1% late (488 cars, 25 euros a car;
                   Monday 2.8%, Tuesday 3.3%, Wednesday to Friday 3.4%); 2 waiting 13.7%; 3 to 5 9.5%; 6 and more 22.8%.
`find2`, `clear2`: a second step: with `find2` hours of notice while fewer than `clear2` are waiting. With 8 hours and more
                   and 2 to 5 waiting: 4.6% late (65 cars); with 6 and more waiting 18.9%.
`easy_stop`, `easy_find`: once `easy_stop` cars are waiting, an easy car needs `easy_find` hours instead of 4. Easy cars with
                   4 to 6 hours of notice from Wednesday on: under 3 waiting 2.8% late (1,004 cars), 3 to 5 9.4% (307), 6 and more 25.7% (265 cars,
                   10 euros a car).

Later options are quoted as version 8 quotes them. The count needs no book: it reads the desk's orders, bookings and
posts, which a restart rebuilds from the world. (While a restarted desk reads the week's history again it has no posts
yet, so it may take a past same-day option for quoted that was not; that touches only what the price book learns from
those few answers.)"""
from __future__ import annotations

from dataclasses import dataclass, replace

from dispatch import desk as desk_module
from dispatch.desk import Desk
from dispatch.geo import DAY, HOUR, PLATES_MINUTES, Geo, last_pickup
from dispatch.notes import apply
from dispatch.policy import Params, Policy


@dataclass(frozen=True)
class Live:
    find: float = 0.0  # hours of notice with which any plain car's same-day option is quoted while the day is clear; 0 is off
    clear: int = 2  # ... clear: fewer than this many of today's cars are waiting for a driver
    find2: float = 0.0  # ... and with this many hours of notice while fewer than `clear2` are waiting; 0 is off
    clear2: int = 6
    easy_stop: int = 0  # from this many waiting cars an easy car's same-day option needs `easy_find` hours; 0 is off
    easy_find: float = 6.0
    wait: int = 60  # a car is waiting when it has no driver and its gig was posted at least this many minutes ago


class LivePolicy(Policy):
    def __init__(self, params: Params, live: Live):
        super().__init__(params)
        self.k = live

    def waiting(self, desk: "Desk", day: int) -> int:
        """Our cars that must be collected on `day`, have no driver, and have been in the app for `wait` minutes."""
        count = 0
        for order_id, order in desk.orders.items():
            if None not in order["deliveredAt"] or desk.last_pickup.get(order_id, order["lastPickupAt"]) // DAY != day:
                continue
            gigs = desk.gigs_of(order_id)
            if any(gig in desk.booked for gig in gigs):
                continue
            posted = max((desk.posts[gig]["schedule"][0]["at"] for gig in gigs if gig in desk.posts), default=desk.now)
            count += desk.now - posted >= self.k.wait
        return count

    def lasts(self, desk: "Desk", request: dict) -> dict[str, int]:
        """The last minute to collect the car on each option, as `Policy.quote` counts it (the note read)."""
        leg, facts, ours = request["legs"][0], desk.facts(request), self.p.notes == "ours"
        noted = apply(leg, facts) if ours else leg
        minutes = desk.geo.drive(leg) + (PLATES_MINUTES if ours and facts.plates else 0)
        out = {}
        for option in request["options"]:
            deadline = min(option["deadline"], facts.deadline) if ours and facts.deadline else option["deadline"]
            last = last_pickup(noted, deadline, minutes)
            if last is not None:
                out[option["kind"]] = last
        return out

    def quote(self, desk: "Desk", request: dict) -> dict[str, int]:
        k, base = self.k, self.p
        if not (k.find or k.find2 or k.easy_stop) or not self.plain_leg(request) or not self.wanted(request):
            return super().quote(desk, request)
        today, lasts = request["arrivedAt"] // DAY, self.lasts(desk, request)
        same_day = {kind for kind, last in lasts.items() if last // DAY == today}
        if not same_day:
            return super().quote(desk, request)
        usual = self.find_hours(desk, request)  # version 8: 14 hours, or 4 for an easy car
        need, waiting = usual, self.waiting(desk, today)
        if k.find and waiting < k.clear:
            need = min(need, k.find)
        elif k.find2 and waiting < k.clear2:
            need = min(need, k.find2)
        if k.easy_stop and usual < base.min_find_hours and waiting >= k.easy_stop:
            need = max(need, k.easy_find)
        if need == usual:
            return super().quote(desk, request)
        desk.stats["live_looser" if need < usual else "live_tighter"] += 1
        notice = {kind: (last - request["respondBy"]) / HOUR for kind, last in lasts.items()}
        kept = [o for o in request["options"] if o["kind"] in notice and notice[o["kind"]] >= (need if o["kind"] in same_day else usual)]
        if not kept:  # nothing left to sell: version 8's own way of saying no
            self.p = replace(base, min_find_hours=10.0 ** 6, easy_find_hours=0.0)
            asked = request
        else:  # version 8's own quote for the options we keep: its notice test is set so that it lets exactly these through
            least = min(need, usual)
            self.p = replace(base, min_find_hours=min(base.min_find_hours, least), easy_find_hours=min(base.easy_find_hours, least) if base.easy_find_hours else 0.0)
            asked = {**request, "options": kept}
        try:
            return super().quote(desk, asked)
        finally:
            self.p = base


def build(client, world, level: int, now: int, params: Params, live: Live):
    if params.windows and "driver_late" not in desk_module.WAKE_ON:
        desk_module.WAKE_ON.append("driver_late")  # as dispatch.play.new_desk does for the usual desk
    desk = Desk(world, level, now, LivePolicy(params, live), Geo(client.map()))
    desk.meet(world.roster())
    return desk


def make(client, world, level: int, now: int, params: Params):
    """The rule as sized: any plain car with 6 hours of notice while fewer than 2 of today's cars wait for a driver; an
    easy car needs 6 hours instead of 4 once 6 wait."""
    return build(client, world, level, now, params, Live(find=6.0, clear=2, easy_stop=6, easy_find=6.0))
