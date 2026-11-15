"""Version 7 with two changes to the fees (leaders/fees): (A) a car that goes where at least 30 drivers live, with a drive
under 3 hours and a typical fee of 22 euros or more, opens at 0.75 typical fees instead of 0.85 (in the real weeks of
ld_fees_a75 and ld_fees_ab the drives of 3 to 5 hours gained little and came late three times as often); (B) a car won
5 to 7 hours before its last pickup opens at its usual opening fee and reaches the top fee within 40 to 80 minutes."""
from alt.ld_fees_core import Rule, build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, Rule(easy_open=0.75, easy_min_fee=2200, easy_hours=3.0, short_ramp=1))
