"""API line: see alt/ld_api_core.py. This desk: Parts(bands=True) = as ld_api_last, and a late car's fees aim at the next
step of the refund table (24 hours late, two business days late) and start again, lower, when a step is lost."""
from alt.ld_api_core import Parts, build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, Parts(bands=True))
