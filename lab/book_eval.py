"""Replays a price book against the dealers' measured limits (lab/limits.py), without the server.

    python -m lab.book_eval                    # every variant below, on all measured weeks
    python -m lab.book_eval lab                # only on the weeks of one family

A measured week knows, for every request, the highest price the dealer takes. So any way of pricing can be
replayed in a second: the book quotes each request in the order they came, wins when its price is at or under
the limit, and learns from each answer 15 minutes later, as the desk does. Two things the replay leaves out:
what a different set of wins does to the dealers' trust and to the competitor later in the week, and the
drivers. So a variant that wins here is a candidate, and played weeks decide.

Variants are compared at the same number of cars won (the cost is scaled until each wins `SHARE` of the plain
requests), because a book that simply prices lower wins more and delivers later."""
from __future__ import annotations

import math
import sys
from collections import defaultdict

from dispatch.pricing import DayBook, PriceBook, chance
from lab.limit_fit import load

SHARE = 0.45  # of the plain requests: about 375 cars a week, what the desk wins and delivers today

VARIANTS = {
    "today: market, dealer, delivery town": {},
    "+ trust, pickup, slower dealer 0.015": {"trust": 1, "families": ("dealer", "to", "from"), "rates": {"dealer": 0.015}},
    "+ trust, lane instead of towns": {"trust": 1, "families": ("dealer", "lane")},
    "day book: level per day, trust, towns": {"book": "day", "trust": 1, "families": ("to", "from")},
    "day book, towns slower 0.015": {"book": "day", "trust": 1, "families": ("to", "from"), "rates": {"to": 0.015, "from": 0.015}},
    "day book, towns slower, noise 0.065": {"book": "day", "trust": 1, "families": ("to", "from"), "rates": {"to": 0.015, "from": 0.015}, "noise": 0.065},
    "day book, lane 0.03": {"book": "day", "trust": 1, "families": ("lane",)},
    "day book, lane 0.06": {"book": "day", "trust": 1, "families": ("lane",), "rates": {"lane": 0.06}},
    "day book, lane 0.06, noise 0.065": {"book": "day", "trust": 1, "families": ("lane",), "rates": {"lane": 0.06}, "noise": 0.065},
    "day book, lane 0.10, noise 0.065": {"book": "day", "trust": 1, "families": ("lane",), "rates": {"lane": 0.10}, "noise": 0.065},
    "day book, towns 0.015 + lane 0.06": {"book": "day", "trust": 1, "families": ("to", "from", "lane"), "rates": {"to": 0.015, "from": 0.015, "lane": 0.06}, "noise": 0.065},
    "day book, towns + lane, noise 0.08": {"book": "day", "trust": 1, "families": ("to", "from", "lane"), "rates": {"to": 0.015, "from": 0.015, "lane": 0.06}, "noise": 0.08},
    "day book, towns + lane, half trust": {"book": "day", "trust": 0.5, "families": ("to", "from", "lane"), "rates": {"to": 0.015, "from": 0.015, "lane": 0.06}, "noise": 0.065},
}
RATES = {"market": 0.03, "dealer": 0.03, "to": 0.04, "from": 0.03, "lane": 0.03, "fastest": 0.02}


def keys_of(row: dict, families: tuple) -> list:
    names = {"dealer": row["dealer"], "to": row["delivery"], "from": row["pickup"], "lane": row["pickup"] + ">" + row["delivery"], "fastest": row["fastest"]}
    return [(family, names[family]) for family in families]


class Shrinking(PriceBook):
    """A price book whose steps get smaller as a key has been seen more often: a new dealer or town is learned
    fast, a well-known one is no longer thrown about by single answers. The market keeps its own steady step."""

    def __init__(self, start, spread, rates, half: float):
        super().__init__(start, spread, rates)
        self.half, self.seen = half, defaultdict(int)

    def learn(self, keys, markup, won):
        surprise = (1.0 if won else 0.0) - chance(self.level(keys), markup, self.spread)
        self.market += self.rates["market"] * surprise
        for key in keys:
            self.seen[key] += 1
            self.offset[key] += 3 * self.rates[key[0]] * surprise * self.half / (self.half + self.seen[key])


def replay(rows: list[dict], variant: dict, scale: float) -> dict:
    """One week, in the order the requests came. `scale` multiplies the cost: the price of a place in the day."""
    families = variant.get("families", ("dealer", "to"))
    rates = {**RATES, **variant.get("rates", {})}
    spread = variant.get("spread", 0.14)
    if variant.get("book") == "day":
        book = DayBook(variant.get("start", 1.38), spread, rates, variant.get("noise", 0.05), variant.get("prior", 0.18))
    else:
        book = Shrinking(1.15, spread, rates, variant["shrink"]) if variant.get("shrink") else PriceBook(1.15, spread, rates)
    day = 0
    waiting: list[tuple] = []  # (answer minute, keys, markup, won, trust shift)
    margin = won = 0.0
    errors, loss = [], 0.0
    for row in rows:
        while waiting and waiting[0][0] <= row["at"]:
            _, keys, markup, yes, shift = waiting.pop(0)
            book.learn(keys, markup / shift, yes)
        if row["day"] != day:
            day = row["day"]
            book.new_day()
        keys = keys_of(row, families)
        shift = 1 + variant.get("trust", 0) * row["trusted"] / 100  # what the rules add for our on-time orders: known, not learned
        level = book.level(keys) * shift
        cost = scale * row["cost"]
        book_cost = cost / shift
        markup = book.best_markup(keys, book_cost, floor=book_cost * 1.05, ceiling=3.0 / shift)[0] * shift
        yes = math.log(markup) <= row["y"]
        if yes:
            margin += (markup - row["cost"]) * row["list"] / 100
            won += 1
        errors.append(row["y"] - math.log(level))
        p = book.win(math.log(markup / shift) - sum(book.offset[k] for k in keys)) if variant.get("book") == "day" else chance(level, markup, spread)
        p = min(1 - 1e-6, max(1e-6, p))
        loss -= math.log(p if yes else 1 - p)
        waiting.append((row["respondBy"], keys, markup, yes, shift))
    mean = sum(errors) / len(errors)
    return {"margin": margin, "won": won, "n": len(rows), "bias": mean, "spread": (sum((e - mean) ** 2 for e in errors) / len(errors)) ** 0.5, "loss": loss / len(rows)}


def at_share(weeks: dict[str, list[dict]], variant: dict) -> tuple[float, list[dict]]:
    """The cost scale at which the variant wins SHARE of the requests over all weeks, and the weeks at that scale."""
    low, high = 0.5, 3.0
    for _ in range(14):
        scale = (low + high) / 2
        results = [replay(rows, variant, scale) for rows in weeks.values()]
        if sum(r["won"] for r in results) / sum(r["n"] for r in results) > SHARE:
            low = scale
        else:
            high = scale
    return scale, results


def main() -> None:
    from dispatch.policy import ROAD_BASE, ROAD_MINUTE
    weeks: dict[str, list[dict]] = defaultdict(list)
    for row in load(sys.argv[1] if len(sys.argv) > 1 else ""):
        if row["kind"] == "plain":
            line = ROAD_BASE + ROAD_MINUTE * row["minutes"]
            row["cost"] = min(1.25 * row["typical"], max(0.8 * row["typical"], line)) / row["list"]  # the noise-free typical fee, in list prices
            weeks[row["seed"]].append(row)
    for rows in weeks.values():
        rows.sort(key=lambda r: r["at"])
    print(f"{len(weeks)} measured weeks: {' '.join(weeks)}; plain requests only; every variant wins {SHARE:.0%} of them\n")
    print(f"{'price book':46} {'margin a week':>13} {'gain':>7} {'weeks better':>12} {'error of the level':>19} {'log loss':>9} {'cost scale':>10}")
    base = None
    for name, variant in VARIANTS.items():
        scale, results = at_share(weeks, variant)
        margins = [r["margin"] for r in results]
        if base is None:
            base = margins
        gains = [a - b for a, b in zip(margins, base)]
        print(f"{name:46} {sum(margins) / len(margins):13,.0f} {sum(gains) / len(gains):+7,.0f} {sum(g > 0 for g in gains):>5}/{len(gains):<6} "
              f"{sum(r['spread'] for r in results) / len(results):19.3f} {sum(r['loss'] for r in results) / len(results):9.3f} {scale:10.2f}")


if __name__ == "__main__":
    main()
