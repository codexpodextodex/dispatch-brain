"""Never quote the same-day option (see alt/bold.py)."""
from alt.bold import Bold, make as bold_make


def make(client, world, level, now, params):
    return bold_make(client, world, level, now, params, Bold(no_same_day=True))
