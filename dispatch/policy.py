"""The two decisions of the desk: which price to quote for a request, and which fees to post for an order.

Everything else (posting, retries, restarts) is plumbing in desk.py."""
from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from . import risk
from .geo import DAY, HOUR, PLATES_MINUTES, last_pickup, last_private_pickup, neighbours
from .notes import apply
from .pricing import DayBook, PriceBook, chance

if TYPE_CHECKING:
    from .desk import Desk

VERSION = 11  # raise it when the decisions change, so the lab plays its saved weeks again
# A line through 18,043 typical fees of plain cars against road minutes: 16.04 euros and 38.44 cents a minute.
# Two separate fits of saved weeks agree on it (15.7 and 38.6), and it is the world's rule, the same in every week.
LANES = Path(__file__).with_name("lanes.json")  # log offsets of the dealers' level by lane, from earlier worlds (see `lane_prior`)
ROAD_BASE, ROAD_MINUTE = 1604, 38.44
# What a faster delivery is worth to a dealer, in cents, fitted on a million of our quotes and their answers (sim/dealers.py).
OPTION_VALUE = {"same_day": 2350, "next_day": 750, "within_3_days": 0}


@dataclass(frozen=True)
class Params:
    guard: float = 0.08  # when more than this share of our cars so far is late or about to be, the desk turns careful; 0 is off
    guard_kinds: int = 0  # 1: once careful, the brake prices out only the kinds that are late in the hard weeks (version 9, eight hardest
    # weeks): an end where few drivers live within 30 km AND within 60 km (9.8% late), a drive over five hours (19.1%), a last pickup before
    # 13:00 (22.8%). Not a thin town beside the capital (Hyvinkää, Porvoo: 1.1% late, 66 cars a week) and not a private address (3.9%)
    guard_after: int = 0  # 1: the brake leaves a car due after Friday alone: it has the weekend to find its driver (late 2.9%)
    guard_once: int = 0  # 1 counts each warned car once. The world repeats a deadline warning when a car's gig runs out (19.9 warnings for
    # 11.5 cars a week), and without this the guard counts the car again: two thirds of its careful time (leaders/api/AUDIT.md)
    guard_cost: float = 0.5  # ... a car at risk then costs this many typical fees more,
    easy_cost: float = 0.0  # typical fees off the cost of every car while the week goes well (see `Policy.relaxed`); 0 is off
    flu: int = 0  # 1 watches for the flu day (drivers give back that day's bookings just after midnight) and raises that day's open gigs early; 2 raises only the long drives (`long_hours` or more)
    rescue_hour: float = 0.0  # at this hour on the day of a car's last pickup, a gig that still has no driver goes up at once; 0 is off
    rescue_fee: float = 1.5  # ... to this many typical fees, climbing to the late fee by the deadline warning. With `guard` set, only in a careful week
    long_lead: float = 0.0  # for a long drive the fee reaches the late fee this many hours before the last pickup; 0 treats it like any car
    long_hours: float = 5.0  # ... a long drive: at least this many hours
    guard_lead: float = 6.0  # ... and a gig's fee reaches the late fee this long before the last pickup
    menu: int = 0  # 1 prices a quote by the dealers' measured rule for choosing between delivery options (see `Policy.menu`); 2 only learns by it
    design: str = ""  # the lab only: the name of a module in alt/ whose desk plays the week instead of this one
    lab_step: int = 0  # the lab only: 12 answers the events of every 12 minutes together, four times as fast; the final ignores it
    # Which cars we try to win.
    min_find_hours: float = 14.0  # quote an option only when at least this long remains to find a driver
    min_last_hour: float = 0.0  # quote an option only when its last pickup is at or after this hour of the day
    private_drive_hours: float = 2.0  # off at 0; a car with a private address at either end is quoted only when its drive is shorter than this
    private_delivery: int = 1  # 1 also quotes cars that go to a private address, at its booked hour
    premium: int = 0  # 1 also quotes premium cars; only an experienced driver may move one
    private_after: int = 0  # 1 quotes a private address with a drive of `private_drive_hours` or more on an option whose last pickup falls
    # after Friday: the appointment has the weekend to be arranged
    trade_hour: int = 1  # 1: trade-ins (new car out to a customer, the old car back) are quoted and posted by the customer's hour:
    # dispatch/trade.py. 0 declines them, as up to version 10. With the hour as the delivery's window they are on time 84% of the
    # time instead of 55% (EXPERIMENTS.md 74)
    premium_after: int = 1  # 1 quotes a premium car on an option whose last pickup falls after Friday: there the few experienced drivers
    # have the weekend to take it, where on a weekday it is late 9 to 15% of the time. With trade_hour: +338 ± 90 a week on 80 weeks,
    # +471 ± 204 on the 20 of them that were never tuned on, no week under 90% (EXPERIMENTS.md 74)
    trade_in: int = 0  # 1 also quotes trade-ins: the new car out and the old car back, one gig
    private_pickup: int = 1  # 1 also quotes cars that wait at a private seller, to be collected in the seller's slot
    private_find_hours: float = 3.0  # ... when at least this long remains to find a driver: the slot is hours away by its nature
    budget: float = 0.0  # the delivery minimum as a budget. The desk keeps a forecast of the week's on-time share, with one bad day
    # still to come, and this is the headroom over 90% under which a car's chance to come late starts to cost extra; 0 is off
    budget_price: float = 15.0  # ... with no headroom left, a car costs this many typical fees for a certain late arrival, pro rata
    late_cost: float = 1.5  # what a late car costs us in any week (refund, and the dealer's trust halves), in typical fees
    risky_last_day: int = -1  # the kinds of car that come late more often (premium, a private address) are quoted only on an option whose
    # last pickup falls on this day of the week or earlier (0 Monday): a bad day late in the week cannot be repaired, one early can.
    # -1 has no such limit
    easy_find_hours: float = 4.0  # a shorter time to find a driver is enough for an easy car; 0 has no such exception
    easy_drive_hours: float = 2.0  # an easy car: at most this much driving,
    easy_drivers: int = 100  # from a town with at least this many drivers within 30 km
    decline: float = 4.0  # a quote this far above the list price says no; a quote that loses costs nothing
    quote_ready_shift: int = 0  # account for the days the dealer shifts its deadline on a delayed handover
    notes: str = "ours"  # "ours" reads the dealer's note with notes.py; "kit" keeps the starter's keyword match
    # The price: the best expected margin against the level that the dealer accepts (pricing.py).
    start_level: float = 1.15  # the level we assume before the first answer, in list prices
    dealer_calibration: float = 0.0  # 1 calibrates the current book against public dealer history
    spread: float = 0.14  # how fast the chance to win falls as the price rises
    market_rate: float = 0.03  # how far one answer moves the market level
    dealer_rate: float = 0.03  # how far one answer moves its dealer's offset
    small_rate: float = 0.0  # ... the one offset shared by every dealer outside the four that send most requests. Each of those
    # dealers sends about 12 requests a week, too few for an offset of its own, while the market level follows the big four, whose
    # acceptance rises with every order we deliver them: by Thursday we win 51% of the big four's quotes and 36% of the others'
    # (version 11, 80 weeks; both 44% on Monday). 0 keeps no such offset
    lane_rate: float = 0.04  # ... the offset of the town the car goes to; 0 keeps no such offset
    option_rate: float = 0.0  # ... the offset of the fastest delivery option we quote
    hour_cost: float = 0.0  # euros for each hour a car takes a driver, the trips to the car and home included; 0 is off
    fee_share: float = 1.0  # with `hour_cost`: the share of the fee-based cost that stays
    trust_gain: float = 0.0  # how much of what an on-time delivery adds to a dealer's later prices comes off a car's cost; 0 is off
    pair_bonus: float = 0.0  # typical fees off the cost of a car that would make a round trip with one of ours that waits for a driver
    outage: float = 0.0  # how far (in standard errors) one region's answers of today must stand above the rest before we call an outage there; 0 is off
    outage_lift: float = 0.28  # what dealers in an outage region accept more, measured with fork (0.26 to 0.38)
    outage_km: int = 80  # the reach of an outage around its centre
    pickup_rate: float = 0.0  # ... the offset of the town the car comes from
    lane_prior: float = 0.0  # how much of what earlier worlds taught about each lane the price book knows from the first minute (lanes.json,
    # log offsets by route, pickup town and delivery town): the handbook says part of the competitor's price on a lane is the same in
    # every world. 0 is off, 1 takes the table as it is
    lane_table: str = "lanes"  # ... the table's file in dispatch/, without .json
    route_rate: float = 0.0  # ... the offset of the pair of towns: within a week, cars on one route sell alike
    book: str = "market"  # "day" starts each working day afresh: the dealers' level is one level a day (pricing.DayBook)
    day_level: float = 1.38  # the level a day book expects on its first morning, in list prices
    book_noise: float = 0.065  # how much two requests of one day differ, for the day book
    book_prior: float = 0.18  # how far a day's level can lie from what the week has shown, for the day book
    menu_strength: float = 0.0  # 1 uses the measured effect of omitting the fastest requested option
    cost: float = 1.0  # what a won car costs us, in typical fees: the driver's fee and the risk of a refund
    cost_drive: float = 0.08  # more cost for each hour of driving over three, in typical fees
    cost_thin: float = 0.0  # more cost where few drivers live near the delivery or the pickup, in typical fees
    thin_km: int = 30  # "near" for that count: the app notifies within 30 km; drivers come from further
    snow_cost: float = 0.0  # extra typical fees for a pickup day exposed to a published forecast
    cap_thin: int = 0  # 1 lets the cap on cars due per day count, and slow, only the cars with few drivers near them
    fee_floor: int = 0  # no fee step under this many cents: a tiny typical fee is less than any driver takes
    trust: int = 0  # 1 moves a dealer's level by 1% for each on-time order, as the rules say the dealer does
    same_day_premium: float = 0.0  # this much more for the same-day option when we also quote a later one
    cost_short: float = 0.0  # more cost for each hour under 14 that is left to find a driver, in typical fees
    cost_private: float = 0.0  # more cost for a delivery to a private address, in typical fees
    cost_premium: float = 0.0  # more cost for a premium car: few drivers are experienced
    cost_private_pickup: float = 0.2  # more cost for a pickup at a private seller: evening work, and a slot to keep
    cost_trade_in: float = 0.0  # more cost for a trade-in
    day_cap: float = 0.11  # cars due on one day, per driver in the list, at which a new car costs us double; 0 is off
    reserve_chosen_day: int = 0  # reserve a pending quote on the pickup day of the service the dealer is likeliest to choose
    cap_power: float = 4.0  # how sharply the cost rises towards the cap
    fill_cut: float = 0.0  # a car costs up to this share less while its due day is behind its pace: a day's cars are won on the day
    # before it, and a day that lags (Tuesday after a cold Monday: 54 cars against a cap of 88) has idle drivers; 0 is off
    fill_target: float = 0.85  # ... the pace is that of a day that ends at this share of the cap
    cap_monday: float = 1.0  # the cap for cars whose last pickup falls after Friday is this many times the usual one: they are the
    # safest cars we carry, but without any cap the extra ones thin the hard weeks (+235 a week, three times the risk)
    cap_week_only: int = 1  # 1: no cap for cars whose last pickup falls after Friday. No new requests come after Friday, so nothing competes
    # for the drivers of the Monday after, and its cars have the weekend to be booked: they are the best we carry (57 euros a car, 1.6% late)
    # and the cap held them to a weekday's number (+416 ± 64 a week on 60 weeks, +256 ± 106 on 20 unseen ones; EXPERIMENTS.md 67)
    cap_after_hours: float = 0.0  # a drive of this many hours or more keeps the day cap after Friday too: long cars are late by how many long
    # cars share the day (150 euros and more, due after Friday: 6.3% late with the cap, 12.5% without); 0 lifts the cap for every car
    cap_long: float = 0.0  # with cap_after_hours: such a long car, due after Friday, is charged by the long cars due that day alone, against
    # this share of the drivers' number (0.02 is two long cars per 100 drivers); 0 charges it by every car due that day, as before Friday
    cap_easy: float = 0.0  # the cap while the week goes well (see `Policy.relaxed`): in a week of few listed drivers the cap alone decides how many
    # cars we carry (0.55 a driver in 33 of 60 weeks, at the usual on-time share), so a clean week can carry more; 0 keeps day_cap
    strain: float = 0.0  # how much dearer a new car gets for each point of our cars that lately had no driver in time; 0 is off
    min_margin: float = 0.05  # never quote below cost plus this share
    ceiling: float = 3.0
    # The fee schedule of a gig, in typical fees. It opens low, reaches `top_fee` by the time drivers plan
    # the day of the last pickup, and `late_fee` when the deadline warning comes, 3 hours before the last pickup.
    open_fee: float = 0.85
    teaser_fee: float = 0.0  # a lower fee for the first minutes of a gig, when most drivers look at it; 0 has none
    teaser_minutes: int = 45
    top_fee: float = 1.2
    late_fee: float = 1.8
    hold: float = 0.3  # the share of the time to the top fee that the opening fee stands
    road_fee_blend: float = 1.0  # how much of the typical fee's noise to take out of a gig's fees: 0 none, 1 all (see `steady`)
    premium_fee_line: int = 0  # use bounded road costs for fees on a weekend-due single premium car
    steady_private: int = 0  # 1: a car with a private address whose typical fee was drawn under the road line is paid by the line:
    # such a private delivery came late 10% of the time against 3% for the rest (leaders/kinds)
    road_cost_blend: float = 1.0  # the same for the cost a price is built on
    late_lead: float = 3.0  # the late fee comes this long before the last pickup. The world warns at 3 hours, but a driver booked
    # that late arrives the next day three times in four. Above 3, a moment in the night moves to the evening before
    lead_hours: float = 6.0  # the top fee comes this long before the last pickup,
    early_hour: float = 13.0  # or, when the last pickup is before this hour, on the evening before,
    early_long: float = 15.0  # ... and for a long drive (`long_hours` or more) before this hour: such a trip fills a driver's day, so it is
    # planned the day before even when the pickup is after lunch; 0 uses early_hour
    thin_evening_floor: float = 0.0  # a single car with a last pickup before 15:00 and fewer than ten drivers near an end shows at least
    # this many typical fees from 17:00 on the day before, while it has no driver (Astra: such cars still open then are late 20 to 40%); 0 is off
    evening_hour: float = 17.0  # at this hour: a driver for a morning pickup plans it the day before
    schedule: str = "ramp"  # "ramp": rise evenly to the top fee; "plan": rise only at the hours when drivers plan their day
    plan_hours: str = "6.5,17"  # those hours: early morning and late afternoon, when most bookings happen
    plan_lead_hours: float = 5.0  # the last planning hour that still counts is this long before the last pickup
    mid_fee: float = 1.0  # the fee one planning hour before the last one that counts
    home_open: float = 0.75  # the opening fee of a plain car that goes where drivers live: a driver on the way home has no trip back to pay
    # for (on the same cars 0.75 pays 0.05 typical fees less than 0.85 with as many on time; leaders/fees); 0 keeps open_fee
    cost_after: float = 0.0  # typical fees off the cost of a car whose last pickup falls after Friday: such a car has the weekend to find its
    # driver, is paid 0.89 typical fees and is late 1.6% of the time (version 9, 80 weeks); 0 is off
    cost_home: float = 0.0  # typical fees off the cost of such a car in the price: it is paid 0.82 typical fees and comes late 1 to 2%
    # of the time, but is priced at the cost of an average car; 0 is off
    home_drivers: int = 30  # ... at least this many drivers live within 30 km of the delivery,
    home_hours: float = 3.0  # ... the drive is shorter than this,
    home_min_fee: int = 2200  # ... and the typical fee is at least this many cents: a small gig gains nothing from a lower fee
    short_ramp: int = 1  # 1: a car won at short notice opens at its usual fee and reaches the top fee in 40 to 80 minutes, instead of opening at the top fee
    open_easy: float = 0.0  # the opening fee for a short drive to a town full of drivers; 0 uses open_fee
    open_hard: float = 0.0  # ... and for a long drive to a town with few; 0 uses open_fee
    night_hold: int = 1  # 1 makes no raise from 22:00 to 06:30: no driver reads a notification at night
    weekend_hold: int = 0  # 1 makes no raise from Saturday noon to Sunday midnight: almost nobody books then
    relane: int = 0  # 1 sets the fees of a car that the dealer sent to another place from the new drive
    # After the deadline warning.
    urgent_step: float = 0.2  # more every half hour
    urgent_top: float = 2.4
    offer_lead: float = 0.0  # hours before the last pickup from which a gig without a driver is offered directly to drivers who looked at it; 0 is off
    chain_fee: float = 0.0  # a driver who has just delivered one of our cars is offered a car of ours that waits nearby, at this many typical fees; 0 is off
    chain_reach: int = 45  # ... nearby: at most this many road minutes from where they delivered to the waiting car
    offer_fee: float = 1.4  # the fee of such an offer, in typical fees (after the deadline warning: the late fee)
    late_by_pickup: int = 1  # 1 also takes the cheap path below once the last pickup has passed: a car whose pickup site has closed for the
    # day cannot be on time either, and 2.5 such cars a week were paid the steep fees (leaders/ontime)
    late_open: float = 1.0  # the first fee for a car that can no longer be on time, in typical fees; 0 keeps the urgent ladder
    late_top: float = 1.3  # ... and where that fee stands a day later
    # Two cars, one driver: a round trip posted as one gig.
    pairs: int = 1  # 1 pairs a new order with an open one when the two make a round trip
    pair_fee: float = 0.8  # the fees of a pair, as a share of the two cars' fees posted alone
    pair_steady: int = 0  # 1: a round trip is paid by its two cars' fees with the draw taken out (`steady`), as a single plain car is,
    # in both directions; pair_road_cap only takes the high draws down
    pair_road_cap: float = 0.0  # high summed reference/road-line ratio above which both ordinary pair legs use bounded road fees; zero leaves pair fees alone
    pair_hop: int = 60  # at most this many minutes of road from the first delivery to the second pickup
    pair_back: int = 90  # ... and from the second delivery back to where the driver started
    pair_urgent_first: int = 0  # a pair may start this many minutes earlier so that the car with the tighter pickup goes first: the second
    # car of a pair is late three times as often as the first (Astra, 2,828 pairs); 0 keeps the order with the latest start
    windows: int = 1  # 1: a single car's pickup window ends at its last pickup (a pair's first pickup: at the pair's last start), so a booked
    # driver who plans to come later says so (`driver_late`), and is released while another can still come (leaders/ontime)
    pair_safe: int = 1  # 1 keeps a booked pair on the desk's list of pairs. Without it a pair that its driver gives back counts as two
    # single gigs: a new order then takes one car out of it and the other is left without any gig (36 cars in 60 weeks; leaders/ontime)
    pair_hold: float = 4.0  # hours a newly won plain car may wait, without a gig, for a round-trip partner among the cars won after it; 0 is off.
    # Half of the round trips that exist are lost because the first car has its driver before the second is won (leaders/routes).
    # With 4 hours a week books 86 round trips instead of 57, on seed families it was and was not tuned on (EXPERIMENTS.md 62)
    hold_after: float = 0.0  # a car due after Friday may wait for its partner until this hour on Friday (0 keeps the 4 hours): its
    # drivers book from Friday afternoon to Monday morning, so the wait costs it no booking
    hold_until: float = 18.0  # ... and never past this hour of the day it was won: the last requests come at 18:00
    hold_spare: float = 16.0  # ... only a car with at least this many hours to its last pickup waits at all,
    hold_drive: int = 180  # ... and at most this many minutes of driving: a long drive held back is booked late
    pair_split_hours: float = 10.0  # a pair that no driver has taken this long before its last start goes back to two gigs
    # Delivery rules from swarm/leader_delivery (all off by default, so saved weeks replay to the cent).
    pickup_buffer: float = 0.0  # minutes, plus 10% of the drive, by which a single car's pickup window ends before lastPickupAt; 0 is off
    drop_rescue: float = 0.0  # after a drop or no-show with >= 4 h to the last pickup, the fees start again at this many typical fees; 0 is off


class Policy:
    def __init__(self, params: Params = Params()):
        self.p = params
        rates = {"market": params.market_rate, "dealer": params.dealer_rate, "to": params.lane_rate, "option": params.option_rate, "from": params.pickup_rate, "route": params.route_rate, "small": params.small_rate,
                 "outage": 0.0}
        self.regions: dict[str, set[str]] = {}  # town -> the towns an outage centred there would reach
        self.outage_towns: set[str] = set()  # the towns we believe are without the competitor today
        self.outage_seen = False  # the week has one outage day: after it, we stop looking
        self.answers_today: list[tuple[str, float]] = []  # (pickup town, how far the answer was from what the book expected)
        if params.book == "day":
            self.book: PriceBook = DayBook(params.day_level, params.spread, rates, params.book_noise, params.book_prior)
        else:
            self.book = PriceBook(params.start_level, params.spread, rates)
        self.book.rates.setdefault("prior", 0.0)
        table = LANES.with_name(params.lane_table + ".json")
        self.lanes = json.loads(table.read_text(encoding="utf-8")) if params.lane_prior and table.exists() else {}
        self.day = 0  # the working day of the last request: a new one tells the book that a day has begun
        if params.menu_strength:
            self.book.rates["speed"] = 0.0
            self.book.offset["speed", "offered"] = 0.04 * params.menu_strength
            self.book.offset["speed", "omitted"] = -0.09 * params.menu_strength
        self.quoted: dict[str, dict[str, float]] = {}  # request id -> option -> the markup we quoted, declines left out
        self.keys: dict[str, list] = {}  # request id -> what the price book knows the request by
        self.hoped: dict[str, tuple[int, float]] = {}  # request id -> (day of the last pickup, chance to win) for quotes not yet answered
        self.dealer_days: dict[tuple[str, int], list[int]] = {}
        self.dealer_deliveries: dict[str, list[int]] = {}
        self.trusted: dict[str, int] = {}  # dealer -> orders we delivered to it on time, as the dealer counts them
        self.risk_model = risk.load() if params.budget else {}  # how often which car comes late
        self.posting = False  # whether the fee schedule being built is for one plain car (see `rising`)
        self.headroom_at, self.headroom_now = -1, 0.0  # the forecast of the week's on-time share over 90%, and the minute it was made
        self.asked: dict[str, int] = {}  # dealer -> requests it has sent this week
        self.wins: dict[str, int] = {}  # dealer -> orders it gave us
        self.done: dict[str, int] = {}  # dealer -> orders of its that we have delivered, on time or late
        self.sold = [0, 0]  # cents and orders: what an order pays us on average
        self.arrivals = [0, 0]  # orders delivered on time, and late

    # Decision 1: the price.

    def quote(self, desk: "Desk", request: dict) -> dict[str, int]:
        """A price for each option we want to sell; a declining price for the first option when we want none."""
        p, markups, days, lasts = self.p, {}, {}, {}
        self.asked[request["dealerId"]] = self.asked.get(request["dealerId"], 0) + 1
        if request["arrivedAt"] // DAY != self.day:
            self.day = request["arrivedAt"] // DAY
            self.book.new_day()
            self.outage_seen = self.outage_seen or bool(self.outage_towns)  # an outage lasts one day: each morning starts clean
            self.outage_towns, self.answers_today = set(), []
            for key in [key for key in self.book.offset if key[0] == "outage"]:
                self.book.offset[key] = 0.0
        first_leg = request["legs"][0]
        private_too_far = (
            p.private_drive_hours > 0
            and len(request["legs"]) == 1
            and (first_leg["delivery"]["privateAddress"] or first_leg["pickup"]["privateAddress"])
            and desk.geo.drive(first_leg) >= p.private_drive_hours * HOUR
        )
        if self.wanted(request) and (not private_too_far or p.private_after):
            leg, facts, ours = request["legs"][0], desk.facts(request), p.notes == "ours"
            if ours:  # what the note changes: a later ready time, shorter hours, a tighter deadline
                leg = apply(leg, facts)
            find_hours = self.find_hours(desk, request)
            shift = 0
            if p.quote_ready_shift and ours and facts.pickup_from and len(request["legs"]) == 1:
                original = request["legs"][0]
                if not (original["pickup"]["privateAddress"] or original["delivery"]["privateAddress"]):
                    shift = DAY * max(0, facts.pickup_from // DAY - original["pickup"]["window"]["from"] // DAY)
                    if shift:
                        leg = dict(leg)
                        for end in ("pickup", "delivery"):
                            window = {**leg[end]["window"], "to": original[end]["window"]["to"] + shift}
                            leg[end] = {**leg[end], "window": window}
            for option in request["options"]:
                deadline = option["deadline"] + shift
                if ours and facts.deadline:
                    deadline = min(deadline, facts.deadline)
                drive = desk.geo.drive(request["legs"][0]) + (PLATES_MINUTES if ours and facts.plates else 0)
                last = last_private_pickup(leg, deadline, drive) if leg["pickup"]["privateAddress"] else last_pickup(leg, deadline, drive)
                if last is not None and last - request["respondBy"] >= find_hours * HOUR and last % DAY >= p.min_last_hour * HOUR:
                    if p.risky_last_day >= 0 and last // DAY > p.risky_last_day and self.risky(request):
                        continue
                    if p.premium_after and not p.premium and last // DAY < 5 and any(each["car"]["premium"] for each in request["legs"]):
                        continue
                    if private_too_far and last // DAY < 5:
                        continue
                    days[option["kind"]] = last // DAY
                    lasts[option["kind"]] = last
            keys = self.keys_of(request, list(days)) if days else []
            factor = self.dealer_factor(request, keys, days) if days and p.dealer_calibration else 1.0
            target = 0.0
            if p.menu == 1 and days:
                markups, target = self.menu(desk, request, lasts, keys)
                days = {kind: day for kind, day in days.items() if kind in markups}
            else:
                for option in request["options"]:
                    if option["kind"] in days:
                        markups[option["kind"]] = self.markup(desk, request, option, lasts[option["kind"]], keys, factor)
            if p.same_day_premium and "same_day" in markups and len(markups) > 1:  # speed is worth more to the dealer
                markups["same_day"] *= 1 + p.same_day_premium
        if markups:
            self.quoted[request["id"]] = markups
            self.keys[request["id"]] = keys
            first = next(o["kind"] for o in request["options"] if o["kind"] in markups)  # the option a dealer most often takes
            beat = markups[first]
            if p.menu == 1:  # the option that is the best deal for the dealer, and the competitor level the quote beats
                listed = {o["kind"]: o["listPriceCents"] for o in request["options"]}
                first, beat = max(markups, key=lambda kind: OPTION_VALUE[kind] - markups[kind] * listed[kind]), target
            reserved_day = days[first]
            if p.reserve_chosen_day and len(markups) > 1:
                # Speed values and prices are both in cents. The amount we hold still comes from the original bid.
                offered = [o for o in request["options"] if o["kind"] in markups]
                preferred = max(offered, key=lambda o: OPTION_VALUE[o["kind"]] - round(markups[o["kind"]] * o["listPriceCents"]))
                reserved_day = days[preferred["kind"]]
            self.hoped[request["id"]] = (reserved_day, chance(factor * self.book.level(keys), beat, p.spread) * self.cap_weight(desk, request["legs"][0]))
        else:
            markups[request["options"][0]["kind"]] = p.decline
        return {o["kind"]: round(o["listPriceCents"] * markups[o["kind"]]) for o in request["options"] if o["kind"] in markups}

    def risky(self, request: dict) -> bool:
        """The kinds of car beyond the plain ones: a premium car, or a private address at either end."""
        return any(leg["car"]["premium"] or leg["pickup"]["privateAddress"] or leg["delivery"]["privateAddress"] for leg in request["legs"])

    def wanted(self, request: dict) -> bool:
        """The plain cars: one car between two dealer sites that any driver may take. Every other kind has its switch."""
        p, legs = self.p, request["legs"]
        if any(leg["car"]["premium"] for leg in legs) and not p.premium and not p.premium_after:
            return False
        if len(legs) == 2:
            return bool(p.trade_in)
        if legs[0]["delivery"]["privateAddress"] and not p.private_delivery:
            return False
        return bool(p.private_pickup) or not legs[0]["pickup"]["privateAddress"]

    def find_hours(self, desk: "Desk", request: dict) -> float:
        """The least time we want for finding a driver for a request, in hours."""
        p, leg = self.p, request["legs"][0]
        if leg["pickup"]["privateAddress"]:
            return p.private_find_hours
        if p.easy_find_hours and len(request["legs"]) == 1 and desk.geo.drive(leg) <= p.easy_drive_hours * HOUR and desk.near.get(leg["pickup"]["placeId"], 0) >= p.easy_drivers:
            return p.easy_find_hours  # a short drive from a town full of drivers finds one fast
        return p.min_find_hours

    def keys_of(self, request: dict, kinds: list[str]) -> list:
        """What the price book knows a request by: its dealer, the town the car goes to, and the fastest option we quote."""
        keys = [("dealer", request["dealerId"])]
        if self.p.small_rate and sum(self.asked.values()) >= 40 and request["dealerId"] not in sorted(self.asked, key=self.asked.get, reverse=True)[:4]:
            keys.append(("small", "dealers"))  # not one of the four that have sent most requests so far
        if self.p.lane_rate:
            keys.append(("to", request["legs"][0]["delivery"]["placeId"]))
        if self.p.option_rate:
            keys.append(("option", next(o["kind"] for o in request["options"] if o["kind"] in kinds)))
        if self.p.pickup_rate:
            keys.append(("from", request["legs"][0]["pickup"]["placeId"]))
        if self.p.outage and 8 * HOUR <= request["respondBy"] % DAY < 18 * HOUR:  # the competitor's day runs from 08:00 to 18:00
            keys.append(("outage", request["legs"][0]["pickup"]["placeId"]))
        if self.p.route_rate:
            keys.append(("route", request["legs"][0]["pickup"]["placeId"] + ">" + request["legs"][0]["delivery"]["placeId"]))
        if self.p.lane_prior:  # what earlier worlds know of this lane: an offset that is set once and not learned
            a, b = request["legs"][0]["pickup"]["placeId"], request["legs"][0]["delivery"]["placeId"]
            key = ("prior", a + ">" + b)
            if key not in self.book.offset:
                known = self.lanes.get("route", {}).get(a + ">" + b)
                if known is None:
                    known = self.lanes.get("from", {}).get(a, 0.0) + self.lanes.get("to", {}).get(b, 0.0)
                self.book.offset[key] = self.p.lane_prior * known
            keys.append(key)
        if self.p.menu_strength:
            fastest = request["options"][0]["kind"]
            keys.append(("speed", "offered" if fastest in kinds else "omitted"))
        return keys

    def dealer_factor(self, request: dict, keys: list, offered: dict) -> float:
        """Fit from lab practice only. This calibrates decisions; learning retains its original coordinates."""
        dealer = request["dealerId"]
        prior_wins, prior_seen = self.dealer_days.get((dealer, request["arrivedAt"] // DAY - 1), (0, 0))
        delivered, late = self.dealer_deliveries.get(dealer, (0, 0))
        missing_same = request["options"][0]["kind"] == "same_day" and "same_day" not in offered
        delta = (-0.002 - 0.254 * math.log(self.book.level(keys) / 1.4)
                 + 0.336 * math.log1p(self.trusted.get(dealer, 0) / 100)
                 - 0.091 * ((prior_wins + 1) / (prior_seen + 2) - 0.5)
                 - 0.043 * math.log1p(late) + 0.040 * math.log1p(delivered) / 3
                 - 0.131 * missing_same)
        return math.exp(self.p.dealer_calibration * delta)

    def markup(self, desk: "Desk", request: dict, option: dict, last: int, keys: list, factor: float = 1.0) -> float:
        """The price with the best expected margin, in list prices: chance to win x (price - cost)."""
        cost = self.cost(desk, request, option, last)
        return factor * self.book.best_markup(keys, cost / factor, floor=cost * (1 + self.p.min_margin) / factor,
                                              ceiling=self.p.ceiling / factor)[0]

    def cost(self, desk: "Desk", request: dict, option: dict, last: int) -> float:
        """What a car costs us if we win it on this option, in list prices of the option."""
        p, day = self.p, last // DAY
        leg = request["legs"][0]
        hours = desk.geo.drive(leg) / HOUR
        find_hours = (last - request["respondBy"]) / HOUR
        # A long drive and a place where few drivers live both make a car dearer to move and later to arrive (lab/fit_cost.py).
        typical_fees = p.cost + p.cost_drive * max(0.0, hours - 3) + p.cost_thin * desk.thinness(leg)
        typical_fees += p.cost_short * max(0.0, 14 - find_hours) + (p.cost_private if leg["delivery"]["privateAddress"] else 0.0)
        typical_fees += p.cost_premium if leg["car"]["premium"] else 0.0
        if p.cost_home and self.homebound(desk, request):
            typical_fees -= p.cost_home
        if p.cost_after and day >= 5:
            typical_fees -= p.cost_after
        typical_fees += (p.cost_private_pickup if leg["pickup"]["privateAddress"] else 0.0) + (p.cost_trade_in if len(request["legs"]) == 2 else 0.0)
        if p.guard and self.careful(desk) and self.at_risk(desk, leg, last) and not (p.guard_after and last // DAY >= 5):
            typical_fees += p.guard_cost
        if p.budget:  # the chance to come late above a plain car's, at what lateness costs now
            extra = max(0.0, self.late_chance(desk, request, last) - risk.PLAIN)
            typical_fees += extra * (p.late_cost + p.budget_price * max(0.0, 1 - self.headroom(desk) / p.budget) ** 2)
        if p.easy_cost and self.relaxed(desk):
            typical_fees -= p.easy_cost
        if p.snow_cost and desk.snow_on(leg, day):  # snow slows the drive and keeps drivers at home: such cars are late four times as often
            typical_fees += p.snow_cost
        cents = typical_fees * self.steady(desk, request, leg, request["referenceFeeCents"], p.road_cost_blend)
        if p.fee_floor:  # no driver takes a fee of a few euros, whatever the typical fee says
            cents = max(cents, 1.15 * p.fee_floor)
        if p.hour_cost:  # a driver's time is the scarce thing: charge for every hour a car takes one, the trips there and home too
            cents = p.fee_share * cents + 100 * p.hour_cost * desk.driver_hours(leg)
        if p.pair_bonus and desk.pairable(request, last):  # a round trip is driven for three quarters of two single fees
            cents -= p.pair_bonus * request["referenceFeeCents"]
        if p.trust_gain:
            cents = max(0.3 * cents, cents - p.trust_gain * self.trust_value(request))
        cost = cents / option["listPriceCents"]  # in list prices of this option
        if p.fill_cut and p.day_cap and 1 <= day <= 4:
            # The share of a due day's cars that is won before the day before it (60 weeks): Tuesday none, Friday four in ten;
            # the rest comes between 08:00 and 18:00 of the day before, evenly. Behind that pace the day will end with idle
            # drivers, so its next car costs less; the full cut at 0.2 of the cap behind.
            early = {1: 0.0, 2: 0.17, 3: 0.27, 4: 0.41}[day]
            hours = (day * DAY + 18 * HOUR - desk.now) / HOUR
            if hours <= 34:
                pace = p.fill_target * (early + (0.95 - early) * min(1.0, (34 - hours) / 10))
                held = (desk.due(day) + sum(hope for hoped_day, hope in self.hoped.values() if hoped_day == day)) / (p.day_cap * desk.drivers)
                cost *= 1 - p.fill_cut * min(1.0, max(0.0, pace - held) / 0.2)
        long_after = bool(p.cap_after_hours) and desk.geo.drive(leg) >= p.cap_after_hours * HOUR
        if long_after and p.cap_long and p.cap_week_only and day >= 5:
            # A long car due after Friday pays for the long cars already due that day, and only for them: long cars are late by how
            # many long cars share the day (4.8% under one per 100 listed drivers, 10 to 13% above two); short cars do not crowd them
            longs = sum(1 for order_id, order in desk.orders.items() if None in order["deliveredAt"] and len(order["legs"]) == 1
                        and desk.last_pickup.get(order_id, order["lastPickupAt"]) // DAY == day and desk.geo.drive(order["legs"][0]) >= p.cap_after_hours * HOUR)
            cost *= 1 + (longs / (p.cap_long * desk.drivers)) ** p.cap_power
        elif p.day_cap and not (p.cap_week_only and day >= 5 and not long_after):  # drivers can move only so many cars on one day: near the cap, a new car for that day costs much more
            due = desk.due(day, thin_only=bool(p.cap_thin)) + sum(hope for hoped_day, hope in self.hoped.values() if hoped_day == day)
            cap = (p.cap_easy if p.cap_easy and self.relaxed(desk) else p.day_cap) * (p.cap_monday if day >= 5 else 1.0)
            cost *= 1 + self.cap_weight(desk, leg) * (due / (cap * desk.drivers)) ** p.cap_power
        if p.strain:  # deadline warnings are coming: drivers are short today, so take on less
            cost *= 1 + p.strain * max(0.0, desk.strain() - 0.03)
        return cost

    def menu(self, desk: "Desk", request: dict, lasts: dict, keys: list) -> tuple[dict[str, float], float]:
        """Prices for the options we can serve, by the rule the dealers follow (measured on a million quotes):
        a dealer weighs each offer by what its speed is worth minus its price, takes our best offer if it is at
        least as good as the competitor's best, and the competitor is priced on EVERY option the dealer asked
        for, also the ones we leave out. So a next-day quote to a dealer who asked for same day must beat the
        competitor's same-day offer, 16 euros of speed included. We pick the competitor level `m` we want to
        beat (chance to win x margin), and price every option to be exactly as good as the competitor at that
        level; the option that earns us most stays as it is and the others cost 1.50 more, so the dealer takes it.
        Returns the markups by option, and `m`."""
        p, level, asked = self.p, self.book.level(keys), request["options"]
        costs = {o["kind"]: self.cost(desk, request, o, lasts[o["kind"]]) * o["listPriceCents"] for o in asked if o["kind"] in lasts}
        best = None
        for step in range(int((p.ceiling - 0.6) / 0.01) + 1):
            m = 0.6 + 0.01 * step
            theirs = max(OPTION_VALUE[o["kind"]] - m * o["listPriceCents"] for o in asked)
            for kind, cost in costs.items():
                price = OPTION_VALUE[kind] - theirs
                if price >= cost * (1 + p.min_margin):
                    value = chance(level, m, self.book.spread) * (price - cost)
                    if best is None or value > best[0]:
                        best = (value, m, kind, theirs)
        if best is None:
            return {}, 0.0
        _, m, chosen, theirs = best
        listed = {o["kind"]: o["listPriceCents"] for o in asked}
        prices = {kind: OPTION_VALUE[kind] - theirs + (0 if kind == chosen else 150) for kind in costs}
        return {kind: price / listed[kind] for kind, price in prices.items() if price >= costs[kind] * (1 + p.min_margin)}, m

    def beaten(self, request: dict, markups: dict[str, float]) -> float:
        """The competitor level that a quote beats: the dealer says yes when the competitor stands above it."""
        listed = {o["kind"]: o["listPriceCents"] for o in request["options"]}
        ours = max(OPTION_VALUE[kind] - markup * listed[kind] for kind, markup in markups.items())
        return max((OPTION_VALUE[kind] - ours) / cents for kind, cents in listed.items())

    def cap_weight(self, desk: "Desk", leg: dict) -> float:
        """How much a car counts against the day's cap: fully when few drivers live near its two ends, hardly at
        all when many do. Cars with drivers near both ends arrive on time however full the day is."""
        return min(1.0, desk.thinness(leg) / 0.8) if self.p.cap_thin else 1.0

    def late_chance(self, desk: "Desk", request: dict, last: int, flu: Optional[bool] = None) -> float:
        """How likely this car is to come late if we win it with this last pickup (dispatch/risk.py). Whether its day
        is a flu day is known from just after midnight; for a day still to come it is one chance in five."""
        leg, day = request["legs"][0], last // DAY
        near = min(desk.near.get(leg["pickup"]["placeId"], 0), desk.near.get(leg["delivery"]["placeId"], 0))
        kind = risk.kind_of(leg["car"]["premium"], leg["pickup"]["privateAddress"], leg["delivery"]["privateAddress"])
        hours, find = desk.geo.drive(leg) / HOUR, (last - request["respondBy"]) / HOUR

        def of(flu_day: bool) -> float:  # the flu was measured on weekdays only
            return risk.chance(self.risk_model, risk.facts(kind, hours, find, near, day, flu_day and day <= 4))

        if flu is not None:
            return of(flu)
        if day <= desk.now // DAY or day > 4:  # today's flu has shown by now, and no flu was seen at a weekend
            return of(day == desk.flu_day)
        return 0.8 * of(False) + 0.2 * of(True)

    def headroom(self, desk: "Desk") -> float:
        """The forecast of the week's on-time share, less the 90% that ranking needs. It counts the cars that have
        arrived, each car on its way by its chance to come late (a car without a driver close to its last pickup
        by what such cars did: three in ten late at ten hours, three in four at three), the cars we will still
        win, and one bad day still to come: the weekday ahead on which a flu would cost us most."""
        if self.headroom_at == desk.now:
            return self.headroom_now
        on_time, late = self.arrivals
        today, expected, ahead, flying = desk.now // DAY, 0.0, defaultdict(float), 0
        for order in desk.orders.values():
            if None not in order["deliveredAt"] or order["id"] not in desk.requests:
                continue
            flying += 1
            if desk.now > order["deadline"]:
                expected += 1.0
                continue
            request = desk.requests[order["id"]]
            last = desk.last_pickup.get(order["id"], order["lastPickupAt"])
            day, left = last // DAY, (last - desk.now) / HOUR
            usual = self.late_chance(desk, request, last, day == desk.flu_day)
            if any(gig in desk.booked for gig in desk.gigs_of(order["id"])):
                expected += 0.6 * usual
            else:
                expected += max(usual, 0.75 if left <= 3 else 0.6 if left <= 5 else 0.45 if left <= 7 else 0.3 if left <= 10 else 0.0)
            if today < day <= 4:
                ahead[day] += self.late_chance(desk, request, last, True) - usual
        won = on_time + late + flying
        # the cars still to win: requests come on five working days from 08:00 to 18:00
        gone = min(5.0, today + min(1.0, max(0.0, (desk.now % DAY - 8 * HOUR) / (10 * HOUR))))
        coming = (5.0 - gone) * (won / gone if gone >= 1 else 75.0)
        days_ahead = max(0, 4 - today)
        # A bad day is worse than the usual flu day: on the worst ones one car in six of that day came late, two and a
        # half times what the usual flu day adds (60 weeks: lab/flu_severity.py).
        bad_day = 2.5 * (max(ahead.values(), default=0.0) + (0.04 * coming / days_ahead if days_ahead else 0.0))
        share = 1 - (late + expected + 0.035 * coming + bad_day) / max(1.0, won + coming)
        self.headroom_at, self.headroom_now = desk.now, share - 0.90
        desk.stats["headroom_low"] = min(desk.stats.get("headroom_low", 1000), round(1000 * self.headroom_now))
        desk.stats[f"headroom_day{today}"] = round(1000 * self.headroom_now)  # the last forecast of each day, for the lab
        return self.headroom_now

    def careful(self, desk: "Desk") -> bool:
        """Whether this week is going badly: the share of our cars that came late, or that had no driver three hours
        before their last pickup in the last day (three in four of those come late). One week decides the final and
        a week under 90% on time scores nothing, so from here the desk gives up some margin to stay clear of it."""
        warned = sum(1 for at in desk.warnings if at > desk.now - DAY)
        done = sum(self.arrivals) + warned
        return done >= 40 and (self.arrivals[1] + 0.75 * warned) / done > self.p.guard

    def relaxed(self, desk: "Desk") -> bool:
        """Whether this week is going well: at least 40 cars decided and the late share under half the guard's
        line. Then the drivers can carry more, and the desk prices to win more cars. The same count that makes
        the desk careful in a hard week lets it take more in an easy one."""
        warned = sum(1 for at in desk.warnings if at > desk.now - DAY)
        done = sum(self.arrivals) + warned
        return done >= 40 and (self.arrivals[1] + 0.75 * warned) / done < (self.p.guard or 0.05) / 2

    def at_risk(self, desk: "Desk", leg: dict, last: int) -> bool:
        """The kinds of car that make most of the late ones: an end where few drivers live, a drive over five hours,
        a last pickup in the morning, a private address."""
        if self.p.guard_kinds:
            thin = any(desk.near.get(leg[end]["placeId"], 0) < 15 and desk.reach.get(leg[end]["placeId"], 0) < 100 for end in ("pickup", "delivery"))
            return thin or desk.geo.drive(leg) > 5 * HOUR or last % DAY < 13 * HOUR
        near = min(desk.near.get(leg["pickup"]["placeId"], 0), desk.near.get(leg["delivery"]["placeId"], 0))
        return (near < 15 or desk.geo.drive(leg) > 5 * HOUR or last % DAY < 13 * HOUR
                or leg["pickup"]["privateAddress"] or leg["delivery"]["privateAddress"])

    def trust_value(self, request: dict) -> float:
        """What one more on-time delivery to this dealer is worth in its later prices, in cents. Each one adds 1% to
        what the dealer accepts from us, up to 25 (measured with fork: 0.96 to 1.00 of that). So until the count is
        full, a delivery brings 1% of what we sell that dealer from now to the day the count would be full anyway."""
        dealer, now = request["dealerId"], request["arrivedAt"]
        missing = 25 - self.trusted.get(dealer, 0) - (self.wins.get(dealer, 0) - self.done.get(dealer, 0))
        if missing <= 0:
            return 0.0
        worked = min(5.0, now // DAY + min(1.0, max(0.0, (now % DAY - 8 * HOUR) / (10 * HOUR))))  # working days gone
        a_day = max(self.wins.get(dealer, 0), 0.35 * self.asked.get(dealer, 0)) / max(0.25, worked)  # orders a day from this dealer
        days = min(5.0 - worked, missing / max(1.0, a_day) + 1.0)  # a delivery follows its win by about a day
        price = self.sold[0] / self.sold[1] if self.sold[1] else 8500.0
        return 0.01 * price * a_day * max(0.0, days)

    def delivered(self, dealer: str, on_time: bool) -> None:
        """A dealer accepts 1% more from us for each order we brought on time, up to 25, and a late order halves
        that count (level 8). We know the rule, so we move the dealer's level at once instead of waiting to learn it."""
        if self.p.dealer_calibration:
            deliveries = self.dealer_deliveries.setdefault(dealer, [0, 0])
            deliveries[0] += 1
            deliveries[1] += int(not on_time)
        self.done[dealer] = self.done.get(dealer, 0) + 1
        self.arrivals[0 if on_time else 1] += 1
        before = self.trusted.get(dealer, 0)
        after = min(25, before + 1) if on_time else before // 2
        self.trusted[dealer] = after
        if self.p.trust:
            self.book.offset[("dealer", dealer)] += math.log((100 + after) / (100 + before))

    def observe(self, desk: "Desk", event: dict) -> None:
        """Learns the price levels from the answers to our quotes."""
        if event["kind"] in ("order_won", "order_lost"):
            rid = event["order"]["id"] if event["kind"] == "order_won" else event["requestId"]
            self.hoped.pop(rid, None)
            if self.p.dealer_calibration and rid in desk.requests:
                request = desk.requests[rid]
                day_key = (request["dealerId"], request["arrivedAt"] // DAY)
                answers = self.dealer_days.setdefault(day_key, [0, 0])
                answers[0] += int(event["kind"] == "order_won")
                answers[1] += 1
        if event["kind"] == "order_won":
            order = event["order"]
            markups, keys = self.quoted.pop(order["id"], None) or {}, self.keys.pop(order["id"], None)
            request = desk.requests.get(order["id"])
            if request:  # after a restart the remembered quote can be missing: the order itself says what the dealer paid
                self.wins[request["dealerId"]] = self.wins.get(request["dealerId"], 0) + 1
                self.sold = [self.sold[0] + order["priceCents"], self.sold[1] + 1]
                listed = next(o["listPriceCents"] for o in request["options"] if o["kind"] == order["option"])
                if keys and markups.get(order["option"]):
                    self.outage_answer(desk, request, keys, markups[order["option"]], True)
                paid = markups.get(order["option"]) or order["priceCents"] / listed
                if self.p.menu:  # what the yes says about the competitor: it stands above the level this quote beats
                    paid = self.beaten(request, markups or {order["option"]: paid})
                self.book.learn(keys or self.keys_of(request, [order["option"]]), paid, won=True)
        elif event["kind"] == "order_lost":
            markups, keys = self.quoted.pop(event["requestId"], None), self.keys.pop(event["requestId"], None)
            if markups and keys:  # the dealer refused even our lowest price
                if event["requestId"] in desk.requests:
                    self.outage_answer(desk, desk.requests[event["requestId"]], keys, min(markups.values()), False)
                refused = min(markups.values())
                if self.p.menu and event["requestId"] in desk.requests:
                    refused = self.beaten(desk.requests[event["requestId"]], markups)
                self.book.learn(keys, refused, won=False)

    def outage_answer(self, desk: "Desk", request: dict, keys: list, markup: float, won: bool) -> None:
        """Looks for the competitor's outage in today's answers. On that day the dealers who load within about
        80 km of one town take about 28% more from us, from 08:00 to 18:00. We see only our own answers: so for
        every town we compare how the answers from around it surprised the price book with the answers from
        everywhere else. A day when the whole market is dear moves both alike and is not an outage. When one
        region stands out far enough, on enough answers, the book's level for that region goes up by the measured
        28% until the evening, and the market level gives back what those surprising wins had added to it."""
        p = self.p
        if not p.outage or self.outage_seen or self.outage_towns or request["respondBy"] // DAY != self.day or not 8 * HOUR <= request["respondBy"] % DAY < 18 * HOUR:
            return
        plain = [key for key in keys if key[0] != "outage"]
        self.answers_today.append((request["legs"][0]["pickup"]["placeId"], (1.0 if won else 0.0) - chance(self.book.level(plain), markup, self.book.spread)))
        if len(self.answers_today) < 16 or len(self.answers_today) % 4:
            return
        if not self.regions:
            self.regions = {town: set(neighbours(desk.geo, town, p.outage_km)) for town in desk.geo.at}
        best = None
        for centre, region in self.regions.items():
            inside = [surprise for town, surprise in self.answers_today if town in region]
            outside = [surprise for town, surprise in self.answers_today if town not in region]
            if len(inside) < 8 or len(outside) < 8:
                continue  # too few answers on one side to tell: a quiet region is never called
            gap = sum(inside) / len(inside) - sum(outside) / len(outside)
            score = gap / (0.25 / len(inside) + 0.25 / len(outside)) ** 0.5
            if gap >= 0.2 and score >= p.outage and (best is None or score > best[0]):
                best = (score, centre, sum(inside))
        if best:
            self.outage_towns = self.regions[best[1]]
            for town in self.outage_towns:
                self.book.offset["outage", town] = math.log(1 + p.outage_lift)
            self.book.market -= self.book.rates["market"] * best[2]
            desk.stats["outages"] += 1
            desk.stats[f"outage_day{self.day}"] += 1

    # Decision 2: the fees.

    def fees(self, desk: "Desk", order: dict, cars: int, urgent: bool) -> list[dict]:
        """The fee schedule for some of an order's cars, from now on."""
        typical = desk.typical(order) * cars / len(order["legs"])
        typical = self.steady(desk, desk.requests[order["id"]], order["legs"][0], typical, self.p.road_fee_blend)
        last = desk.last_pickup.get(order["id"], order["lastPickupAt"])
        leg = order["legs"][0]
        if self.p.premium_fee_line and last // DAY >= 5 and len(order["legs"]) == 1 and leg["car"]["premium"]:
            asked = desk.requests[order["id"]]["legs"][0]
            endpoints = ("pickup", "delivery")
            if all(not leg[end]["privateAddress"] and leg[end]["placeId"] == asked[end]["placeId"] for end in endpoints):
                line = ROAD_BASE + ROAD_MINUTE * desk.geo.minutes[leg["pickup"]["placeId"], leg["delivery"]["placeId"]]
                typical = max(0.8 * typical, min(1.25 * typical, line))
        gone = order["lastPickupAt"] if order["lastPickupAt"] - last > 12 * HOUR else last  # the dealer may have moved the deadline after the note
        if self.p.late_open and desk.level >= 2 and len(order["legs"]) == 1 and (
                desk.now + desk.geo.drive(leg) > order["deadline"] or (self.p.late_by_pickup and cars == 1 and desk.now > gone)):
            # Too late to be on time whatever we pay. From here a fee buys only a smaller refund (a quarter of the
            # price back up to a day late, half after), so it starts low and climbs slowly; the steep end stays,
            # because a car that is never delivered costs twice its price.
            p = self.p
            path = ((0, p.late_open), (6, (2 * p.late_open + p.late_top) / 3), (12, (p.late_open + 2 * p.late_top) / 3), (24, p.late_top), (36, p.late_fee), (48, p.urgent_top))
            return self.settle([{"at": desk.now + hours * HOUR, "feeCents": max(1, round(typical * fee))} for hours, fee in path], hold=False)
        lead = max(self.p.late_lead, self.p.guard_lead) if self.p.guard and self.careful(desk) else None
        if self.p.long_lead and desk.geo.drive(leg) >= self.p.long_hours * HOUR:
            # A long drive that is still without a driver twelve hours before its last pickup comes late one time in
            # four (200 of 807 over 60 weeks), and long drives are half of the late cars of a hard week.
            lead = max(lead or self.p.late_lead, self.p.long_lead)
        self.posting = cars == 1 and self.plain_leg(order)
        steps = self.schedule(desk, typical, last, urgent, self.opening(desk, order), lead, desk.geo.drive(leg))
        self.posting = False
        floor = self.p.thin_evening_floor
        if floor <= 0 or desk.level != 8 or urgent or cars != 1 or len(order["legs"]) != 1 or last % DAY >= 15 * HOUR or desk.now >= last - 3 * HOUR:
            return steps
        if min(desk.near.get(leg[end]["placeId"], 0) for end in ("pickup", "delivery")) >= 10:
            return steps
        at = max(desk.now, last // DAY * DAY - 7 * HOUR)  # 17:00 on the day before
        minimum = round(typical * floor)
        if next((s["feeCents"] for s in reversed(steps) if s["at"] <= at), 0) >= minimum:
            return steps
        return [s for s in steps if s["at"] < at] + [{"at": at, "feeCents": minimum}] + [s for s in steps if s["at"] > at and s["feeCents"] > minimum]

    def steady(self, desk: "Desk", request: dict, leg: dict, typical: float, blend: float) -> float:
        """The typical fee with `blend` of its noise taken out. The world draws each request's typical fee around the
        cost of its lane (handbook, "The typical fee"), and a driver does not care about that draw. A fee far under
        the lane's line is booked a day late ten times as often, and a price built on it wins exactly those cars.
        Only for plain cars on the lane the dealer first asked for; never more than 20% down or 25% up."""
        asked = request["legs"][0]
        plain = len(request["legs"]) == 1 and not leg["car"]["premium"] and not any(leg[end]["privateAddress"] for end in ("pickup", "delivery"))
        moved = any(leg[end]["placeId"] != asked[end]["placeId"] for end in ("pickup", "delivery"))
        if self.p.steady_private and blend and not plain and not moved and len(request["legs"]) == 1 and not leg["car"]["premium"]:
            line = ROAD_BASE + ROAD_MINUTE * desk.geo.minutes[leg["pickup"]["placeId"], leg["delivery"]["placeId"]]
            return max(typical, min(1.25 * typical, line))  # a private address: only the low draws, up to the line
        if not blend or not plain or moved:
            return typical
        line = ROAD_BASE + ROAD_MINUTE * desk.geo.minutes[leg["pickup"]["placeId"], leg["delivery"]["placeId"]]
        return typical + blend * (min(1.25 * typical, max(0.8 * typical, line)) - typical)

    def pair_typical(self, desk: "Desk", first: dict, second: dict) -> float:
        """Price ordinary pairs whose two reference fees together were an unusually high draw."""
        a, b = desk.typical(first), desk.typical(second)
        raw = a + b
        threshold = self.p.pair_road_cap
        if threshold > 0:
            line = 0.0
            bounded = 0.0
            for order, reference in ((first, a), (second, b)):
                leg = order["legs"][0]
                request = desk.requests[order["id"]]
                asked = request["legs"][0]
                if not self.plain_leg(order) or any(leg[end]["placeId"] != asked[end]["placeId"] for end in ("pickup", "delivery")):
                    break
                line += ROAD_BASE + ROAD_MINUTE * desk.geo.minutes[leg["pickup"]["placeId"], leg["delivery"]["placeId"]]
                bounded += self.steady(desk, request, leg, reference, 1.0)
            else:
                if raw >= threshold * line:
                    raw = min(raw, bounded)
        elif self.p.pair_steady and self.plain_leg(first) and self.plain_leg(second):
            raw = sum(self.steady(desk, desk.requests[order["id"]], order["legs"][0], reference, 1.0) for order, reference in ((first, a), (second, b)))
        return raw * self.p.pair_fee

    @staticmethod
    def plain_leg(item: dict) -> bool:
        """One ordinary car between two dealer sites (an order or a request)."""
        leg = item["legs"][0]
        return len(item["legs"]) == 1 and not leg["car"]["premium"] and not leg["pickup"]["privateAddress"] and not leg["delivery"]["privateAddress"]

    def homebound(self, desk: "Desk", item: dict) -> bool:
        """A plain car (an order or a request) that goes where drivers live, on a short drive, with a fee worth a trip: a
        driver on the way home takes it for less."""
        p, leg = self.p, item["legs"][0]
        if not self.plain_leg(item) or desk.near.get(leg["delivery"]["placeId"], 0) < p.home_drivers or desk.geo.drive(leg) >= p.home_hours * HOUR:
            return False
        request = desk.requests.get(item["id"], item)
        return self.steady(desk, request, leg, request["referenceFeeCents"], p.road_fee_blend) >= p.home_min_fee

    def opening(self, desk: "Desk", order: dict) -> float:
        """The opening fee, in typical fees: lower for a short drive to a town full of drivers, who are on their way home."""
        p, leg = self.p, order["legs"][0]
        if p.home_open and self.homebound(desk, order):
            return p.home_open
        many = desk.near.get(leg["delivery"]["placeId"], 0) >= 100
        short = desk.geo.drive(leg) < 3 * HOUR
        if p.open_easy and many and short:
            return p.open_easy
        if p.open_hard and not many and not short:
            return p.open_hard
        return p.open_fee

    def schedule(self, desk: "Desk", typical: float, last: int, urgent: bool, opening: float = 0.0, lead: Optional[float] = None, drive: float = 0) -> list[dict]:
        """A fee schedule from now on for a gig whose typical fee is `typical` and whose first car must be collected by `last`."""
        p, now = self.p, desk.now
        opening = opening or p.open_fee

        def step(at: float, fee: float) -> dict:
            return {"at": int(at), "feeCents": max(1, round(typical * fee))}

        if desk.level == 1:  # level 1 takes one fee only
            return [step(now, opening)]
        lead = p.late_lead if lead is None else lead
        warning = last - int(lead * HOUR)
        if lead > 3 and not 8 * HOUR <= warning % DAY < 22 * HOUR:  # no driver reads then: the evening before is the last chance
            warning = (warning - 8 * HOUR) // DAY * DAY + int(21.5 * HOUR)
        if urgent or now >= warning:
            rises = int((p.urgent_top - p.late_fee) / p.urgent_step + 1e-9)
            return self.settle([step(now + k * 30, p.late_fee + k * p.urgent_step) for k in range(rises + 1)], hold=False)
        if p.teaser_fee and warning - now >= 6 * HOUR:  # time enough: first ask for less, then go on as usual
            usual = self.rising(now + p.teaser_minutes, last, warning, step, opening, drive)
            return self.settle([step(now, p.teaser_fee)] + usual)
        return self.settle(self.rising(now, last, warning, step, opening, drive))

    def settle(self, steps: list[dict], hold: bool = True) -> list[dict]:
        """Applies the rules about when a raise is worth making, and the lowest fee a driver takes."""
        p = self.p
        if p.fee_floor:
            steps = [{**step, "feeCents": max(step["feeCents"], p.fee_floor)} for step in steps]
        if hold and (p.night_hold or p.weekend_hold):
            moved = [steps[0]]
            for step in steps[1:]:
                at, minute, weekday = step["at"], step["at"] % DAY, step["at"] // DAY % 7
                if p.weekend_hold and (weekday == 6 or (weekday == 5 and minute >= 12 * HOUR)):
                    at = (at // DAY + (1 if weekday == 6 else 2)) * DAY  # to Monday 00:00
                    minute = 0
                if p.night_hold and (minute >= 22 * HOUR or minute < 6.5 * HOUR):
                    at = (at // DAY + (1 if minute >= 22 * HOUR else 0)) * DAY + int(6.5 * HOUR)  # to 06:30
                moved.append({"at": max(at, moved[-1]["at"]), "feeCents": step["feeCents"]})
            steps = moved
        merged: list[dict] = []
        for step in steps:  # one step a minute: of the steps that now fall together, the last and highest counts
            if merged and step["at"] <= merged[-1]["at"]:
                merged[-1] = {"at": merged[-1]["at"], "feeCents": max(merged[-1]["feeCents"], step["feeCents"])}
            else:
                merged.append(step)
        return merged

    def rising(self, now: int, last: int, warning: int, step, opening: float, drive: float = 0) -> list[dict]:
        p = self.p
        early = p.early_long if p.early_long and drive >= p.long_hours * HOUR else p.early_hour
        if p.schedule == "plan":
            return self.planned(now, last, warning, step, opening)
        if last % DAY < early * HOUR:
            top_at = last // DAY * DAY - DAY + p.evening_hour * HOUR
        else:
            top_at = warning - (p.lead_hours - 3) * HOUR  # with the usual 3-hour warning this is `lead_hours` before the last pickup
        top_at = min(max(top_at, now), warning)
        if p.short_ramp and self.posting and top_at - now < HOUR and last % DAY >= early * HOUR and warning - now >= 2 * HOUR:
            # Won at short notice. Opened at the top fee it is booked at once; opened at the usual fee with the top
            # fee within the hour it is booked as punctually and paid 1.01 typical fees instead of 1.2.
            reach = now + min(80, (warning - now) / 3)
            start = now + p.hold * (reach - now)
            steps = [step(now, opening)] + [step(start + (reach - start) * k / 6, opening + (p.top_fee - opening) * k / 6) for k in range(1, 7)]
            if warning - reach >= HOUR:
                steps += [step(reach + (warning - reach) * k / 6, p.top_fee + (p.late_fee - p.top_fee) * k / 6) for k in range(1, 7)]
            return steps
        ramp_from = now + p.hold * (top_at - now)
        rises = 6
        steps = [step(now, opening if top_at - now >= HOUR else p.top_fee)]
        if top_at - now >= HOUR:
            steps += [step(ramp_from + (top_at - ramp_from) * k / rises, opening + (p.top_fee - opening) * k / rises) for k in range(1, rises + 1)]
        if warning - top_at >= HOUR:
            steps += [step(top_at + (warning - top_at) * k / rises, p.top_fee + (p.late_fee - p.top_fee) * k / rises) for k in range(1, rises + 1)]
        return steps

    def planned(self, now: int, last: int, warning: int, step, opening: float) -> list[dict]:
        """A schedule that rises only when drivers plan their day. Most bookings happen early in the morning and
        late in the afternoon, so a raise between those hours buys nothing. The fee reaches `top_fee` at the last
        planning hour that still leaves a driver time to plan the trip, and `mid_fee` at the one before it."""
        p = self.p
        hours = [float(h) * HOUR for h in p.plan_hours.split(",")]
        moments = sorted(day * DAY + h for day in range(now // DAY, last // DAY + 1) for h in hours)
        moments = [m for m in moments if now < m <= last - p.plan_lead_hours * HOUR]
        steps = [step(now, opening if moments else p.top_fee)]
        if moments:
            if len(moments) >= 2:
                steps.append(step(moments[-2], p.mid_fee))
            steps.append(step(moments[-1], p.top_fee))
        after = max(now, moments[-1] if moments else now)
        if warning - after >= HOUR:  # from there to the deadline warning, rise evenly to the late fee
            steps += [step(after + (warning - after) * k / 4, p.top_fee + (p.late_fee - p.top_fee) * k / 4) for k in range(1, 5)]
        return steps
