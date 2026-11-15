"""leaders/routes: version 8 with one change to the day cap (`Policy.cost`, `day_cap`): a two-car gig counts as one
car while both its cars are undelivered. The cap stands for the drivers a day can find, and a pair needs one.
Offline (leaders/routes/q5_cap.py, version 7's 60 weeks decided again): about 19 more cars a week, first order.
`build` also serves ld_routes_hold4cap: the same on the pair-holding desk."""
from __future__ import annotations

from alt.ld_routes_hold import Hold, HoldDesk8
from dispatch.geo import DAY, Geo
from dispatch.policy import Params, Policy


class PairCapDesk(HoldDesk8):
    def due(self, day: int, thin_only: bool = False) -> float:
        return max(0.0, super().due(day, thin_only) - (0 if thin_only else self.pairs_due(day)))

    def pairs_due(self, day: int) -> int:
        """The two-car gigs, open or booked, whose cars are both undelivered and whose second car is due on `day`."""
        count = 0
        for gig_id in self.pairs:
            post = self.posts.get(gig_id)
            ids = list(dict.fromkeys(stop["orderId"] for stop in post["stops"])) if post else []
            orders = [self.orders.get(order_id) for order_id in ids]
            if len(orders) == 2 and all(o is not None and None in o["deliveredAt"] for o in orders):
                count += self.last_pickup.get(ids[1], orders[1]["lastPickupAt"]) // DAY == day
        return count


def build(client, world, level: int, now: int, params: Params, hold: Hold):
    desk = PairCapDesk(world, level, now, Policy(params), Geo(client.map()), hold=hold)
    desk.meet(world.roster())
    return desk


def make(client, world, level, now, params):
    return build(client, world, level, now, params, Hold(hours=0))  # no holding: version 8's posting to the letter
