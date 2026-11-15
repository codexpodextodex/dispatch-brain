"""Which candidates raise the chance of a top-ten week? The final is one week and the top ten go to the jury, so a
change that gains in most weeks and loses badly in a few can be worth more than its mean says, and the reverse.

    python -m lab.top10                      # every row below, from the weeks that are saved
    python -m lab.top10 day_cap=0.125        # one more candidate against the current version

The model, from our own ranking weeks (EXPERIMENTS.md 64, 69): against the tenth team of a week our margin stood
at +1% for version 9 with a spread of 6 points from week to week, and version 10 is 2.4% above version 9. So a
week counts as "in the top ten" with the chance that a normal draw of spread SIGMA leaves us above the line, given
the edge of the base version and the candidate's own gain in that week, times the chance that the week is ranked
(on time at 90% or more, with the week's own noise as in lab/cands.py). It is a ruler for comparing candidates on
the same weeks, not a forecast."""
from __future__ import annotations

import hashlib
import json
import math
import statistics as st
import sys

from lab.runs import KINDS, RUNS

SEEDS = [f"{family}-{i}" for family in ("lab", "hold", "fresh") for i in range(1, 21)]
SIGMA = 0.06
EDGE = {8: -0.005, 9: 0.010, 10: 0.034, 11: 0.050}  # the base version's margin against the tenth team of a week
ROWS: list[tuple[str, int, dict, dict]] = [  # name, version the weeks were saved under, base, candidate
    ("premium cars due after Friday", 10, {}, {"premium_after": 1}),
    ("... with their cost 0.2 higher", 10, {}, {"premium_after": 1, "cost_premium": 0.2}),
    ("long private drives due after Friday", 10, {}, {"private_after": 1}),
    ("cap kept after Friday for 4 h+ drives", 10, {}, {"cap_after_hours": 4.0}),
    ("... charged by long cars only, 2 per 100 drivers", 10, {}, {"cap_after_hours": 4.0, "cap_long": 0.02}),
    ("version 9 -> version 10 (no cap after Friday)", 9, {}, {"cap_week_only": 1}),
    ("cap x2 after Friday", 9, {}, {"cap_monday": 2.0}),
    ("no cap after Friday + their cost 0.1 lower", 9, {"cap_week_only": 1}, {"cap_week_only": 1, "cost_after": 0.1}),
    ("no cap after Friday + fees held over the weekend", 9, {"cap_week_only": 1}, {"cap_week_only": 1, "weekend_hold": 1}),
    ("no brake", 9, {}, {"guard": 0.0}),
    ("no day cap at all", 9, {}, {"day_cap": 0.0}),
    ("any car with 4 hours' notice", 9, {}, {"min_find_hours": 4.0}),
    ("home-bound cars cost 0.1 less", 9, {}, {"cost_home": 0.1}),
    ("home-bound cars cost 0.05 less", 9, {}, {"cost_home": 0.05}),
    ("wait 6 h for a partner", 9, {}, {"pair_hold": 6.0}),
    ("fill a lagging day, 10% off the cost", 8, {}, {"fill_cut": 0.1}),
    ("fill a lagging day, 20% off the cost", 8, {}, {"fill_cut": 0.2}),
    ("version 8 -> version 9 (wait for a partner)", 8, {}, {"pair_hold": 4.0}),
]


def phi(z: float) -> float:
    return 0.5 * (1 + math.erf(z / 2 ** 0.5))


def noise(share: float) -> float:
    return 0.0162 if share < 0.94 else 0.0081 if share < 0.96 else 0.0064 if share < 0.975 else 0.0054


def saved(seed: str, version: int, changed: dict) -> dict | None:
    """A saved week by the text it was saved under: the version of that time and the settings that were not its defaults."""
    setting = json.dumps({"version": version, **dict(sorted(changed.items()))}, sort_keys=True)
    path = RUNS / f"L8-{seed}-{hashlib.sha1(setting.encode()).hexdigest()[:10]}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def ranked(share: float) -> float:
    return 1 - phi((0.90 - share) / noise(share))


def row(name: str, version: int, base: dict, changed: dict) -> str:
    a, b = {s: saved(s, version, base) for s in SEEDS}, {s: saved(s, version, changed) for s in SEEDS}
    both = [s for s in SEEDS if a[s] and b[s]]
    if len(both) < 12:
        return f"{name:50} {len(both):3}"
    edge = EDGE[version] + (0.024 if base.get("cap_week_only") else 0.0)
    gain = {s: b[s]["score"]["marginCents"] / a[s]["score"]["marginCents"] - 1 for s in both}
    euros = [(b[s]["score"]["marginCents"] - a[s]["score"]["marginCents"]) / 100 for s in both]
    was = {s: phi(edge / SIGMA) * ranked(a[s]["score"]["onTimeShare"]) for s in both}
    now = {s: phi((edge + gain[s]) / SIGMA) * ranked(b[s]["score"]["onTimeShare"]) for s in both}
    before, after = st.mean(was.values()), st.mean(now.values())
    error = st.stdev(now[s] - was[s] for s in both) / len(both) ** 0.5  # of the difference, week by week
    unranked = st.mean(1 - ranked(b[s]["score"]["onTimeShare"]) for s in both)
    return (f"{name:50} {len(both):3} {st.mean(euros):+6.0f} ± {st.stdev(euros) / len(euros) ** 0.5:3.0f} {st.median(euros):+6.0f} {sum(g > 0.02 for g in gain.values()):4} {sum(g < -0.05 for g in gain.values()):4} "
            f"{unranked:6.1%} {before:7.1%} {after:7.1%} {100 * (after - before):+6.1f} ± {100 * error:3.1f}")


def main() -> None:
    rows = ROWS
    if len(sys.argv) > 1:
        rows = []
        for arg in sys.argv[1:]:
            changed = {k: KINDS[k](v) for k, v in (item.split("=", 1) for item in arg.split(","))}
            rows.append((arg.replace(",", " "), max(EDGE), {}, changed))
    print(f"{'candidate against its base':50} {'wks':>3} {'mean gain':>12} {'median':>6} {'>+2%':>4} {'<-5%':>4} {'unranked':>8} {'top ten: base':>13} {'with it':>7} {'points':>12}")
    for name, version, base, changed in rows:
        print(row(name, version, base, changed))


if __name__ == "__main__":
    main()
