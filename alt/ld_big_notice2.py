"""leaders/bigcars, variant "notice2": variant "notice" (no charge for length with 48 hours and more to a weekday last
pickup, drives of 3 to 7 hours) + half the charge when that last pickup falls after Friday (measured 0.95 to 1.07
typical fees against 1.12 to 1.28 charged) + under 48 hours a drive of 6 to 7 hours is charged as 6 hours (measured
1.10 to 1.25 against 1.28). See alt/ld_big_core.py."""
from alt.ld_big_core import Rule, build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, Rule(week_rate=0.0, after_rate=0.5, flat_from=6.0))
