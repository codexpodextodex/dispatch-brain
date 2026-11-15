"""The wall for cars due after Friday (cost x 0.92), no cap for last pickups up to Tuesday, and the cap for last
pickups on Thursday and Friday tightened to 0.8 of version 7's in a careful week; see alt/ld_capacity_core.py."""
from alt.ld_capacity_core import make as base_make


def make(client, world, level, now, params):
    return base_make(client, world, level, now, params, scale=0.92, tue_cap=0.0, late_week=0.8)
