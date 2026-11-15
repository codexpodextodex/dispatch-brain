"""Win many more cars on Monday and Tuesday, fewer from Wednesday: cost x 0.80, 0.85, 1.00, 1.15, 1.15 (see alt/bold.py)."""
from alt.bold import Bold, make as bold_make


def make(client, world, level, now, params):
    return bold_make(client, world, level, now, params, Bold(by_day=(0.80, 0.85, 1.00, 1.15, 1.15)))
