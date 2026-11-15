"""leaders/bulk: a long drive costs more for each car we already have on its lane for the same day.

Measured on version 7's 60 weeks (leaders/bulk/s3d_lane.py): of our cars with a drive of 200 minutes or more
on one lane (yard and town) due on one day, the first is late 4 to 6% of the time, the third and fourth 6 to
11%, the fifth and later 17 to 38%, and the time to book goes from under an hour to 40. The drivers for whom
that trip is cheap (they live at its far end) are few, and a batch or the bulk order sends several such cars at
once. These cars are a third of the late cars of the hardest weeks (10 of 40 in fresh-12, 8 of 22 in fresh-2).

So: the third long car on a lane and day costs STEP typical fees more, the fourth twice that, and so on. Cars
count when we hold them and are still to be collected; open quotes count with their chance to win, so a bulk
order cannot fill a lane in the 15 minutes before its first answer. The rest is version 7."""
from __future__ import annotations

from dispatch.desk import Desk
from dispatch.geo import DAY, Geo
from dispatch.policy import Params, Policy

LONG = 200  # road minutes: from here on the lane's own drivers run out
FREE = 2  # cars on one lane and day that cost nothing extra
STEP = 0.25  # typical fees more for each car beyond them


class LanePolicy(Policy):
    step = STEP

    def cost(self, desk: Desk, request: dict, option: dict, last: int) -> float:
        cost = super().cost(desk, request, option, last)
        leg = request["legs"][0]
        if len(request["legs"]) != 1 or desk.geo.drive(leg) < LONG:
            return cost
        ahead = self.on_lane(desk, request, last // DAY)
        if ahead <= FREE - 1:
            return cost
        typical = self.steady(desk, request, leg, request["referenceFeeCents"], self.p.road_cost_blend)
        return cost + self.step * (ahead - (FREE - 1)) * typical / option["listPriceCents"]

    def on_lane(self, desk: Desk, request: dict, day: int) -> float:
        """Our cars on this request's lane whose last pickup falls on `day`: the ones we hold and have not
        collected, and the open quotes by their chance to win."""
        leg = request["legs"][0]
        lane = (leg["pickup"]["placeId"], leg["delivery"]["placeId"])
        count = 0.0
        for order in desk.orders.values():
            if len(order["legs"]) != 1 or None not in order["deliveredAt"]:
                continue
            other = order["legs"][0]
            if (other["pickup"]["placeId"], other["delivery"]["placeId"]) == lane and desk.last_pickup.get(order["id"], order["lastPickupAt"]) // DAY == day:
                count += 1.0
        for request_id, (hoped_day, hope) in self.hoped.items():
            if hoped_day != day or request_id == request["id"] or request_id in desk.orders:
                continue
            other = desk.requests.get(request_id)
            if other and (other["legs"][0]["pickup"]["placeId"], other["legs"][0]["delivery"]["placeId"]) == lane:
                count += hope
        return count


def make(client, world, level: int, now: int, params: Params, step: float = STEP):
    policy = LanePolicy(params)
    policy.step = step
    desk = Desk(world, level, now, policy, Geo(client.map()))
    desk.meet(world.roster())
    return desk
