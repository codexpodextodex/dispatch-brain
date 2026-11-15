"""leaders/capgigs: version 8's cap on cars, unchanged; for last pickups up to Friday also the cap on driver-hours
(0.5497 a listed driver, the new car by its own hours / 5.06), the larger charge counts. Cars due after Friday keep
version 8's cap alone. See alt/ld_capgigs_more.py."""
from alt.ld_capgigs_more import build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, mode="bothwk", cap=0.5497, ref=5.06)
