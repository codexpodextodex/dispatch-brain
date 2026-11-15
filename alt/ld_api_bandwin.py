"""API line: see alt/ld_api_core.py. This desk: Parts(bands=True, windows=True) = as ld_api_bands, and the late gig carries
windows of its own that end with the step of the refund table its fees aim at."""
from alt.ld_api_core import Parts, build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, Parts(bands=True, windows=True))
