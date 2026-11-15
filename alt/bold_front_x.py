"""Win far more cars on Monday and Tuesday and far fewer late in the week: cost x 0.70, 0.80, 1.05, 1.25, 1.30 (see alt/bold.py)."""
from alt.bold import Bold, make as bold_make


def make(client, world, level, now, params):
    return bold_make(client, world, level, now, params, Bold(by_day=(0.70, 0.80, 1.05, 1.25, 1.30)))
