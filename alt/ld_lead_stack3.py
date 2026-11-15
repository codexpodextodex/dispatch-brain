"""As alt/ld_lead_stack2 (fee rules A under 3 hours and B + the punctuality desk ld_ontime_tell4), but WITH the day
cap also for cars due after Friday: version 7's cap untouched. It tells how much of stack2's gain and of its thinner
tail (60 exact weeks with guard=0.08: +801 ± 120, eight hardest weeks 93.4% on time against 94.3%, lowest 90.9%)
comes from taking the cap off the last Monday."""
from alt.ld_lead_stack2 import build


def make(client, world, level, now, params):
    return build(client, world, level, now, params, monday_cap=True)
