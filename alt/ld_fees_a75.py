"""Version 7 with one change: a car that goes where at least 30 drivers live (within 30 km of the delivery), with a
drive under 5 hours and a typical fee of 22 euros or more, opens at 0.75 typical fees instead of 0.85 (leaders/fees/REPORT.md)."""
from alt.ld_fees_core import Rule, build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, Rule(easy_open=0.75, easy_min_fee=2200))
