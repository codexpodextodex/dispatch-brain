"""Version 7, except that on Friday a car that can also go on the last Monday is not offered for the same day
(leaders/ swarm, line "capacity").

Why (python -X utf8 leaders/capacity/steering.py, 60 weeks): Friday's requests with a same-day option and a next-day
option give us 9.8 same-day cars a week, the worst cars we carry: 17.9 euros of margin, 1.23 typical fees, 6.4% late
(7.2% in ordinary weeks), collected on the fullest day of the week. The same kind of car on the Monday option pays
0.77 typical fees, earns 39 euros and was never late in 54 cars. Friday requests on which we quote the next-day
option alone are won 35% of the time at the usual price. So: fewer of these cars, each worth twice as much, and ten
cars off Friday. Offline estimate +50 to +100 a week and 0.6 late cars fewer; not a volume play."""
from dispatch.desk import Desk
from dispatch.geo import DAY, Geo
from dispatch.policy import Params, Policy


class FridayGoesMonday(Policy):
    def quote(self, desk, request):
        prices = super().quote(desk, request)
        markups = self.quoted.get(request["id"])
        if request["arrivedAt"] // DAY % 7 != 4 or not markups or "same_day" not in markups or len(markups) < 2:
            return prices
        today = next(o for o in request["options"] if o["kind"] == "same_day")
        if today["deadline"] // DAY != request["arrivedAt"] // DAY:
            return prices
        if not any(o["kind"] in markups and o["deadline"] // DAY > today["deadline"] // DAY for o in request["options"]):
            return prices
        del markups["same_day"]  # the book then learns from the next-day quote, as for any request quoted on one option
        prices.pop("same_day", None)
        desk.stats["friday_to_monday"] += 1
        return prices


def make(client, world, level: int, now: int, params: Params):
    desk = Desk(world, level, now, FridayGoesMonday(params), Geo(client.map()))
    desk.meet(world.roster())
    return desk
