"""leaders/bulk: price every request again while its 15 minutes run, with what the answers since have taught.

The rules: "A new quote for the same request replaces the earlier one", and the dealer decides at the response
deadline on the last quote. Version 7 quotes the minute a request arrives and never looks again, so its price
knows the answers to requests that came 15 minutes or more before it. Requests come in runs (a bulk order sends
35 from one dealer in 100 minutes; a morning's first answers arrive at 08:15), and by the time a request is
decided the book has seen five more answers than when it was priced.

Each time the desk is awake (the lab wakes it on every request and every win), it prices the requests that
are still open again and sends a new quote when a price has moved by 0.2% or more. Replayed against the
dealers' measured limits a quote held to two minutes before its answer earns +142 +- 48 a week at the same
number of cars (leaders/bulk/s4_price.py).

Not for the final as it stands: after a restart `relearn` rebuilds the first quote of each past request, not
the last, so the book would learn from prices up to a few percent off. The rest is version 7."""
from __future__ import annotations

from dispatch.desk import Desk
from dispatch.geo import Geo
from dispatch.policy import Params, Policy

MOVE = 0.002  # a new quote goes out when a price has moved by this share


class RequoteDesk(Desk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.waiting: dict[str, int] = {}  # request id -> its response deadline, while the dealer has not decided

    def quote(self, request: dict) -> None:
        super().quote(request)
        self.waiting[request["id"]] = request["respondBy"]

    def handle(self, event: dict) -> None:
        super().handle(event)
        if event["kind"] == "order_won":
            self.waiting.pop(event["order"]["id"], None)
        elif event["kind"] == "order_lost":
            self.waiting.pop(event["requestId"], None)

    def tick(self) -> None:
        super().tick()
        policy = self.policy
        for request_id, respond_by in list(self.waiting.items()):
            request = self.requests.get(request_id)
            if respond_by <= self.now or request is None:  # the world refuses a quote at the deadline or later
                del self.waiting[request_id]
                continue
            if request["arrivedAt"] >= self.now or request["arrivedAt"] // 1440 != policy.day:
                continue  # priced in this very minute; or a request of yesterday (never open that long)
            before = (policy.quoted.pop(request_id, None), policy.keys.pop(request_id, None), policy.hoped.pop(request_id, None))
            asked = policy.asked.get(request["dealerId"], 0)
            prices = policy.quote(self, request)
            policy.asked[request["dealerId"]] = asked  # a second look is not a second request
            old = self.asked.get(request_id)
            if old is not None and set(old) == set(prices) and all(abs(prices[kind] - old[kind]) < MOVE * old[kind] for kind in prices):
                for book, value in zip((policy.quoted, policy.keys, policy.hoped), before):  # the old quote stands: remember it as it was
                    book.pop(request_id, None)
                    if value is not None:
                        book[request_id] = value
                continue
            self.asked[request_id] = prices
            self.outbox.append({"type": "quote", "requestId": request_id, "prices": prices})
            self.stats["requotes"] += 1


def make(client, world, level: int, now: int, params: Params):
    desk = RequoteDesk(world, level, now, Policy(params), Geo(client.map()))
    desk.meet(world.roster())
    return desk
