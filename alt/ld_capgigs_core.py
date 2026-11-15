"""leaders/capgigs: version 8 with ONE change, what the day cap counts.

Version 8 (`Policy.cost`): a car whose last pickup falls on day d costs x (1 + (our undelivered cars due on d /
(day_cap x listed drivers)) ^ cap_power). Every car counts 1, whatever it asks of a driver. Here the load of a day is
counted in another unit; everything else (the cost before the cap, the price book, fees, pairs) is version 8's code.

  cars    version 8's count, through this module's code path: must send version 8's quotes to the cent (the check)
  hours   driver-hours (`Desk.driver_hours`: the trip to the car, the drive, the trip home). The day's load is the
          driver-hours of our cars due that day per listed driver, and the new car is charged by its own hours:
          x (1 + hours of this car / REF x (hours due / (CAP x drivers)) ^ power)
  flat    the same load in hours, every new car charged alike (no own weight)
  long    two pools. Offline (leaders/capgigs/out/within_check.txt): a short car is late a little more often for every
          car added to its day, whatever that car's length; a long car (4 h of road or more) is late much more often
          for every LONG car added and not for short ones. So: every car pays for the cars due that day at a looser
          cap, and a long car also pays for the long cars due that day.
  near    cars due that day with an end within 60 km of one of this car's ends, per driver living there

The caps are set so that over version 8's 60 saved weeks each form charges the same mean multiplier as version 8's
cap (leaders/capgigs/replay.py): the test is the shape of the count, not a looser cap.
"""
from __future__ import annotations

from dataclasses import replace

from dispatch.desk import Desk
from dispatch.geo import DAY, HOUR, Geo, neighbours
from dispatch.policy import Params, Policy


class CapPolicy(Policy):
    def __init__(self, params: Params, mode: str = "cars", cap: float = 0.0, ref: float = 1.0, cap_long: float = 0.0, long_hours: float = 4.0, km: int = 60):
        super().__init__(params)
        self.mode, self.cap, self.ref, self.cap_long, self.long_hours, self.km = mode, cap, ref, cap_long, long_hours, km
        self.uncapped = replace(params, day_cap=0.0)
        self.zones: dict[str, frozenset] = {}

    def cost(self, desk: Desk, request: dict, option: dict, last: int) -> float:
        p, day = self.p, last // DAY
        if not p.day_cap or (p.cap_week_only and day >= 5):
            return super().cost(desk, request, option, last)
        self.p = self.uncapped  # version 8's cost without its cap ...
        try:
            cost = super().cost(desk, request, option, last)
        finally:
            self.p = p
        return cost * (1 + self.cap_term(desk, request["legs"][0], day))  # ... and the cap, counted this module's way

    def cap_term(self, desk: Desk, leg: dict, day: int) -> float:
        p = self.p
        monday = p.cap_monday if day >= 5 else 1.0
        if self.mode == "cars":
            due = desk.due(day, thin_only=bool(p.cap_thin)) + sum(hope for hoped_day, hope in self.hoped.values() if hoped_day == day)
            cap = (p.cap_easy if p.cap_easy and self.relaxed(desk) else p.day_cap) * monday
            return self.cap_weight(desk, leg) * (due / (cap * desk.drivers)) ** p.cap_power
        if self.mode in ("hours", "flat"):
            load = self.load(desk, day, desk.driver_hours)
            own = desk.driver_hours(leg) / self.ref if self.mode == "hours" else 1.0
            return own * (load / (self.cap * monday * desk.drivers)) ** p.cap_power
        if self.mode == "long":
            term = (self.load(desk, day, lambda _: 1.0) / (self.cap * monday * desk.drivers)) ** p.cap_power
            if desk.geo.drive(leg) >= self.long_hours * HOUR:
                term += (self.load(desk, day, lambda l: float(desk.geo.drive(l) >= self.long_hours * HOUR)) / (self.cap_long * monday * desk.drivers)) ** p.cap_power
            return term
        if self.mode == "near":
            zone = self.zone(desk, leg["pickup"]["placeId"]) | self.zone(desk, leg["delivery"]["placeId"])
            load = self.load(desk, day, lambda l: float(l["pickup"]["placeId"] in zone or l["delivery"]["placeId"] in zone))
            return (load / (self.cap * monday * max(5, sum(self.homes.get(place, 0) for place in zone)))) ** p.cap_power
        raise ValueError(self.mode)

    def load(self, desk: Desk, day: int, weight) -> float:
        """Our undelivered cars due on a day, and the quotes still unanswered by their chance, each by `weight` of its car."""
        total = sum(weight(order["legs"][0]) for order_id, order in desk.orders.items()
                    if None in order["deliveredAt"] and desk.last_pickup.get(order_id, order["lastPickupAt"]) // DAY == day)
        for request_id, (hoped_day, hope) in self.hoped.items():
            if hoped_day == day and request_id in desk.requests:
                total += hope * weight(desk.requests[request_id]["legs"][0])
        return total

    def zone(self, desk: Desk, place: str) -> frozenset:
        if place not in self.zones:
            self.zones[place] = frozenset(neighbours(desk.geo, place, self.km))
        return self.zones[place]


def build(client, world, level: int, now: int, params: Params, **how):
    from dispatch import desk as desk_module
    if params.windows and "driver_late" not in desk_module.WAKE_ON:  # as `dispatch.play.new_desk` does for version 8 itself, which
        desk_module.WAKE_ON.append("driver_late")  # returns before this line for a plug-in: the practice clock must stop at the notice
    policy = CapPolicy(params, **how)
    desk = Desk(world, level, now, policy, Geo(client.map()))
    roster = world.roster()
    desk.meet(roster)
    policy.homes = {}
    for driver in roster:
        policy.homes[driver["homePlaceId"]] = policy.homes.get(driver["homePlaceId"], 0) + 1
    return desk


def make(client, world, level, now, params):
    return build(client, world, level, now, params, mode="cars")  # version 8 through this module: the check
