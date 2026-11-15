"""leaders/bulk: a new plain car waits up to 15 minutes for a partner before its gig is posted.

Requests of one batch (one dealer, one yard, one ready day) arrive within minutes and are decided within
minutes of each other; 77 of our 406 cars a week are won in a minute in which we win another car. Version 7
posts each car at once, and a car won in the same minute as its partner is not yet a gig the desk can pair
with, while a car won two minutes earlier may already have its driver. A two-car gig is driven for 0.73 of two
typical fees against about 1.0 alone (leaders/bulk/s3e_pairs.py), also when both cars come from the same yard.
Holding every car 15 minutes makes 12 more two-car gigs a week in the replay (leaders/bulk/s4c_sameminute.py).

No car waits past 17:30 of the day it was won (the lab wakes the desk on events; after the last requests
there may be none for hours), and none with under 16 hours to its last pickup. The rest is alt/pairhold.py."""
from alt.pairhold import Hold, make as hold_make


def make(client, world, level, now, params):
    return hold_make(client, world, level, now, params, Hold(hours=0.25, until=17.5))
