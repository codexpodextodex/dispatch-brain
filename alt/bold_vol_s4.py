"""Volume with two brakes of our own: play with the main session's volume settings (cost=0.95 day_cap=0.12
easy_find_hours=6). Short drives wait up to 4 h for a round-trip partner, so the extra cars ride in pairs where
they can; and a day takes no new car once 2.5 posted cars per 100 drivers due that day have no driver
(see alt/bold.py, alt/pairhold.py)."""
from alt.bold import Bold, make as bold_make
from alt.pairhold import Hold


def make(client, world, level, now, params):
    return bold_make(client, world, level, now, params, Bold(stop=2.5), hold=Hold(hours=4, max_drive=180))
