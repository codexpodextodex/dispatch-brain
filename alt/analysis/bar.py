"""Compares a design with version 6 on the same saved weeks, against the bar for a design that counts.

    python3 -X utf8 -m alt.analysis.bar design=pairhold_h4 [lab_step=12] [--base design=other ...]

For each family (lab, hold, fresh) and all together: weeks played by both, mean margin of each, the gain with
its standard error, weeks better, cars, mean and lowest on-time share, weeks under 93% and under 90%. Then the
eight hardest weeks of version 6 and their mean on-time share (the bar: at least 93.5%, no week under 90%).
The base is the current version (no settings, or `lab_step=12` alone in fast mode) unless `--base` names settings."""
from __future__ import annotations

import statistics
import sys

from dispatch.policy import VERSION
from lab.runs import KINDS, load

HARD = ["fresh-9", "fresh-12", "hold-10", "hold-17", "hold-2", "hold-9", "fresh-20", "lab-11"]


def parse(words: list[str]) -> dict:
    return {k: KINDS[k](v) for k, v in (word.split("=", 1) for word in words)}


def main() -> None:
    args = sys.argv[1:]
    base_words = args[args.index("--base") + 1:] if "--base" in args else []
    words = args[:args.index("--base")] if "--base" in args else args
    ours = parse(words)
    base = parse(base_words) if base_words else {k: v for k, v in ours.items() if k == "lab_step"}
    seeds = [f"{family}-{n}" for family in ("lab", "hold", "fresh") for n in range(1, 21)]
    a = {s: load(8, s, ours) for s in seeds}
    b = {s: load(8, s, base) for s in seeds}
    both = [s for s in seeds if a[s] and b[s]]
    print(f"{' '.join(words)}  against  {' '.join(base_words) or f'version {VERSION}'}{' (fast)' if 'lab_step' in base else ''}")
    print(f"{'family':7} {'weeks':>5} {'base':>7} {'design':>7} {'gain':>13} {'better':>7} {'cars':>9} {'on time':>8} {'lowest':>13} {'<93%':>9} {'<90%':>9}")
    for family in ("lab", "hold", "fresh", "all"):
        ss = [s for s in both if family == "all" or s.startswith(family + "-")]
        if not ss:
            continue
        m = lambda runs, s: runs[s]["score"]["marginCents"] / 100
        gains = [m(a, s) - m(b, s) for s in ss]
        err = statistics.stdev(gains) / len(gains) ** 0.5 if len(gains) > 1 else 0.0
        ot = lambda runs: [runs[s]["score"]["onTimeShare"] for s in ss]
        cars = lambda runs: statistics.mean(runs[s]["score"]["wonOrders"] for s in ss)
        print(f"{family:7} {len(ss):5} {statistics.mean(m(b, s) for s in ss):7,.0f} {statistics.mean(m(a, s) for s in ss):7,.0f} {statistics.mean(gains):+7,.0f} ± {err:4,.0f}"
              f" {sum(g > 0 for g in gains):>3}/{len(ss):<3} {cars(b):4.0f}>{cars(a):<4.0f} {statistics.mean(ot(a)):8.1%} {min(ot(b)):6.1%}>{min(ot(a)):6.1%}"
              f" {sum(x < .93 for x in ot(b)):4}>{sum(x < .93 for x in ot(a)):<4} {sum(x < .90 for x in ot(b)):4}>{sum(x < .90 for x in ot(a)):<4}")
    hard = [s for s in HARD if s in both]
    if hard:
        shares = lambda runs: [runs[s]["score"]["onTimeShare"] for s in hard]
        print(f"hardest {len(hard)} weeks, mean on time: base {statistics.mean(shares(b)):.1%}  design {statistics.mean(shares(a)):.1%};  "
              f"margin {statistics.mean(b[s]['score']['marginCents'] for s in hard) / 100:,.0f} > {statistics.mean(a[s]['score']['marginCents'] for s in hard) / 100:,.0f}")
        rest = [s for s in both if s not in HARD]
        for label, ss in ((f"the {len(hard)} hardest", hard), (f"the other {len(rest)}", rest)):
            if len(ss) > 1:
                gains = [(a[s]["score"]["marginCents"] - b[s]["score"]["marginCents"]) / 100 for s in ss]
                print(f"  gain on {label}: {statistics.mean(gains):+,.0f} ± {statistics.stdev(gains) / len(gains) ** 0.5:,.0f}, cars "
                      f"{statistics.mean(b[s]['score']['wonOrders'] for s in ss):.0f} > {statistics.mean(a[s]['score']['wonOrders'] for s in ss):.0f}")
        print("  " + "  ".join(f"{s} {b[s]['score']['onTimeShare']:.1%}>{a[s]['score']['onTimeShare']:.1%}" for s in hard))


if __name__ == "__main__":
    main()
