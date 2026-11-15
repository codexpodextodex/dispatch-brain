"""Measuring desk, not for the final: version 7 declining the requests that are late in 30% or more of the saved weeks of the same seed (alt/ld_percar_orc.py)."""
from alt.ld_percar_orc import make as base_make


def make(client, world, level, now, params):
    return base_make(client, world, level, now, params, key="late30")
