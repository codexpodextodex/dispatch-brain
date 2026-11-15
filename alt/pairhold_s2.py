"""Design A, holding only short drives: a car with at most 3 hours of driving waits up to 2 hours for a partner.
A long drive almost never finds one (3 paired cars a week of 64 held in the exact panel of pairhold_h4) and
loses its first-look drivers by waiting (see alt/pairhold.py)."""
from alt.pairhold import Hold, make as hold_make


def make(client, world, level, now, params):
    return hold_make(client, world, level, now, params, Hold(hours=2, max_drive=180))
