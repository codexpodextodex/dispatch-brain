"""Design A on version 7: short drives (up to 3 h) wait up to 4 h for a partner, but only while the guard finds
the week going well; in a week that turns hard every car is posted at once, as version 7 (see alt/pairhold.py)."""
from alt.pairhold import Hold, make as hold_make


def make(client, world, level, now, params):
    return hold_make(client, world, level, now, params, Hold(hours=4, max_drive=180, calm=1))
