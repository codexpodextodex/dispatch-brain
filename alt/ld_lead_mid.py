"""leaders/lead: the day cap looser for cars whose last pickup falls on a calm weekday (Tuesday and Wednesday).

Version 9's 80 saved weeks by day of the last pickup (EXPERIMENTS.md section 66): Tuesday 61.5 cars at 0.70 of the cap,
late 2.5% (2.9% in the eight hardest weeks); Wednesday 72.6 at 0.83, late 3.3% (3.5%); Thursday 78.5 at 0.90, late 3.7%
(11.6%); Friday 95.0 at 1.09, late 4.1% (6.4%). At those loads the cap still adds 24% and 47% to the cost of a Tuesday
and a Wednesday car, on the two days that stay punctual even in the hard weeks. The cars due after Friday were the
same case, and a looser cap for them pays (`cap_monday`). Here: the cap for last pickups on `days` is `factor` times
the usual one; every other day, and everything else, is version 9's code (through alt/ld_capgigs_core.py, mode "cars").
"""
from __future__ import annotations

import alt.ld_capgigs_core as core
from dispatch.desk import Desk


def build(client, world, level, now, params, factor: float = 1.5, days: tuple = (1, 2)):
    class MidPolicy(core.CapPolicy):
        def cap_term(self, desk: Desk, leg: dict, day: int) -> float:
            term = super().cap_term(desk, leg, day)
            return term / factor ** self.p.cap_power if day in days else term  # the cap x factor on these days

    real = core.CapPolicy
    core.CapPolicy = MidPolicy
    try:
        return core.build(client, world, level, now, params, mode="cars")
    finally:
        core.CapPolicy = real


def make(client, world, level, now, params):
    return build(client, world, level, now, params)
