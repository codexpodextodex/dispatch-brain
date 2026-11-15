"""API line: see alt/ld_api_core.py. This desk: as ld_api_last (a late car is posted again in the minute after its last
pickup, at a late car's fees), with the guard's count of warnings kept as version 7 has it. ld_api_last without this
also takes two thirds of the brake away, by accident (leaders/api/guard_count.py)."""
from alt.ld_api_core import Parts, build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, Parts(keep_count=True))
