"""What does a car cost us to move, and how often is it late? Fitted on the tuning weeks, checked on the holdout.

    python -m lab.fit_cost --set notes=ours ...

Two straight-line fits on the won orders of the saved weeks, with four things known when the request arrives:
the hours of driving, how many drivers live within 30 km of the delivery (their trip home is free), how many
live within 30 km of the pickup (the app notifies only them), and the hour by which the car must be collected.

    cost  = what we paid for the car, in typical fees: the driver, refunds, failed visits
    late  = the share of such cars that arrive late
"""
from __future__ import annotations

import argparse
import math

from lab.orders import rows
from lab.runs import EVENTS, KINDS, load
from lab.sweep import seeds


def features(row: dict) -> list[float]:
    """1, hours of driving over three, how thin the drivers are at the delivery and at the pickup, and how many
    hours before 16:00 the car must be collected."""
    return [1.0, max(0.0, row["drive"] / 60 - 3), thin(row["near_delivery"]), thin(row["near_pickup"]), max(0.0, 16 - row["last_pickup_hour"])]


def thin(drivers: int) -> float:
    """1 with no driver nearby, 0.5 with 30, falling towards 0 with hundreds."""
    return 1 / (1 + drivers / 30)


def solve(xs: list[list[float]], ys: list[float]) -> list[float]:
    """Least squares by the normal equations: few features, so plain elimination is enough."""
    n = len(xs[0])
    a = [[sum(x[i] * x[j] for x in xs) for j in range(n)] + [sum(x[i] * y for x, y in zip(xs, ys))] for i in range(n)]
    for i in range(n):
        pivot = max(range(i, n), key=lambda r: abs(a[r][i]))
        a[i], a[pivot] = a[pivot], a[i]
        for r in range(n):
            if r != i:
                factor = a[r][i] / a[i][i]
                a[r] = [v - factor * w for v, w in zip(a[r], a[i])]
    return [a[i][n] / a[i][i] for i in range(n)]


def collect(family: str, changed: dict, count: int) -> list[dict]:
    out = []
    for seed in seeds(count, family):
        run = load(8, seed, changed)
        if run and (EVENTS / f"{run['worldId']}.json.gz").exists():
            out += [r for r in rows(run) if not r["cancelled"] and r["legs"] == 1]
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--set", nargs="*", default=[], metavar="NAME=VALUE")
    parser.add_argument("--seeds", type=int, default=10)
    args = parser.parse_args()
    changed = {k: KINDS[k](v) for k, v in (item.split("=", 1) for item in args.set)}
    lab, hold = collect("lab", changed, args.seeds), collect("hold", changed, args.seeds)
    cost = lambda r: (r["fees"] + r["refunds"] + r["other"]) / r["typical"]
    late = lambda r: 0.0 if r["on_time"] else 1.0
    names = ["base", "per hour of driving over 3", "thin drivers at delivery", "thin drivers at pickup", "per hour the last pickup is before 16:00"]
    for label, target in (("cost, in typical fees", cost), ("late share", late)):
        weights = solve([features(r) for r in lab], [target(r) for r in lab])
        print(f"\n{label}: fitted on {len(lab)} orders of the tuning weeks")
        for name, w in zip(names, weights):
            print(f"    {name:<30} {w:+.3f}")
        for family, data in (("tuning", lab), ("holdout", hold)):
            if not data:
                continue
            predicted = [sum(w * f for w, f in zip(weights, features(r))) for r in data]
            actual = [target(r) for r in data]
            mean = sum(actual) / len(actual)
            explained = 1 - sum((a - p) ** 2 for a, p in zip(actual, predicted)) / sum((a - mean) ** 2 for a in actual)
            # calibration: the orders sorted by prediction, in five equal groups
            order = sorted(range(len(data)), key=lambda i: predicted[i])
            fifths = [order[i * len(order) // 5:(i + 1) * len(order) // 5] for i in range(5)]
            groups = "  ".join(f"{sum(predicted[i] for i in g) / len(g):.2f}->{sum(actual[i] for i in g) / len(g):.2f}" for g in fifths)
            print(f"    {family:<8} mean {mean:.3f}, variance explained {explained:.1%}; predicted->actual by fifth: {groups}")


if __name__ == "__main__":
    main()
