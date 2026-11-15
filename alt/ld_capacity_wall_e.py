"""Cars due after Friday at version 7's cost, behind a wall that stands further out while their gigs find drivers
(0.12 live cars a listed driver with up to 15% of them waiting) and moves in to 0.084 as they wait or the week turns
careful: `ld_lead_monoff` kept for the weeks that can take the cars; see alt/ld_capacity_core.py and
leaders/capacity (signals.py: with under 10% waiting the Monday cars were late 1.3% even past 0.15 cars a driver,
with 20 to 30% waiting 8.7%)."""
from alt.ld_capacity_core import make as base_make


def make(client, world, level, now, params):
    return base_make(client, world, level, now, params, scale=1.0, wall=0.12, flow_from=0.15, flow_slope=1.25, floor=0.70)
