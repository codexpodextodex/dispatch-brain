"""At what fee version 6's single cars are booked, in noise-free typical fees (the road line), and how that
depends on where drivers live. Reads saved exact weeks of version 6.

    PYTHONPATH=. python -X utf8 -m alt.analysis.fee_levels"""
from __future__ import annotations

from collections import defaultdict

from dispatch.policy import ROAD_BASE, ROAD_MINUTE
from lab.orders import geo, rows
from lab.runs import load


def main() -> None:
    g = geo()
    out = []
    for family in ("lab", "hold", "fresh"):
        for n in range(1, 21):
            run = load(8, f"{family}-{n}", {})
            if run:
                out += rows(run)
    plain = [r for r in out if r["legs"] == 1 and not r["private"] and not r["premium"] and r["bookings"] and not r["cancelled"]]
    by = defaultdict(list)
    for r in plain:
        line = ROAD_BASE + ROAD_MINUTE * r["drive"]  # drive is road minutes
        fee = r["final_fee"] * r["typical"] / line
        first = r["first_fee"] * r["typical"] / line
        nd = "deliv<30" if r["near_delivery"] < 30 else "deliv<100" if r["near_delivery"] < 100 else "deliv100+"
        hr = "last<13" if r["last_pickup_hour"] < 13 else "last<17" if r["last_pickup_hour"] < 17 else "last17+"
        for key in ("all", nd, hr, f"{nd} {hr}"):
            by[key].append((first, fee, r["book_wait"], r["on_time"], r["drops"]))
    q = lambda xs, f: sorted(xs)[int(f * (len(xs) - 1))]
    print(f"{'group':24} {'cars':>6} {'first p25':>9} {'median':>7} {'p75':>6} {'p90':>6} {'booked <1h':>10} {'on time':>8} {'dropped':>8}")
    for key in sorted(by):
        xs = by[key]
        firsts = [x[0] for x in xs]
        print(f"{key:24} {len(xs):6} {q(firsts, .25):9.2f} {q(firsts, .5):7.2f} {q(firsts, .75):6.2f} {q(firsts, .9):6.2f} {sum(x[2] <= 1 for x in xs) / len(xs):10.0%} {sum(x[3] for x in xs) / len(xs):8.1%} {sum(x[4] > 0 for x in xs) / len(xs):8.1%}")


if __name__ == "__main__":
    main()
