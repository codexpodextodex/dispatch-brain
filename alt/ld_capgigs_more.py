"""leaders/capgigs: two more forms of the day cap, to tell the two halves of 'hours' apart (see alt/ld_capgigs_core.py).
  own     version 8's count of CARS for the day's load, the new car charged by its own driver-hours / REF
  thin    version 8's count of cars, the new car charged by how exposed it is: `ref` for a drive of 4 hours or more or
          fewer than 150 drivers living within 60 km of its ends, `cap_long` otherwise (offline such cars are 4 to 5
          times as sensitive to the day's load: leaders/capgigs/out/within_car.txt)
  both    two limits, the larger charge counts: version 8's cap on cars (unchanged) and the cap on driver-hours with the
          car's own hours (alt/ld_capgigs_hours.py). Played alone, the hours cap made the long-car days punctual (fresh-12
          Friday: 38 -> 28 long cars, 24 -> 8 late) and let 12 to 18 more short cars onto three Fridays, which then ran
          late (lab-5: 3 -> 16 late). A day is full when its cars OR its driver-hours are.
  bothwk  the same for last pickups up to Friday only; cars due after Friday keep version 8's cap alone. In the played
          weeks a long car more on a Friday went with 1.3 more late cars that day, on the Monday after with 0.17
          (leaders/capgigs/out/daydiff_both_screens.txt), and the long Monday cars are the best cars we carry.
  gigs    a two-car gig, open or booked, counts as ONE car while both its cars are undelivered: it needs one driver. The
          pair is driven on its second car's day, so the first car is the one that stops counting. Meant for the desk
          that holds cars for a partner (`pair_hold=4`: 70 driven pairs a week, 15% of the cars due at a quote); the
          cap 0.0929 gigs a listed driver charges what version 8's cap charges there (leaders/capgigs/replay_gigs.py).
"""
from __future__ import annotations

from alt.ld_capgigs_core import CapPolicy, build as core_build
from dispatch.desk import Desk
from dispatch.geo import DAY, HOUR


class MorePolicy(CapPolicy):
    def cap_term(self, desk: Desk, leg: dict, day: int) -> float:
        p = self.p
        if self.mode == "gigs":
            load = max(0.0, self.load(desk, day, lambda _: 1.0) - self.pairs_due(desk, day))
            return (load / (self.cap * (p.cap_monday if day >= 5 else 1.0) * desk.drivers)) ** p.cap_power
        if self.mode in ("both", "bothwk"):
            monday = p.cap_monday if day >= 5 else 1.0
            cars = (self.load(desk, day, lambda _: 1.0) / (p.day_cap * monday * desk.drivers)) ** p.cap_power
            if self.mode == "bothwk" and day >= 5:
                return cars
            hours = desk.driver_hours(leg) / self.ref * (self.load(desk, day, desk.driver_hours) / (self.cap * monday * desk.drivers)) ** p.cap_power
            return max(cars, hours)
        if self.mode not in ("own", "thin"):
            return super().cap_term(desk, leg, day)
        load = self.load(desk, day, lambda _: 1.0)
        if self.mode == "own":
            own = desk.driver_hours(leg) / self.ref
        else:
            zone = self.zone(desk, leg["pickup"]["placeId"]) | self.zone(desk, leg["delivery"]["placeId"])
            own = self.ref if desk.geo.drive(leg) >= 4 * HOUR or sum(self.homes.get(place, 0) for place in zone) < 150 else self.cap_long
        return own * (load / (self.cap * (p.cap_monday if day >= 5 else 1.0) * desk.drivers)) ** p.cap_power


    def pairs_due(self, desk: Desk, day: int) -> int:
        """The two-car gigs, open or booked, whose cars are both undelivered and whose FIRST car is due on `day`."""
        count = 0
        for gig_id in desk.pairs:
            post = desk.posts.get(gig_id)
            ids = list(dict.fromkeys(stop["orderId"] for stop in post["stops"])) if post else []
            orders = [desk.orders.get(order_id) for order_id in ids]
            if len(orders) == 2 and all(o is not None and None in o["deliveredAt"] for o in orders):
                count += desk.last_pickup.get(ids[0], orders[0]["lastPickupAt"]) // DAY == day
        return count


def build(client, world, level, now, params, **how):
    import alt.ld_capgigs_core as core
    real = core.CapPolicy
    core.CapPolicy = MorePolicy
    try:
        return core_build(client, world, level, now, params, **how)
    finally:
        core.CapPolicy = real
