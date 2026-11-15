"""The week's front-loading (cost x 0.80, 0.85, 1.00, 1.15, 1.15) on the desk that holds cars up to 4 h for a partner (see alt/bold.py, alt/pairhold.py)."""
from alt.bold import Bold, make as bold_make
from alt.pairhold import Hold


def make(client, world, level, now, params):
    return bold_make(client, world, level, now, params, Bold(by_day=(0.80, 0.85, 1.00, 1.15, 1.15)), hold=Hold(hours=4))
