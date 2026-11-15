"""Version 7 with the swarm's two small measured changes together (leaders/ swarm, lead):
  - fees (leaders/fees/REPORT.md, alt/ld_fees_a3b): a dealer-to-dealer car that goes where at least 30 drivers live,
    drive under 3 hours, typical fee of 22 euros or more, opens at 0.75 typical fees instead of 0.85; a car won 5 to
    7 hours before its last pickup opens at its usual fee and reaches the top fee within 40 to 80 minutes;
  - the day cap does not count cars whose last pickup falls after Friday (alt/ld_lead_monoff: +253 ± 85 on the 12
    screen weeks): the last Monday has the weekend behind it and no new requests.
Play it with `guard=0.08` for the third (60 exact weeks: +81 ± 36)."""
from dataclasses import replace

from alt.ld_fees_core import FeeDesk, FeePolicy, Rule
from dispatch.geo import DAY, Geo
from dispatch.policy import Params


class StackPolicy(FeePolicy):
    def cost(self, desk, request, option, last):
        if last // DAY >= 5 and self.p.day_cap:
            keep = self.p
            self.p = replace(keep, day_cap=0.0)
            try:
                return super().cost(desk, request, option, last)
            finally:
                self.p = keep
        return super().cost(desk, request, option, last)


def make(client, world, level: int, now: int, params: Params, rule: Rule = Rule(easy_open=0.75, easy_min_fee=2200, easy_hours=3.0, short_ramp=1)):
    desk = FeeDesk(world, level, now, StackPolicy(params, rule), Geo(client.map()))
    desk.meet(world.roster())
    return desk
