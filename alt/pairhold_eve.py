"""Design A, posted by time to the last pickup: a car due tomorrow waits up to 4 hours for a partner, a car due
later waits to 17:00 on the working day before its last pickup (see alt/pairhold.py)."""
from alt.pairhold import Hold, make as hold_make


def make(client, world, level, now, params):
    return hold_make(client, world, level, now, params, Hold(hours=4, evening=17))
