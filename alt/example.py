"""An alternative desk for the lab: the pattern to copy.

A module in alt/ is a whole different way of running the week. The lab plays it when the setting
`design=<module name>` is given, for example:

    python -m lab.sweep --both --seeds 20 --set design=example lab_step=12

`make` gets what the usual desk gets and returns a desk: any object with the methods and fields that
`dispatch.play.play_practice` and `lab.runs.run` use (the easiest is to subclass `dispatch.desk.Desk` and
`dispatch.policy.Policy` and change what you need; a desk built straight on `spread.starter.Desk` works too).
`params` is the usual `Params`: every other setting on the command line still arrives in it.

This example changes one thing, to show where: it never quotes a car whose drive is over six hours."""
from __future__ import annotations

from dispatch.desk import Desk
from dispatch.geo import HOUR, Geo
from dispatch.policy import Params, Policy


class ShortHaulPolicy(Policy):
    def wanted(self, request: dict) -> bool:
        return super().wanted(request) and self.desk.geo.drive(request["legs"][0]) <= 6 * HOUR


def make(client, world, level: int, now: int, params: Params):
    policy = ShortHaulPolicy(params)
    desk = Desk(world, level, now, policy, Geo(client.map()))
    policy.desk = desk  # `wanted` gets no desk of its own: give the policy a way to the map
    desk.meet(world.roster())
    return desk
