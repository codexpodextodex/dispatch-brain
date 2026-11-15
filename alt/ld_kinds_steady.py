"""leaders/kinds, variant "steady": version 8, and the road line in place of the typical fee's draw also for the private
cars it already carries (alt/ld_kinds_core.py, rule 1). No new kind of car."""
from alt.ld_kinds_core import Kinds, build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, Kinds(steady_all=True))
