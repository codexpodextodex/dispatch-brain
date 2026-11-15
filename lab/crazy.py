"""A hundred ideas that are far from anything we would tune towards, each played on the same 12 weeks.

    python -m lab.crazy queue      # puts the weeks that are not saved yet in the worker's queue (fast mode)
    python -m lab.crazy            # the table: every idea against the current version on the same weeks

Emil's ask (Sat 11:50): "try some crazy ideas, like paying the drivers almost nothing; come up with 100".
Most of them should lose: the point is to find the one or two that do not, and to know what the world punishes.
The screen is 4 hard weeks and 8 ordinary ones in fast mode (lab_step=12), which is coarse but shows any effect
of a thousand euros a week. What survives goes to all 60 weeks in exact mode."""
from __future__ import annotations

import statistics as st
import sys

from lab.runs import load

HARD = ["fresh-9", "fresh-12", "hold-10", "hold-2"]
EASY = ["lab-1", "lab-3", "lab-5", "hold-3", "hold-5", "fresh-1", "fresh-3", "fresh-7"]
FAST = {"lab_step": 12}

IDEAS: list[tuple[str, str, dict]] = [
    # --- pay the drivers as little as possible
    ("fees", "open every gig at 30% of the typical fee", {"open_fee": 0.3}),
    ("fees", "open at 50%", {"open_fee": 0.5}),
    ("fees", "open at 60%", {"open_fee": 0.6}),
    ("fees", "open at 70%", {"open_fee": 0.7}),
    ("fees", "open at 75%", {"open_fee": 0.75}),
    ("fees", "open at 50% and never above 80% before the warning", {"open_fee": 0.5, "top_fee": 0.8}),
    ("fees", "never pay more than the typical fee, whatever happens", {"top_fee": 1.0, "late_fee": 1.0, "urgent_top": 1.0, "late_top": 1.0}),
    ("fees", "pay almost nothing: 40% rising to 70%, rescue at 100%", {"open_fee": 0.4, "top_fee": 0.7, "late_fee": 1.0, "urgent_top": 1.2}),
    ("fees", "open at 60% and hold it most of the time", {"open_fee": 0.6, "hold": 0.8}),
    ("fees", "top fee at the typical fee", {"top_fee": 1.0}),
    ("fees", "cheap rescue: late fee 1.2, ceiling 1.4", {"late_fee": 1.2, "urgent_top": 1.4}),
    ("fees", "two hours at 40%, then as usual", {"teaser_fee": 0.4, "teaser_minutes": 120}),
    ("fees", "45 minutes at 60%, then as usual", {"teaser_fee": 0.6}),
    ("fees", "20 minutes at 50%, then as usual", {"teaser_fee": 0.5, "teaser_minutes": 20}),
    ("fees", "no fee under 30 euros", {"fee_floor": 3000}),
    ("fees", "pairs at 60% of two fees", {"pair_fee": 0.6}),
    ("fees", "pairs at 50%", {"pair_fee": 0.5}),
    ("fees", "pairs at 70%", {"pair_fee": 0.7}),
    # --- or pay them well
    ("fees", "pay the typical fee at once, flat", {"open_fee": 1.0, "top_fee": 1.0}),
    ("fees", "pay 120% at once", {"open_fee": 1.2, "top_fee": 1.2}),
    ("fees", "open at 100%, top 140%", {"open_fee": 1.0, "top_fee": 1.4}),
    ("fees", "open at 95%", {"open_fee": 0.95}),
    ("fees", "pay anything to save a car: late fee 2.5, ceiling 4", {"late_fee": 2.5, "urgent_top": 4.0}),
    ("fees", "a car past saving is paid 60%, then 90%", {"late_open": 0.6, "late_top": 0.9}),
    ("fees", "the old steep ladder for a car past saving", {"late_open": 0.0}),
    # --- when the fee moves
    ("timing", "rise only at the hours drivers plan (06:30, 17:00)", {"schedule": "plan"}),
    ("timing", "top fee 12 hours before the last pickup", {"lead_hours": 12.0}),
    ("timing", "top fee 3 hours before", {"lead_hours": 3.0}),
    ("timing", "start rising at once", {"hold": 0.0}),
    ("timing", "hold the opening fee 80% of the time", {"hold": 0.8}),
    ("timing", "every car gets its top fee on the evening before", {"early_hour": 24.0, "early_long": 24.0}),
    ("timing", "no car gets a top fee on the evening before", {"early_hour": 0.0, "early_long": 0.0}),
    ("timing", "late fee 6 hours before the last pickup", {"late_lead": 6.0}),
    ("timing", "raise at night too", {"night_hold": 0}),
    ("timing", "no raise at the weekend", {"weekend_hold": 1}),
    ("timing", "the evening before starts at 15:00", {"evening_hour": 15.0}),
    ("timing", "the evening before starts at 20:00", {"evening_hour": 20.0}),
    ("timing", "long drives: late fee 12 hours ahead, from 7 hours of drive", {"long_lead": 12.0, "long_hours": 7.0}),
    # --- prices
    ("price", "price for volume: cost 0.8", {"cost": 0.8}),
    ("price", "cost 0.6", {"cost": 0.6}),
    ("price", "cost 0.9", {"cost": 0.9}),
    ("price", "price for margin: cost 1.2", {"cost": 1.2}),
    ("price", "cost 1.5", {"cost": 1.5}),
    ("price", "boutique: cost 2.0", {"cost": 2.0}),
    ("price", "never under 30% over cost", {"min_margin": 0.3}),
    ("price", "never under 60% over cost", {"min_margin": 0.6}),
    ("price", "believe dealers answer sharply (spread 0.07)", {"spread": 0.07}),
    ("price", "believe dealers answer loosely (spread 0.25)", {"spread": 0.25}),
    ("price", "start the week at 1.5 list prices", {"start_level": 1.5}),
    ("price", "start the week at the list price", {"start_level": 1.0}),
    ("price", "learn the level three times as fast", {"market_rate": 0.1, "dealer_rate": 0.1, "lane_rate": 0.1}),
    ("price", "learn it three times as slowly", {"market_rate": 0.01, "dealer_rate": 0.01, "lane_rate": 0.01}),
    ("price", "same day costs 15% more", {"same_day_premium": 0.15}),
    ("price", "same day costs 10% less", {"same_day_premium": -0.1}),
    ("price", "never quote above 1.6 list prices", {"ceiling": 1.6}),
    ("price", "a level for each delivery option", {"option_rate": 0.04}),
    ("price", "no level by town", {"lane_rate": 0.0}),
    ("price", "a level by pickup town and by route", {"pickup_rate": 0.04, "route_rate": 0.04}),
    ("price", "price by the dealers' option rule", {"menu": 1}),
    ("price", "learn from the dealers' option rule", {"menu": 2}),
    ("price", "a new price book each morning", {"book": "day"}),
    ("price", "a new price book each morning at cost 1.2", {"book": "day", "cost": 1.2}),
    ("price", "the outage detector at 2 standard errors", {"outage": 2.0}),
    ("price", "buy the big dealers' trust: full value off the cost", {"trust_gain": 1.0}),
    ("price", "a round-trip partner is worth 0.3 fees off the cost", {"pair_bonus": 0.3}),
    ("price", "charge by the driver's hours (20 euros an hour), half the fee cost", {"hour_cost": 20.0, "fee_share": 0.5}),
    # --- which cars
    ("cars", "take every car with 6 hours to find a driver", {"min_find_hours": 6.0}),
    ("cars", "take every car with 3 hours, easy ones with 2", {"min_find_hours": 3.0, "easy_find_hours": 2.0}),
    ("cars", "only cars with a full day to find a driver", {"min_find_hours": 24.0, "easy_find_hours": 0.0}),
    ("cars", "only cars with 40 hours", {"min_find_hours": 40.0, "easy_find_hours": 0.0}),
    ("cars", "easy cars with 2 hours", {"easy_find_hours": 2.0}),
    ("cars", "easy means up to 4 hours of drive, from towns with 30 drivers", {"easy_drive_hours": 4.0, "easy_drivers": 30}),
    ("cars", "premium cars too, at no extra cost", {"premium": 1}),
    ("cars", "premium cars at half a fee more", {"premium": 1, "cost_premium": 0.5}),
    ("cars", "trade-ins at half a fee more", {"trade_in": 1, "cost_trade_in": 0.5}),
    ("cars", "trade-ins at a whole fee more", {"trade_in": 1, "cost_trade_in": 1.0}),
    ("cars", "private cars of any drive", {"private_drive_hours": 0.0}),
    ("cars", "private cars only under 1 hour of drive", {"private_drive_hours": 1.0}),
    ("cars", "no private cars", {"private_delivery": 0, "private_pickup": 0}),
    ("cars", "take everything: premium, trade-ins, any private car", {"premium": 1, "trade_in": 1, "private_drive_hours": 0.0}),
    ("cars", "long drives dear (0.3 fees an hour over three)", {"cost_drive": 0.3}),
    ("cars", "long drives at par", {"cost_drive": 0.0}),
    ("cars", "thin towns dear", {"cost_thin": 0.3}),
    ("cars", "no drive over about 5 hours (last pickup from 15:00)", {"min_last_hour": 15.0}),
    ("cars", "city courier: only short drives (last pickup from 17:00)", {"min_last_hour": 17.0}),
    ("cars", "no cap on cars a day", {"day_cap": 0.0}),
    ("cars", "a tight cap on cars a day", {"day_cap": 0.08}),
    ("cars", "a loose cap on cars a day", {"day_cap": 0.2}),
    ("cars", "short notice costs extra by the hour", {"min_find_hours": 6.0, "cost_short": 0.05}),
    # --- the brake
    ("brake", "no brake", {"guard": 0.0}),
    ("brake", "a hair trigger (3%)", {"guard": 0.03}),
    ("brake", "a slow brake (12%)", {"guard": 0.12}),
    ("brake", "a brake that bites three times as hard", {"guard_cost": 1.5}),
    ("brake", "the strain rule", {"strain": 5.0}),
    ("brake", "cheaper prices while the week goes well", {"easy_cost": 0.15}),
    ("brake", "the budget in place of the guard", {"guard": 0.0, "budget": 0.05}),
    ("brake", "the budget with a steep price", {"guard": 0.0, "budget": 0.03, "budget_price": 40.0}),
    ("brake", "risky kinds only when due by Wednesday", {"risky_last_day": 2}),
    # --- pairs and drivers
    ("drivers", "no pairs", {"pairs": 0}),
    ("drivers", "wide pairs (2 hours between, 3 hours back)", {"pair_hop": 120, "pair_back": 180}),
    ("drivers", "tight pairs", {"pair_hop": 30, "pair_back": 45}),
    ("drivers", "a pair waits until 3 hours before its start", {"pair_split_hours": 3.0}),
    ("drivers", "a pair is split a day before", {"pair_split_hours": 24.0}),
    ("drivers", "morning rescue at 06:00 at 1.3 fees", {"rescue_hour": 6.0, "rescue_fee": 1.3}),
    ("drivers", "flu-day rescue", {"flu": 1, "rescue_fee": 1.3}),
    ("drivers", "start again at 1.3 fees after a drop", {"drop_rescue": 1.3}),
    ("drivers", "direct offers 6 hours before the last pickup", {"offer_lead": 6.0}),
    ("drivers", "offer a waiting car to the driver who just delivered nearby", {"chain_fee": 0.8}),
    ("drivers", "pickup windows end half an hour early", {"pickup_buffer": 30.0}),
    ("drivers", "the kit's note reader instead of ours", {"notes": "kit"}),
    # --- whole characters
    ("combo", "sweatshop: fees 50 to 90%, cost 0.7, flood the week", {"open_fee": 0.5, "top_fee": 0.9, "late_fee": 1.2, "urgent_top": 1.5, "cost": 0.7}),
    ("combo", "luxury: fees 110 to 140%, cost 1.3", {"open_fee": 1.1, "top_fee": 1.4, "cost": 1.3}),
    ("combo", "courier: short drives only, cost 0.9, fees from 80%", {"min_last_hour": 16.0, "cost": 0.9, "open_fee": 0.8}),
    ("combo", "volume with everything in: cost 0.85, 8 hours notice, premium, any private car", {"cost": 0.85, "min_find_hours": 8.0, "premium": 1, "private_drive_hours": 0.0}),
    ("combo", "flat and generous: fee 100% flat, cost 1.1", {"open_fee": 1.0, "top_fee": 1.0, "cost": 1.1}),
    ("combo", "low fees paid for by a hair trigger: open 70%, guard 3%", {"open_fee": 0.7, "guard": 0.03}),
    ("combo", "low fees with the budget: open 70%, budget 5%", {"open_fee": 0.7, "guard": 0.0, "budget": 0.05}),
    ("combo", "cheap pairs and wide: 60%, 2 hours between", {"pair_fee": 0.6, "pair_hop": 120, "pair_back": 180}),
]


def queue() -> None:
    from lab.sweep import enqueue
    n = 0
    for seed in HARD + EASY:
        n += enqueue(8, seed, FAST, 0)
    for _, _, setting in IDEAS:
        for seed in HARD + EASY:
            n += enqueue(8, seed, {**setting, **FAST}, 0)
    print(f"{len(IDEAS)} ideas, {n} weeks queued")


def table() -> None:
    base = {s: load(8, s, FAST) for s in HARD + EASY}
    rows = []
    for group, name, setting in IDEAS:
        runs = {s: load(8, s, {**setting, **FAST}) for s in HARD + EASY}
        both = [s for s in HARD + EASY if runs[s] and base[s]]
        if len(both) < 6:
            rows.append((None, group, name, len(both)))
            continue
        g = [(runs[s]["score"]["marginCents"] - base[s]["score"]["marginCents"]) / 100 for s in both]
        hard = [s for s in both if s in HARD]
        rows.append((st.mean(g), group, name, len(both), st.stdev(g) / len(g) ** 0.5, st.mean(runs[s]["score"]["wonOrders"] - base[s]["score"]["wonOrders"] for s in both),
                     st.mean(runs[s]["score"]["onTimeShare"] for s in both), st.mean([runs[s]["score"]["onTimeShare"] for s in hard] or [0]), min(runs[s]["score"]["onTimeShare"] for s in both),
                     -sum(runs[s]["ledger"].get("driver_fee", 0) for s in both) / max(1, sum(runs[s]["stats"].get("won_typical", 0) for s in both))))
    done = sorted((r for r in rows if r[0] is not None), reverse=True)
    b = [base[s] for s in HARD + EASY if base[s]]
    if b:
        print(f"the current version in fast mode on these weeks: {st.mean(x['score']['marginCents'] for x in b) / 100:,.0f} a week, {st.mean(x['score']['wonOrders'] for x in b):.0f} cars, "
              f"on time {st.mean(x['score']['onTimeShare'] for x in b):.1%}, fees {-sum(x['ledger'].get('driver_fee', 0) for x in b) / max(1, sum(x['stats'].get('won_typical', 0) for x in b)):.2f} typical")
    print(f"{'gain':>7} {'±':>5} {'wks':>3} {'cars':>6} {'on time':>7} {'4 hard':>7} {'lowest':>7} {'fee':>5}  idea")
    for gain, group, name, n, err, cars, share, hard, low, fee in done:
        print(f"{gain:+7.0f} {err:5.0f} {n:3} {cars:+6.0f} {share:7.1%} {hard:7.1%} {low:7.1%} {fee:5.2f}  [{group}] {name}")
    waiting = [r for r in rows if r[0] is None]
    if waiting:
        print(f"\nnot played yet: {len(waiting)} ideas")


if __name__ == "__main__":
    queue() if len(sys.argv) > 1 and sys.argv[1] == "queue" else table()
