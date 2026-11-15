"""A desk for volume: play with cost=0.85; cars held up to 4 h for a partner; a day takes no new car once 2.5 posted cars per 100 drivers due that day have no driver (see alt/bold.py)."""
from alt.bold import Bold, make as bold_make
from alt.pairhold import Hold


def make(client, world, level, now, params):
    return bold_make(client, world, level, now, params, Bold(stop=2.5), hold=Hold(hours=4))
