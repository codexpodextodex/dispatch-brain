"""The last Monday by how the week goes, cost x 0.75 while it goes well; see alt/ld_lead_moncr.py."""
from alt.ld_lead_moncr import make as base_make


def make(client, world, level, now, params):
    return base_make(client, world, level, now, params, scale=0.75)
