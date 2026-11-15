"""Compares settings with a base on the saved weeks, week by week (the same seeds for both).

    python -m lab.compare cost=1.0 road_fee_blend=1.0 road_cost_blend=1.0 lab_step=12 -- pairs=1 -- late_open=1.2 -- hour_cost=8 fee_share=0.5

The first group of settings is the base; each later group is added to it. For each family (lab, hold): the
mean margin, the gain over the base with its standard error over the weeks, how many weeks are better, cars,
mean and lowest on-time share and the weeks under 93%. Nothing is played: weeks that are not saved are left out."""
from __future__ import annotations

import statistics
import sys

from lab.runs import KINDS, load


def parse(words: list[str]) -> dict:
    return {k: KINDS[k](v) for k, v in (word.split("=", 1) for word in words)}


def weeks(setting: dict, family: str, count: int = 20) -> dict[int, dict]:
    runs = {n: load(8, f"{family}-{n}", setting) for n in range(1, count + 1)}
    return {n: run["score"] for n, run in runs.items() if run}


def main() -> None:
    groups, current = [], []
    for word in sys.argv[1:]:
        if word == "--":
            groups.append(current)
            current = []
        else:
            current.append(word)
    groups.append(current)
    base = parse(groups[0])
    print(f"base: {' '.join(groups[0])}")
    print(f"{'added to the base':44} {'family':6} {'weeks':>5} {'mean':>7} {'gain':>14} {'better':>7} {'cars':>5} {'on time':>8} {'lowest':>7} {'<93%':>4} {'<90%':>4}")
    for words in [[]] + groups[1:]:
        setting = {**base, **parse(words)}
        total = []
        for family in ("lab", "hold"):
            ours, theirs = weeks(setting, family), weeks(base, family)
            both = sorted(set(ours) & set(theirs))
            if not both:
                print(f"{' '.join(words) or '(the base itself)':44} {family:6} {0:5}")
                continue
            gains = [(ours[n]["marginCents"] - theirs[n]["marginCents"]) / 100 for n in both]
            total += gains
            error = statistics.stdev(gains) / len(gains) ** 0.5 if len(gains) > 1 else 0.0
            shares = [ours[n]["onTimeShare"] for n in both]
            print(f"{' '.join(words) or '(the base itself)':44} {family:6} {len(both):5} {statistics.mean(ours[n]['marginCents'] for n in both) / 100:7,.0f} "
                  f"{statistics.mean(gains):+7,.0f} ± {error:4,.0f} {sum(g > 0 for g in gains):>4}/{len(both):<2} {statistics.mean(ours[n]['wonOrders'] for n in both):5.0f} "
                  f"{statistics.mean(shares):8.1%} {min(shares):7.1%} {sum(s < 0.93 for s in shares):4} {sum(s < 0.90 for s in shares):4}")
        if words and len(total) > 2:
            print(f"{'':44} {'both':6} {len(total):5} {'':7} {statistics.mean(total):+7,.0f} ± {statistics.stdev(total) / len(total) ** 0.5:4,.0f}")


if __name__ == "__main__":
    main()
