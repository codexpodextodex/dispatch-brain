"""Design A with a wait of up to 4 hours for a partner (see alt/pairhold.py)."""
from alt.pairhold import Hold, make as hold_make


def make(client, world, level, now, params):
    return hold_make(client, world, level, now, params, Hold(hours=4))
