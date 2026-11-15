"""A price book built on what the rules and the fork measurements say a dealer's limit is made of
(leaders/price/REPORT.md; lab/limits.py; sim/SPEC.md D2 to D8):

    limit of a request = list price x the day's level x (1 + 1% x our on-time orders with the dealer)
                         x an offset of its route (stable within the week) x a small draw of its own;
    one working day the level is 20% lower from 08:00 to 18:00 (the price war);
    one working day the dealers who load within 80 km of one town take about 28% more (the outage).

So the book keeps exactly these things and nothing else:
  - today's level: a row of weights over levels (0.85 to 2.25 list prices), started afresh each morning around
    what the week has shown, with a second hump 20% lower while the price war has not been seen;
  - for each region that could be without the competitor today, how likely that is (same row, shifted 28%);
  - an offset for the delivery town, the pickup town and the route, each with its own uncertainty, so that the
    first answers move it far and later ones little (a Kalman filter on yes/no answers);
  - the dealer's trust is not learned: it is counted from our own deliveries, as the rules say.
Every answer (won or lost at a price) reweighs the rows. A quote is the price with the best expected margin
against the whole row, not against one number, so while the morning is still unsure the price hedges.

Pure Python: the practice machine has no numpy."""
from __future__ import annotations

import dataclasses
import math

from dispatch.desk import Desk
from dispatch.geo import DAY, Geo, straight_km
from dispatch.policy import OPTION_VALUE, Params, Policy

LIFT, WAR = 0.25, 0.223  # log: what an outage region takes more (measured 0.23 to 0.39), and the war day less
STEP = 0.025
GRID = [math.log(0.85) + STEP * i for i in range(40)]
DEFAULTS = {
    "home": math.log(1.40),  # the level a normal day has before we know the week (rules: 1.26 to 1.54)
    "first_sd": 0.09, "prior_sd": 0.07,  # how far a normal day lies from that on Monday, and from the week's days later
    "noise": 0.085,  # how far two requests of one route and day differ (log)
    "tau": {"to": 0.07, "from": 0.04, "route": 0.08},  # how far the offsets lie from zero before any answer
    "war": 1, "outage": 1,  # 0 switches the hump for the price war, the rows for the outage, off
    "war_first": 0.35,  # the chance that Monday is the price-war day (7 of 13 measured weeks)
    "widen": 1.0,  # the spread a price is set against, as a multiple of the spread the book believes
    "scale": 1.0,  # version 7's cost of a car times this: the knob that holds the number of cars
    "menu": 1,  # 1 learns from the level a quote beats under the dealers' option rule; 0 from the price as version 7
}


def sig(x: float) -> float:
    return 1.0 if x > 40 else 0.0 if x < -40 else 1 / (1 + math.exp(-x))


def phi_ratio(t: float) -> float:
    """Density over distribution of the normal at t: the pull of a yes that had chance Phi(t)."""
    cdf = 0.5 * (1 + math.erf(t / 1.4142135623730951))
    return math.exp(-0.5 * t * t) / 2.5066282746310002 / max(cdf, 1e-12)


def best_price(comps: list[tuple[float, float]], s: float, cost: float, floor: float, ceiling: float) -> float:
    """The markup with the best expected margin when the limit's log is a mix of logistic humps (weight, centre)
    of scale `s`. First every 3%, then every half percent around the best."""
    if floor >= ceiling:
        return floor
    low = max(math.log(floor), min(c for _, c in comps) - 5 * s)
    high = min(math.log(ceiling), max(c for _, c in comps) + 3 * s)
    if high <= low:
        return floor if high < math.log(floor) + 1e-9 else math.exp(high)

    def value(x: float) -> float:
        return (math.exp(x) - cost) * sum(w * sig((c - x) / s) for w, c in comps)

    n = max(1, int((high - low) / 0.03))
    coarse = [low + (high - low) * i / n for i in range(n + 1)]
    centre = max(coarse, key=value)
    fine = [x for x in (centre + 0.005 * i for i in range(-6, 7)) if low <= x <= high] or [centre]
    return math.exp(max(fine, key=value))


class SharpBook:
    spread = 0.14  # for the policy's own estimate of the chance to win a waiting quote (the cap on cars a day)

    def __init__(self, places: dict[str, tuple[float, float]], trusted: dict[str, int], cfg: dict | None = None):
        self.c = {**DEFAULTS, **(cfg or {})}
        self.trusted = trusted  # dealer -> on-time orders as the dealer counts them: the policy keeps it
        regions: dict[frozenset, str] = {}
        for town in sorted(places):
            regions.setdefault(frozenset(o for o in places if straight_km(places[town], places[o]) <= 80), town)
        self.regions = list(regions)
        self.inside = {town: {k + 1 for k, region in enumerate(self.regions) if town in region} for town in places}
        self.off: dict[tuple, list[float]] = {}  # (family, name) -> [mean, variance]
        self.offset: dict = {}  # the policy clears its own outage offsets here each morning: this book has none of those
        self.days: list[tuple[float, float]] = []  # each finished day: its level, and how surely it was the price war
        self.outage_seen = False
        self.answers = 0
        self.rows: list[list[float]] = []
        self.war_share: list[float] = []
        self.cache: dict = {}
        self.new_day()

    # The day.

    def summary(self) -> tuple[float, float, float]:
        """Today's level, how surely today is the price war, how surely there is an outage somewhere."""
        level = war = 0.0
        for row in self.rows:
            for i, w in enumerate(row):
                level += w * GRID[i]
                war += w * self.war_share[i]
        return level, war, 1 - sum(self.rows[0])

    def new_day(self) -> None:
        c = self.c
        if self.answers:
            level, war, out = self.summary()
            self.days.append((level, war))
            self.outage_seen = self.outage_seen or out > 0.8
        n = len(self.days)
        centre = (c["home"] + sum(level + WAR * war for level, war in self.days)) / (1 + n)
        sd = c["prior_sd"] if n else c["first_sd"]
        p_war = 0.0
        if c["war"]:
            p_war = c["war_first"] if n == 0 else min(0.9, max(0.02, (1 - sum(war for _, war in self.days)) / max(1, 5 - n)))
        normal = [math.exp(-0.5 * ((g - centre) / sd) ** 2) for g in GRID]
        low = [math.exp(-0.5 * ((g - centre + WAR) / sd) ** 2) for g in GRID]
        normal, low = [x / sum(normal) for x in normal], [x / sum(low) for x in low]
        prior = [(1 - p_war) * a + p_war * b for a, b in zip(normal, low)]
        self.war_share = [p_war * b / p if p > 0 else 0.0 for b, p in zip(low, prior)]
        p_out = min(0.9, 1 / max(1, 5 - n)) if c["outage"] and not self.outage_seen else 0.0
        self.rows = [[(1 - p_out) * w for w in prior]]
        if p_out:
            self.rows += [[p_out / len(self.regions) * w for w in prior] for _ in self.regions]
        self.answers = 0
        self.cache = {}

    def split(self, pickup: str) -> tuple[list[float], list[float]]:
        """The weights over today's level, with this pickup town outside and inside an outage."""
        if pickup not in self.cache:
            inside, outer, inner = self.inside.get(pickup, set()), [0.0] * len(GRID), [0.0] * len(GRID)
            for k, row in enumerate(self.rows):
                target = inner if k in inside else outer
                for i, w in enumerate(row):
                    target[i] += w
            self.cache[pickup] = (outer, inner)
        return self.cache[pickup]

    # A request.

    def offsets(self, pickup: str, delivery: str) -> tuple[float, float, list]:
        keys = [("to", delivery), ("from", pickup), ("route", pickup + ">" + delivery)]
        mean = var = 0.0
        for key in keys:
            m, v = self.off.get(key) or (0.0, self.c["tau"][key[0]] ** 2)
            mean, var = mean + m, var + v
        return mean, var, keys

    def humps(self, pickup: str, delivery: str, minute: int) -> tuple[list[tuple[float, float]], float]:
        """What the book believes about the log of a request's limit before trust: humps (weight, centre) and their scale."""
        mean, var, _ = self.offsets(pickup, delivery)
        s = 0.5513 * math.sqrt(self.c["noise"] ** 2 + var)
        outer, inner = self.split(pickup)
        comps: dict[float, float] = {}
        if 480 <= minute % DAY < 1080:
            for weights, shift in ((outer, 0.0), (inner, LIFT)):
                for i, w in enumerate(weights):
                    if w > 2e-4:
                        comps[GRID[i] + shift + mean] = comps.get(GRID[i] + shift + mean, 0.0) + w
        else:  # answered after 18:00: no outage, and the price war is over
            for i in range(len(GRID)):
                w = outer[i] + inner[i]
                if w > 2e-4:
                    for share, shift in ((1 - self.war_share[i], 0.0), (self.war_share[i], WAR)):
                        if share > 1e-3:
                            comps[GRID[i] + shift + mean] = comps.get(GRID[i] + shift + mean, 0.0) + w * share
        total = sum(comps.values())
        return [(w / total, centre) for centre, w in comps.items()], s

    def learn_at(self, dealer: str, pickup: str, delivery: str, minute: int, markup: float, won: bool) -> None:
        """One answer: the dealer took (or refused) the price `markup`, in list prices."""
        if not 480 <= minute % DAY < 1080:
            return  # the few evening answers say little about tomorrow and nothing about today's events
        x = math.log(markup / (1 + 0.01 * self.trusted.get(dealer, 0)))
        mean, var, keys = self.offsets(pickup, delivery)
        outer, inner = self.split(pickup)
        # the offsets: a Kalman step on a yes/no answer, against what the rows say about the level
        level = spread = 0.0
        for weights, shift in ((outer, 0.0), (inner, LIFT)):
            for i, w in enumerate(weights):
                level += w * (GRID[i] + shift)
        for weights, shift in ((outer, 0.0), (inner, LIFT)):
            for i, w in enumerate(weights):
                spread += w * (GRID[i] + shift - level) ** 2
        total = spread + var + self.c["noise"] ** 2
        t = (level + mean - x) / math.sqrt(total)
        pull = phi_ratio(t) if won else -phi_ratio(-t)
        shrink = pull * (pull + t)
        for key in keys:
            m, v = self.off.get(key) or (0.0, self.c["tau"][key[0]] ** 2)
            self.off[key] = [m + v / math.sqrt(total) * pull, v * (1 - v / total * shrink)]
        # the rows: each level, with and without an outage here, by how well it explains the answer
        s = 0.5513 * math.sqrt(self.c["noise"] ** 2 + var)
        plain = [sig((g + mean - x) / s) for g in GRID]
        lifted = [sig((g + LIFT + mean - x) / s) for g in GRID]
        if not won:
            plain, lifted = [1 - p for p in plain], [1 - p for p in lifted]
        inside, total = self.inside.get(pickup, set()), 0.0
        for k, row in enumerate(self.rows):
            like = lifted if k in inside else plain
            for i in range(len(GRID)):
                row[i] *= like[i]
            total += sum(row)
        if total <= 0:  # an answer no level explains: start the day's rows again rather than divide by zero
            self.new_day()
            return
        self.rows = [[w / total for w in row] for row in self.rows]
        self.answers += 1
        self.cache = {}

    # What dispatch.policy.Policy asks of its book.

    def level(self, keys: list) -> float:
        k = dict(keys)
        comps, _ = self.humps(k["from"], k["to"], k["at"])
        return math.exp(sum(w * c for w, c in comps)) * (1 + 0.01 * self.trusted.get(k["dealer"], 0))

    def learn(self, keys: list, markup: float, won: bool) -> None:
        k = dict(keys)
        self.learn_at(k["dealer"], k["from"], k["to"], k["at"], markup, won)


class SharpPolicy(Policy):
    """Version 7 with the price book replaced. Costs, cars wanted, fees, pairs, the brake: all as version 7."""

    def __init__(self, params: Params, places: dict[str, tuple[float, float]], cfg: dict | None = None):
        super().__init__(params)
        self.book = SharpBook(places, self.trusted, cfg)
        self.cfg = self.book.c

    def keys_of(self, request: dict, kinds: list[str]) -> list:
        leg = request["legs"][0]
        return [("dealer", request["dealerId"]), ("to", leg["delivery"]["placeId"]), ("from", leg["pickup"]["placeId"]), ("at", request["respondBy"])]

    def markup(self, desk, request: dict, option: dict, last: int, keys: list, factor: float = 1.0) -> float:
        k = dict(keys)
        trust = 1 + 0.01 * self.trusted.get(k["dealer"], 0)
        cost = self.cfg["scale"] * self.cost(desk, request, option, last) / trust
        comps, s = self.book.humps(k["from"], k["to"], k["at"])
        return trust * best_price(comps, self.cfg["widen"] * s, cost, cost * (1 + self.p.min_margin), self.p.ceiling / trust)

    def beaten(self, request: dict, markups: dict[str, float]) -> float:
        """The competitor level a quote beats, as a price the dealer would see: trust makes our price count for less."""
        trust = 1 + 0.01 * self.trusted.get(request["dealerId"], 0)
        listed = {o["kind"]: o["listPriceCents"] for o in request["options"]}
        ours = max(OPTION_VALUE[kind] - markup * listed[kind] / trust for kind, markup in markups.items())
        return trust * max((OPTION_VALUE[kind] - ours) / cents for kind, cents in listed.items())


def make_with(client, world, level: int, now: int, params: Params, cfg: dict | None = None):
    world_map = client.map()
    places = {p["id"]: (p["lat"], p["lon"]) for p in world_map["places"]}
    if {**DEFAULTS, **(cfg or {})}["menu"]:
        params = dataclasses.replace(params, menu=2)  # the policy then hands the book the level a quote beats (`beaten`)
    policy = SharpPolicy(params, places, cfg)
    desk = Desk(world, level, now, policy, Geo(world_map))
    desk.meet(world.roster())
    return desk
