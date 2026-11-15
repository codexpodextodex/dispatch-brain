"""leaders/kinds, variant "prem": version 8 + the road line for premium and private cars (rule 1) + premium cars with a
drive of 30 to 120 minutes, or any drive when the last pickup falls after Friday, on options that leave 24 hours to find
an experienced driver (rule 4). See alt/ld_kinds_core.py."""
from alt.ld_kinds_core import Kinds, build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, Kinds(steady_all=True, premium=True))
