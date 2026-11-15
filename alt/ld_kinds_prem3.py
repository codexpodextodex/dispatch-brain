"""leaders/kinds, variant "prem3": ld_kinds_prem2 with the premium car handled and priced for what it costs: its gig
opens at 1.1 typical fees instead of 0.85 (few drivers may take it and each look is worth more: an experienced driver
takes it at 7 to 8% a look from 1.0 of the road line, at 3 to 4% under 0.9), and its cost is 0.2 typical fees above a
plain car's (that fee, and one late car in twenty). See alt/ld_kinds_core3.py."""
from alt.ld_kinds_core3 import Kinds, build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, Kinds(steady_all=True, premium=True, prem_pros=25, prem_calm=True, prem_open=1.1, prem_cost=0.2))
