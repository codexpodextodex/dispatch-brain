"""What price will this dealer accept from us right now? We never see the competitor's price, and it moves
all week: with the day, with each dealer's trust in us, with a price war or an outage, and with the
competitor's own answer to our wins. So we keep one number that we can learn from our own quotes:

    level = the price, in list prices, at which the dealer says yes half of the time.

The level of a request is a market level shared by all requests, times an offset for each thing we know about
the request: its dealer, the town the car goes to, and the fastest delivery option we quote. Each answer to a
quote moves the market level and the offsets of that request a little: a yes we did not expect moves them up,
a no we did not expect moves them down. This is online logistic regression of "won" on the log of the price.

Given the level, the chance to win at a price follows, and we quote the price with the best expected margin.
"""
from __future__ import annotations

import math
from collections import defaultdict

Key = tuple[str, str]  # (family, name): ("dealer", "D01"), ("to", "oulu"), ("option", "same_day")


def chance(level: float, markup: float, spread: float) -> float:
    """The chance that a request whose level is `level` accepts the price `markup`, both in list prices."""
    x = (math.log(level) - math.log(markup)) / spread
    return 1 / (1 + math.exp(-x)) if x > -50 else 0.0


class PriceBook:
    def __init__(self, start: float, spread: float, rates: dict[str, float]):
        self.spread = spread  # how fast the chance to win falls as the price rises, in log price
        self.rates = rates  # how far one answer moves the market level ("market") and an offset of each family
        self.market = math.log(start)
        self.offset: dict[Key, float] = defaultdict(float)  # log offset from the market

    def level(self, keys: list[Key]) -> float:
        return math.exp(self.market + sum(self.offset[key] for key in keys))

    def learn(self, keys: list[Key], markup: float, won: bool) -> None:
        """One answer to one quote: move the levels by how much it surprised us."""
        surprise = (1.0 if won else 0.0) - chance(self.level(keys), markup, self.spread)
        self.market += self.rates["market"] * surprise
        for key in keys:
            self.offset[key] += self.rates[key[0]] * surprise

    def new_day(self) -> None:
        """A new working day begins. This book carries its level over; DayBook starts the day afresh."""

    def best_markup(self, keys: list[Key], cost: float, floor: float, ceiling: float) -> tuple[float, float]:
        """The markup with the best expected margin for a car that costs `cost` list prices to move, and
        that expected margin. Margin = chance to win at the markup x (markup - cost)."""
        level, best, best_value = self.level(keys), floor, -1.0
        steps = max(1, round((ceiling - floor) / 0.01))
        for i in range(steps + 1):
            markup = floor + (ceiling - floor) * i / steps
            value = chance(level, markup, self.spread) * (markup - cost)
            if value > best_value:
                best, best_value = markup, value
        return best, best_value


class DayBook(PriceBook):
    """A price book that knows how the market moves: by the day.

    Measured with `fork` (lab/limits.py): the price the dealers take is one level for the whole working day,
    the same for every dealer once their trust in us is taken out, and a new level the next morning, up to 30%
    away. Two requests of one day differ by about 8%. The plain book carries yesterday's level into the morning
    and needs hours to let go of it.

    So this book keeps, for today only, how likely each level is (a row of weights over levels from 0.8 to 2.2
    list prices). Every answer sharpens it: a yes at 1.5 rules out the low levels, a no at 1.6 the high ones.
    After ten answers the day's level is known to a few percent. The offsets of towns are kept and learned
    slowly, as before. Each morning the weights start wide again around what the week has shown so far."""

    def __init__(self, start: float, spread: float, rates: dict[str, float], noise: float = 0.05, prior: float = 0.18):
        super().__init__(start, spread, rates)
        self.noise = noise  # how much two requests of one day differ, as the scale of the chance to win
        self.prior = prior  # how far a day's level can lie from what we expect in the morning, in log price
        self.grid = [math.log(0.80) + 0.02 * i for i in range(51)]
        self.home = math.log(start)
        self.days: list[float] = []  # the level each finished day settled on
        self.answers = 0
        self.weights: list[float] = []
        self.new_day()

    def new_day(self) -> None:
        if self.answers:
            self.days.append(self.market)
        centre = (self.home + sum(self.days)) / (1 + len(self.days))  # the week so far, and our first guess as one more day
        self.weights = [math.exp(-0.5 * ((g - centre) / self.prior) ** 2) for g in self.grid]
        self.answers = 0
        self.settle()

    def settle(self) -> None:
        total = sum(self.weights)
        self.weights = [w / total for w in self.weights]
        self.market = sum(w * g for w, g in zip(self.weights, self.grid))
        self.likely = [(w, g) for w, g in zip(self.weights, self.grid) if w > 1e-6]  # the levels still in play

    def win(self, x: float) -> float:
        """The chance that a request takes a price whose logarithm, less the request's own offsets, is `x`."""
        return sum(w / (1 + math.exp(min(50.0, (x - g) / self.noise))) for w, g in self.likely)

    def learn(self, keys: list[Key], markup: float, won: bool) -> None:
        x = math.log(markup) - sum(self.offset[key] for key in keys)
        surprise = (1.0 if won else 0.0) - self.win(x)
        for i, g in enumerate(self.grid):
            yes = 1 / (1 + math.exp(min(50.0, max(-50.0, (x - g) / self.noise))))
            self.weights[i] *= yes if won else 1 - yes
        self.answers += 1
        self.settle()
        for key in keys:
            self.offset[key] += self.rates[key[0]] * surprise

    def best_markup(self, keys: list[Key], cost: float, floor: float, ceiling: float) -> tuple[float, float]:
        shift = sum(self.offset[key] for key in keys)

        def value(markup: float) -> float:
            return self.win(math.log(markup) - shift) * (markup - cost)

        if floor >= ceiling:  # a car that costs more than we may ever ask: the floor says no
            return floor, value(floor)
        coarse = [floor + 0.04 * i for i in range(int((ceiling - floor) / 0.04) + 1)]
        centre = max(coarse, key=value)  # first every 4 cents of a list price, then every cent around the best
        fine = [m for m in (centre + 0.01 * i for i in range(-4, 5)) if floor <= m <= ceiling] or [centre]
        best = max(fine, key=value)
        return best, value(best)
