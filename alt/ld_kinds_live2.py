"""leaders/kinds, the live notice rule sized for the whole week (alt/ld_kinds_live.py, leaders/kinds/out/live_week.txt):
the same-day option of any plain car is quoted with 5 hours of notice while fewer than 2 of today's cars have waited an hour
for a driver, with 8 hours while fewer than 6 have, and otherwise as the base quotes it; an easy car needs 6 hours instead
of 4 once 3 are waiting. Offline: it opens 48.8 same-day requests a week that the base leaves closed (Monday 13.4, Tuesday
10.1, Wednesday 6.0, Thursday 7.3, Friday 12.1), about 18 more cars; the cars it keeps came late 3.1% (649 cars, 23.5 euros a
car), the cars it leaves closed 16.9%; the easy cars it closes came late 16.9% (572 cars, 12 euros a car)."""
from alt.ld_kinds_live import Live, build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, Live(find=5.0, clear=2, find2=8.0, clear2=6, easy_stop=3, easy_find=6.0))
