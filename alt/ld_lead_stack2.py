"""Version 7 with the swarm's measured changes together (leaders/ swarm, lead). Each part alone, exact mode against
version 7 (leaders/STATUS.md):
  - fees (leaders/fees, alt/ld_fees_a3b): a dealer-to-dealer car that goes where at least 30 drivers live, drive under
    3 hours, typical fee of 22 euros or more, opens at 0.75 typical fees instead of 0.85; a car won 5 to 7 hours before
    its last pickup opens at its usual fee and reaches the top fee within 40 to 80 minutes (+377 ± 54 and +84 ± 20 a
    week on those cars, 12 of 12 and 10 of 12 weeks);
  - punctuality (leaders/ontime, alt/ld_ontime_tell4): the pairing fault fixed (a pair that a driver gave back is not
    taken apart by a new pair, which left a car without any gig: 36 cars in 60 weeks), a pickup window that ends at the
    last pickup so that a driver who will come late says so, a late driver released when another can still come, and
    the cheap late fees from the minute the last pickup has passed (+337 ± 230 on 16 weeks, on time +0.5 points);
  - the day cap does not count cars whose last pickup falls after Friday (alt/ld_lead_monoff, +253 ± 85 on 12 weeks).
Play it with `guard=0.08` for the fourth (+81 ± 36 on 60 weeks)."""
from dataclasses import replace

from alt.ld_fees_core import FeePolicy, Rule
from alt.ld_ontime_w4 import OnTimeDesk, OnTimePolicy, Parts
from dispatch import desk as desk_module
from dispatch.geo import DAY, Geo
from dispatch.policy import Params, Policy

RULE = Rule(easy_open=0.75, easy_min_fee=2200, easy_hours=3.0, short_ramp=1)
PARTS = Parts(buffer=0, buffer_share=0.0, pair_buffer=0, fix=True)


class StackPolicy(FeePolicy, OnTimePolicy):
    def __init__(self, params: Params, rule: Rule, parts: Parts, monday_cap: bool = False):
        Policy.__init__(self, params)
        self.rule, self.posting, self.parts, self.monday_cap = rule, None, parts, monday_cap

    def cost(self, desk, request, option, last):
        if not self.monday_cap and last // DAY >= 5 and self.p.day_cap:
            keep = self.p
            self.p = replace(keep, day_cap=0.0)
            try:
                return super().cost(desk, request, option, last)
            finally:
                self.p = keep
        return super().cost(desk, request, option, last)


def build(client, world, level: int, now: int, params: Params, rule: Rule = RULE, parts: Parts = PARTS, monday_cap: bool = False):
    if parts.act and "driver_late" not in desk_module.WAKE_ON:
        desk_module.WAKE_ON.append("driver_late")  # the practice clock must stop at the notice, as the live stream does
    desk = OnTimeDesk(world, level, now, StackPolicy(params, rule, parts, monday_cap), Geo(client.map()))
    desk.meet(world.roster())
    return desk


def make(client, world, level: int, now: int, params: Params):
    return build(client, world, level, now, params)
