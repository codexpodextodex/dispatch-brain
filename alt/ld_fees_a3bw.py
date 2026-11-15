"""ld_fees_a3b plus (W): a car that is ready today but not due today, won after 11:00 with a drive of 2 hours or more, or
after 15:00 with any drive, is posted with its pickup from tomorrow morning (leaders/fees)."""
from alt.ld_fees_core import Rule, build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, Rule(easy_open=0.75, easy_min_fee=2200, easy_hours=3.0, short_ramp=1, tomorrow=1))
