"""Version 7 chooses the cars; a second book only raises a price where it is sure (leaders/price, section "hybrid").

Two real tests of the new price book (alt/ld_price_core.py) showed: on the cars both desks won it sold 1.5 euros a
car dearer, and it gave that back through the OTHER cars it won and lost: its sharper level wins more cars on dear
days and in dear weeks, when drivers are short. Version 7's slow book is a brake that the drivers need.

So here version 7's book stays in charge, untouched: it makes every quote and learns as it always did (it is told
the answer its own price would have had). The new book listens to the same answers, and a quote is raised to the
highest price that the new book still gives `sure` chance of a yes. A raise can only lose a car version 7 would
have won, never win one it would not: the cars are version 7's, less a few, at a better price."""
from __future__ import annotations

import math

from alt.ld_price_core import SharpBook, sig
from dispatch.desk import Desk
from dispatch.geo import DAY, Geo
from dispatch.policy import OPTION_VALUE, Params, Policy


class HybridPolicy(Policy):
    def __init__(self, params: Params, places: dict[str, tuple[float, float]], sure: float, cfg: dict | None = None):
        super().__init__(params)
        self.sharp = SharpBook(places, self.trusted, cfg)
        self.sure = sure
        self.own: dict[str, dict[str, float]] = {}  # request id -> option -> the markup version 7's book alone would quote

    def quote(self, desk, request: dict) -> dict[str, int]:
        if request["arrivedAt"] // DAY != self.day:
            self.sharp.new_day()
        return super().quote(desk, request)

    def markup(self, desk, request: dict, option: dict, last: int, keys: list, factor: float = 1.0) -> float:
        m = super().markup(desk, request, option, last, keys, factor)
        self.own.setdefault(request["id"], {})[option["kind"]] = m
        leg = request["legs"][0]
        trust = 1 + 0.01 * self.trusted.get(request["dealerId"], 0)
        comps, s = self.sharp.humps(leg["pickup"]["placeId"], leg["delivery"]["placeId"], request["respondBy"])

        def chance(markup: float) -> float:
            x = math.log(markup / trust)
            return sum(w * sig((c - x) / s) for w, c in comps)

        if chance(m) < self.sure:
            return m
        low, high = m, max(m, self.p.ceiling)
        for _ in range(20):  # the highest price that still has `sure` chance, by halving
            mid = (low * high) ** 0.5
            if chance(mid) >= self.sure:
                low = mid
            else:
                high = mid
        return low

    def observe(self, desk, event: dict) -> None:
        if event["kind"] in ("order_won", "order_lost"):
            won = event["kind"] == "order_won"
            rid = event["order"]["id"] if won else event["requestId"]
            actual, own, request = self.quoted.get(rid), self.own.pop(rid, None), desk.requests.get(rid)
            if actual and request:  # the new book hears the level this quote beat under the dealers' option rule
                trust = 1 + 0.01 * self.trusted.get(request["dealerId"], 0)
                listed = {o["kind"]: o["listPriceCents"] for o in request["options"]}
                ours = max(OPTION_VALUE[kind] - markup * listed[kind] / trust for kind, markup in actual.items())
                beaten = trust * max((OPTION_VALUE[kind] - ours) / cents for kind, cents in listed.items())
                leg = request["legs"][0]
                self.sharp.learn_at(request["dealerId"], leg["pickup"]["placeId"], leg["delivery"]["placeId"], request["respondBy"], beaten, won)
            if actual and own:
                if won:  # version 7's own, lower price would have won too: its book hears exactly that
                    self.quoted[rid] = {kind: own.get(kind, markup) for kind, markup in actual.items()}
                elif any(actual[kind] > own.get(kind, actual[kind]) * 1.0001 for kind in actual):
                    self.quoted.pop(rid, None)  # a raised price that lost says nothing sure about version 7's own price
                    self.keys.pop(rid, None)
        super().observe(desk, event)


def make_with(client, world, level: int, now: int, params: Params, sure: float, cfg: dict | None = None):
    world_map = client.map()
    places = {p["id"]: (p["lat"], p["lon"]) for p in world_map["places"]}
    policy = HybridPolicy(params, places, sure, cfg)
    desk = Desk(world, level, now, policy, Geo(world_map))
    desk.meet(world.roster())
    return desk
