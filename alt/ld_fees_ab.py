"""Version 7 with two changes to the fees (leaders/fees/REPORT.md): a car that goes where at least 30 drivers live,
with a drive under 5 hours and a typical fee of 22 euros or more, opens at 0.75 typical fees instead of 0.85; and a car won 5 to 7 hours before its last
pickup opens at its usual opening fee and reaches the top fee within 40 to 80 minutes, instead of opening at the top fee."""
from alt.ld_fees_core import Rule, build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, Rule(easy_open=0.75, easy_min_fee=2200, short_ramp=1))
