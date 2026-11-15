"""leaders/bulk: as alt/ld_bulk_lane.py, with twice the step: the third long car on a lane and day costs half a
typical fee more, the fourth a whole one."""
from alt.ld_bulk_lane import make as lane_make


def make(client, world, level, now, params):
    return lane_make(client, world, level, now, params, step=0.5)
