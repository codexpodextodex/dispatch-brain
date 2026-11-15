"""Version 7 with one change (leaders/fees/REPORT.md): a car that is ready today but not due today, won after 11:00 with a
drive of 2 hours or more, or after 15:00 with any drive, is posted with its pickup from tomorrow morning."""
from alt.ld_fees_core import Rule, build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, Rule(tomorrow=1))
