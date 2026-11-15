"""How well does the price book predict the dealers' answers? Replays the quotes of saved weeks, in order.

    python -m lab.price_eval --set notes=ours day_cap=0.11 ...        # the saved weeks of one setting
    python -m lab.price_eval --set ... --grid spread=0.1,0.14 market_rate=0.03,0.06

For each quote we made, the book says the chance that the dealer accepts it, before it learns the answer. The
script prints how often the dealer really accepted, by that chance, and the log loss (lower is better). So the
book's own settings are chosen for how well they predict, on quotes it has never used, and not for the margin
on the test weeks."""
from __future__ import annotations

import argparse
import itertools
import math

from dispatch.pricing import PriceBook, chance
from lab.runs import KINDS, REVEALS, load, read_gz
from lab.sweep import seeds


def quotes(reveal: dict) -> list[dict]:
    """Our real quotes of a week: when asked, when answered, dealer, the markup that the answer speaks to, and the answer."""
    out = []
    for answer in reveal["requests"]:
        request, quote = answer["request"], answer["quote"]
        if not quote:
            continue
        lists = {o["kind"]: o["listPriceCents"] for o in request["options"]}
        markups = {kind: price / lists[kind] for kind, price in quote.items() if kind in lists}
        if not markups or min(markups.values()) >= 3.5:  # a decline
            continue
        won = answer["outcome"] == "won"
        markup = markups[answer["option"]] if won and answer["option"] in markups else min(markups.values())
        fastest = next(o["kind"] for o in request["options"] if o["kind"] in markups)
        keys = [("dealer", request["dealerId"]), ("to", request["legs"][0]["delivery"]["placeId"]), ("option", fastest)]
        out.append({"asked": request["arrivedAt"], "answered": request["respondBy"], "keys": keys, "markup": markup, "won": won})
    return sorted(out, key=lambda q: q["asked"])


def replay(week: list[dict], start: float, spread: float, rates: dict[str, float]) -> list[tuple[float, bool, int]]:
    """(predicted chance, answer, minute asked) for each quote, learning each answer only when it arrives."""
    book, pending, out = PriceBook(start, spread, rates), [], []
    for quote in week:
        pending.sort(key=lambda q: q["answered"])
        while pending and pending[0]["answered"] <= quote["asked"]:
            done = pending.pop(0)
            book.learn([k for k in done["keys"] if rates[k[0]]], done["markup"], done["won"])
        out.append((chance(book.level([k for k in quote["keys"] if rates[k[0]]]), quote["markup"], spread), quote["won"], quote["asked"]))
        pending.append(quote)
    return out


def report(label: str, results: list[tuple[float, bool, int]], detail: bool) -> None:
    loss = -sum(math.log(max(1e-6, p if won else 1 - p)) for p, won, _ in results) / len(results)
    print(f"{label:<64} quotes {len(results):6}  log loss {loss:.4f}  won {sum(w for _, w, _ in results) / len(results):.1%}  predicted {sum(p for p, _, _ in results) / len(results):.1%}")
    if not detail:
        return
    print("    predicted -> happened, by tenth of the predicted chance:")
    for low in range(10):
        group = [(p, won) for p, won, _ in results if low / 10 <= p < (low + 1) / 10 or (low == 9 and p == 1)]
        if group:
            print(f"      {low * 10:3}-{low * 10 + 10:<3}%  {len(group):6} quotes  predicted {sum(p for p, _ in group) / len(group):5.1%}  happened {sum(w for _, w in group) / len(group):5.1%}")
    print("    happened minus predicted, by hour of the day:  " + "  ".join(
        f"{hour:02d}h {sum(won - p for p, won, at in results if at % 1440 // 60 == hour) / max(1, sum(1 for _, _, at in results if at % 1440 // 60 == hour)):+.2f}" for hour in range(8, 19)))
    print("    happened minus predicted, by weekday:  " + "  ".join(
        f"{day} {sum(won - p for p, won, at in results if at // 1440 == i) / max(1, sum(1 for _, _, at in results if at // 1440 == i)):+.2f}" for i, day in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri"])))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--set", nargs="*", default=[], metavar="NAME=VALUE", help="the setting whose saved weeks to replay")
    parser.add_argument("--grid", nargs="*", default=[], metavar="NAME=V1,V2", help="settings of the book to compare: start_level spread market_rate dealer_rate lane_rate option_rate")
    parser.add_argument("--seeds", type=int, default=10)
    args = parser.parse_args()
    changed = {k: KINDS[k](v) for k, v in (item.split("=", 1) for item in args.set)}
    weeks = {family: [quotes(read_gz(REVEALS / f"{run['worldId']}.json.gz")) for seed in seeds(args.seeds, family) if (run := load(8, seed, changed))] for family in ("lab", "hold")}
    book_settings = ("start_level", "spread", "market_rate", "dealer_rate", "lane_rate", "option_rate")
    base = {"start_level": 1.15, "spread": 0.09, "market_rate": 0.03, "dealer_rate": 0.03, "lane_rate": 0.0, "option_rate": 0.0, **{k: changed[k] for k in book_settings if k in changed}}
    names = [item.split("=", 1)[0] for item in args.grid]
    values = [[float(v) for v in item.split("=", 1)[1].split(",")] for item in args.grid]
    for combo in itertools.product(*values):
        book = {**base, **dict(zip(names, combo))}
        for family in ("lab", "hold"):
            rates = {"market": book["market_rate"], "dealer": book["dealer_rate"], "to": book["lane_rate"], "option": book["option_rate"]}
            results = [r for week in weeks[family] for r in replay(week, book["start_level"], book["spread"], rates)]
            if results:
                label = f"{family:5} " + ", ".join(f"{k}={v}" for k, v in book.items())
                report(label, results, detail=not args.grid)


if __name__ == "__main__":
    main()
