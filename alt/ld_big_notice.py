"""leaders/bigcars, variant "notice": a plain car with a drive of 3 to 7 hours is not charged for its length (`cost_drive`)
on an option that leaves 48 hours and more to a weekday last pickup. Last pickups after Friday and everything under
48 hours stay as version 10 prices them. See alt/ld_big_core.py."""
from alt.ld_big_core import Rule, build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, Rule(week_rate=0.0, after_rate=1.0))
