"""leaders/kinds, variant "early": version 8 + a looser notice rule early in the week (rule 5): on Monday every plain car
is quoted with 6 hours to find a driver, on Tuesday with 8, instead of 14 (easy cars 4, as now). From Wednesday on, version
8's rule. See alt/ld_kinds_core2.py."""
from alt.ld_kinds_core2 import Kinds, build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, Kinds(notice=((6, 4), (8, 4))))
