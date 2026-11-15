"""leaders/routes: pair holding (alt/pairhold.py, design A) on version 8.

alt/pairhold.py posts a pair made from a held car itself, so that pair misses the one rule version 8 gives every
pair: the first pickup's window ends at the pair's last start (`windows`), so a booked driver who plans to come
later says so. This desk adds it and changes nothing else: with a hold of 0 hours it sends version 8's actions.
`pair_safe` (a pair that its driver gives back stays a pair) needs nothing here: the pair is on the desk's list.

Why play it again: the measured loss of pair holding in hard weeks (about one point on time, alt/NOTES.md) was
measured with version 7's fault that left a car of a returned pair without a gig, and that fault grows with the
number of pairs. And a car due on a later day loses little by waiting: such cars won at 17:00 to 19:00 are booked
as fast, as cheaply and as punctually as those won at 10:00 (leaders/routes/out/q4_noholding.txt)."""
from __future__ import annotations

from alt.pairhold import Hold, HoldDesk
from dispatch.geo import HOUR, Geo, needs_charging
from dispatch.policy import Params, Policy


class HoldDesk8(HoldDesk):
    def pair_held(self, order: dict) -> bool:
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
        if getattr(self.policy.p, "windows", 0) and start >= max(opens, self.now) + HOUR:  # as version 8 posts every pair
            stops[0]["window"] = {"from": opens, "to": start}
        typical = (self.typical(first) + self.typical(second)) * self.policy.p.pair_fee
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


def build(client, world, level: int, now: int, params: Params, hold: Hold):
    desk = HoldDesk8(world, level, now, Policy(params), Geo(client.map()), hold=hold)
    desk.meet(world.roster())
    return desk
