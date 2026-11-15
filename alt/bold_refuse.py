"""Refuse long drives (over 3 h) to towns with few drivers, and play with cost=0.85 to win more of the rest (see alt/bold.py)."""
from alt.bold import Bold, make as bold_make


def make(client, world, level, now, params):
    return bold_make(client, world, level, now, params, Bold(refuse_drive=180))
