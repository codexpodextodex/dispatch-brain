"""Version 7 with the guard as a slope instead of a switch (leaders/ swarm, line "percar": leaders/percar/REPORT.md).

Why. Version 7 turns careful when late cars plus 0.75 x deadline warnings of the last day pass 6% of the cars
decided: from that minute every car at risk costs 0.5 typical fees more. On the 12 screen weeks a variant whose
quotes differ from version 7's by 1% ended 2,681 euros above it in one week and 3,304 below in another, each time
because one of the two desks crossed the 6% line on one day and the other did not: about 4 cars and 300 euros for
every hour the guard is on (leaders/percar/guard_state.py). A switch that one warning can throw makes a week a coin
toss of that size, and the final is one week.

The rule. The same brake, the same cars, the same 0.5 typical fees at the most, but rising evenly with the share:
nothing under `low`, all of it from `high` (0.04 and 0.08 around version 7's 0.06). The fee rule of the guard (the
late fee earlier in a careful week) keeps its 6% switch. With low = high = the guard this is version 7 to the cent."""
from dispatch.desk import Desk
from dispatch.geo import DAY, Geo
from dispatch.policy import Params, Policy


class RampPolicy(Policy):
    low, high = 0.04, 0.08
    forced = None  # while a cost is being computed with the guard forced on or off

    def careful(self, desk) -> bool:
        return super().careful(desk) if self.forced is None else self.forced

    def share(self, desk) -> float:
        """The late and nearly late share that the guard watches; 0 until 40 cars are decided."""
        warned = sum(1 for at in desk.warnings if at > desk.now - DAY)
        done = sum(self.arrivals) + warned
        return (self.arrivals[1] + 0.75 * warned) / done if done >= 40 else 0.0

    def cost(self, desk, request, option, last):
        if not self.p.guard or self.forced is not None:
            return super().cost(desk, request, option, last)
        share = self.share(desk)
        weight = 1.0 if share > self.high else 0.0 if share <= self.low else (share - self.low) / (self.high - self.low)
        try:
            self.forced = False
            off = super().cost(desk, request, option, last)
            if weight == 0.0:
                return off
            self.forced = True
            on = super().cost(desk, request, option, last)
        finally:
            self.forced = None
        return off + weight * (on - off)


def make(client, world, level: int, now: int, params: Params, low: float = 0.04, high: float = 0.08):
    policy = RampPolicy(params)
    policy.low, policy.high = low, high
    desk = Desk(world, level, now, policy, Geo(client.map()))
    desk.meet(world.roster())
    return desk
