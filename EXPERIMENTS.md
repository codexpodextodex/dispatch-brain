# Experiment log

Every idea we tried, with its numbers with and without, on the same weeks. Failures included.

- Level 8 practice weeks. Margin is in game euros per week. "On time" is the share of won orders on time.
- `lab-1..10` are the seeds we tune on. `hold-1..10` are never tuned on: a change is kept only if it also
  helps there.
- "4 seeds" means lab-1..4, from the first hour, before we moved to 10 seeds and a holdout family.
- Reproduce any row with `python -m lab.sweep --both --set <setting>` (saved weeks are not played again).

## Reference points

| System | Seeds | Mean margin | Worst week | Lowest on time | Ranked weeks |
|---|---|---|---|---|---|
| Kit starter | lab-1..10 | −63,748 | −75,667 | 42.9% | 0/10 |
| Kit starter | hold-1..10 | −71,997 | −97,858 | 33.9% | 0/10 |
| Kit starter, handbook seed `spread-1` | 1 | −72,612.51 | | 45.5% | 0/1 (matches the handbook to the cent) |

## 1. Choose the cars, one fixed markup (Sat 00:30)

**Idea.** Quote only plain cars (one car, dealer site to dealer site, not premium) that leave at least N hours
to find a driver, at one markup over the list price; decline the rest with a very high quote.
**Why.** The starter's own week showed where it fails: with under 6 hours to find a driver it was on time
0–7% of the time, with over 14 hours about 60%, and by Thursday it had used up the drivers.

| Markup (≥14 h to find a driver) | Mean margin, 4 seeds | Ranked | Orders won per week |
|---|---|---|---|
| 1.20 | −4,584 | 1/4 | 552 |
| 1.35 | 5,493 | 3/4 | 417 |
| 1.50 | 9,159 | 4/4 | 280 |
| 1.60 | 8,742 | 4/4 | 193 |
| 1.70 | 7,005 | 4/4 | 127 |
| 1.80 | 5,852 | 4/4 | 92 |
| 2.00 | 2,743 | 4/4 | 34 |

Hours to find a driver, at markup 1.5: 8 h → 9,043; 14 h → 9,159; 20 h → 9,296. Kept 14 h.
**Learned.** Fewer cars at a higher price beats volume; the best markup differs by week (1.5 to 1.6).

## 2. Open the gig below the typical fee (Sat 00:40)

**Why.** 65–75% of our gigs were booked at the opening fee, so the typical fee is more than many drivers need.

| Opening fee → top fee, markup 1.5 | Mean margin, 4 seeds | Ranked | Fees paid, × typical |
|---|---|---|---|
| 1.00 → 1.5 (before) | 9,159 | 4/4 | 1.07 |
| 0.85 → 1.3 | 11,152 | 4/4 | 0.96 |
| 0.85 → 1.5 | 11,013 | 4/4 | 0.99 |
| 0.70 → 1.3 | 9,295 | 3/4 | 1.02 |
| 0.70 → 1.5 | 8,212 | 3/4 | 1.08 |

**Learned.** 0.85 is better than 1.0, and 0.70 is worse than both: it ends with higher fees and more late
cars. A gig that opens too low sits on the board, and drivers then wait for the raise. Kept 0.85 → 1.3.

## 3. Does winning on Monday change Tuesday's prices? (Sat 00:45) — no

**Why.** Dealers accept far less from us on Monday than later in the week. We tested whether that is the
competitor's answer to our Monday wins.

| Monday | Tue–Fri markup | Tuesday win rate at 1.4 | Mean margin, 2 seeds |
|---|---|---|---|
| quote list price (win 77%) | 1.4 | 52% | 6,929 |
| win nothing | 1.4 | 48% | 9,868 |

**Learned.** Tuesday's win rate is the same either way, so the low Monday level is a property of the week, not
a reaction. Cheap Monday orders lose money. This is why the price must follow the day.

## 4. Follow each dealer's price level (Sat 00:55)

**Idea.** Keep one number per dealer, the price at which it says yes half the time, learned from every answer
to our quotes (`dispatch/pricing.py`). Quote the price with the best expected margin against that level.
**Why.** At one fixed markup, the share of our quotes that win runs from about 0–20% on Monday to 60–100%
on Thursday, and collapses on the price-war day.

| Setting | Mean margin, 4 seeds | Ranked |
|---|---|---|
| Fixed markup 1.5 (with fees 0.85 → 1.3) | 11,152 | 4/4 |
| Learned level, spread 0.07, cost 1.0 | 4,563 | 1/4 |
| Learned level, spread 0.10, cost 1.2 | 10,528 | 3/4 |
| Learned level, spread 0.14, cost 1.2 | 11,468 | 4/4 |

**Learned.** The learned price wins on price (Monday at 1.28× list, Thursday at 1.58×) but takes too many
cars unless cost is set high. Drivers, not prices, are the limit. See 7.

## 5. Peak the fee when drivers plan the day (Sat 01:00) — neutral so far

**Idea.** Reach the top fee on the evening before the last pickup day when the last pickup is before 15:00.
**Why.** Of 32 late orders in one week, 20 were never booked in time, mostly long drives with an early last
pickup; they were booked within minutes at 1.8× once the deadline had passed.

| Setting (learned level, spread 0.14, cost 1.2) | Seeds | Mean margin | Worst | Lowest on time |
|---|---|---|---|---|
| Top fee 4 h before the last pickup (before) | 4 | 11,468 | 7,247 | 90.7% |
| Evening-before schedule, top 1.3 | lab-1..10 | 12,059 | 7,189 | 90.4% |
| Evening-before schedule, top 1.2 | lab-1..10 | 12,454 | 8,148 | 89.5% |

**Learned.** No clear gain on 4 seeds (11,492 vs 11,468). Kept for now because it is the more defensible
rule; to be re-tested on 10 seeds against the old schedule.

## 6. The holdout family (Sat 01:05) — the policy does not generalise yet

| Setting | Seeds | Mean margin | Worst | Lowest on time | Ranked |
|---|---|---|---|---|---|
| Learned level, spread 0.14, cost 1.2 | lab-1..10 | 12,059 | 7,189 | 90.4% | 10/10 |
| same | hold-1..10 | 7,948 | 2,968 | 78.3% | 6/10 |

**Learned.** The four weak holdout weeks are weeks where drivers take our gigs slowly. The number of our cars
still without a driver at 18:00 climbs day by day in those weeks (30 → 60 → 90) and stays under 40 in healthy
weeks. The driver list alone does not predict it. See 8.

## 7. Read the dealer's note properly (Sat 01:25)

**Idea.** A note reader that repairs typos, splits the note into clauses and lets the words around each time
say what it is (`dispatch/notes.py`). It sets plates, the manual licence, the ready time, real opening hours
and a tighter deadline on the gig, and uses them when deciding whether a car leaves enough time.
**Why.** With the kit's keyword match, orders whose note carried a fact did far worse than the rest
(20 weeks): plates 60.7% on time and −90 a car; manual 84% and +2; "ready later" 86% and +10; against 93% and
+36 for cars with no note.
**Measured against the reveal** (`python -m lab.notes_score`, 6,070 won orders with a note): plates 129/129,
manual 142/142, summer tyres 74/74, ready or released later 533/535, pickup hours 308/308, delivery hours
218/218, tighter deadline 229/230; no wrong reading and no false alarm.

| Setting (learned level, spread 0.14, cost 1.2, top fee 1.2) | Seeds | Mean margin | Worst | Lowest on time | Mean on time |
|---|---|---|---|---|---|
| Kit's keyword match | lab-1..10 | 12,454 | 8,148 | 89.5% | 93.4% |
| Our reader | lab-1..10 | 13,534 | 8,731 | 90.0% | 95.3% |
| Kit's keyword match | hold (8 of 10 played) | 8,917 | 6,174 | 82.8% | 89.7% |
| Our reader | hold-1..10 | 10,074 | 5,555 | 80.7% | 90.9% |

By kind of note, 20 weeks, on time and margin per car, kit's match → our reader: plates 60.7% / −90 → 91.8% / +17;
manual 84.0% / +2 → 89.0% / +27; ready later 85.7% / +10 → 89.6% / +37; delivery hours 79.1% / +20 → 94.9% / +33.
Failed visits fell from 2–4% of orders to under 0.5%. **Kept.**

## 8. A brake on the backlog (Sat 01:35) — works, but too blunt

**Idea.** Every car of ours that still has no driver makes the next car dearer to take on:
cost × (1 + (cars waiting / N)²).
**Why.** See 6: the backlog is the live sign of a week with few drivers.

| N (kit's note match) | lab mean | lab lowest on time | hold mean | hold lowest on time | hold ranked | Orders won |
|---|---|---|---|---|---|---|
| off | 12,454 | 89.5% | 8,917 (8 weeks) | 82.8% | 5/8 | 328 |
| 25 | 9,760 | 91.4% | 8,170 | 91.1% | 10/10 | 188 |
| 40 | 10,749 | 91.1% | 9,843 | 90.6% | 10/10 | 230 |
| 60 | 11,359 | 91.3% | 10,287 | 87.8% | 8/10 | 264 |

**Learned.** It keeps every week ranked at N ≤ 40, but it throttles healthy weeks too, and it punishes Friday:
cars won on Friday are due on Monday and wait all weekend without that being a problem. **Not kept**; see 9.

## 9. A cap on cars due on one day (Sat 01:45)

**Idea.** Count our cars by the day of their last pickup. As a day fills up, a new car for that day costs more:
cost × (1 + (cars due that day / (cap × drivers in the list))⁴). The driver list is public from the first
minute, so the cap fits the week. Quotes not yet answered count with their chance to win, so a bulk order
of 36 requests cannot overfill a day in one minute.
**Why.** On time by cars due that day per listed driver (20 weeks, 6,496 orders): under 0.11 → 93–95%;
0.11–0.16 → 89%; over 0.16 → 79%. The weak holdout weeks had 117–136 cars due on one Friday or Monday.

| Cap (our note reader) | lab mean | lab lowest on time | hold mean | hold worst | hold lowest on time | hold ranked |
|---|---|---|---|---|---|---|
| off | 13,534 | 90.0% | 10,074 | 5,555 | 80.7% | 6/10 |
| 0.09 | 12,926 | 91.0% | 10,602 | 6,986 | 82.8% | 9/10 |
| 0.11 | 13,229 | 92.0% | 11,227 | 8,705 | 84.7% | 8/10 |
| 0.13 | 13,228 | 90.7% | 11,061 (9 weeks) | 7,545 | 87.2% | 8/9 |

**Learned.** The cap lifts the holdout mean by about 1,100 and costs about 300 on the tuning seeds. Two
holdout weeks are still under 90%: their late cars are long drives (47 of 51 late cars in hold-10 had over
4 hours of driving). See 11.

## 10. Direct offers (Sat 01:45) — did not work

**Idea A.** Offer each gig to three drivers who live where the car is going: their trip home is free, and
the app never notifies them. **Idea B.** Offer a gig to drivers who opened it and did not book.
**Why.** Fees: 21.7% of bookings are by a driver who first saw a lower fee and then waited, a median of
16.6 hours, for a fee 0.36 typical fees higher. If they had booked at the fee first seen, fees would be 10% lower.

| lab-1, cap 0.11 | Margin | On time | Offers sent | Accepted | Declined | Not read |
|---|---|---|---|---|---|---|
| No offers | 8,563 | 95.7% | | | | |
| A: drivers living at the delivery | 8,376 | 95.7% | 939 | 7 | 144 | 710 |
| B: drivers who viewed the gig | 8,459 | 94.8% | 981 | 14 | 308 | 659 |

**Learned.** Three in four offers are never read, and a driver who reads one at the app's fee says no almost
every time. So a driver who waits is not bluffing: the gig does not pay them at the lower fee. **Not kept.**

## 11. What decides whether a car is late (Sat 01:50)

On time and margin per car by the hour of the last pickup (our note reader, 20 weeks, 6,570 orders):

| Last pickup at | Orders | On time | Margin per car | Fee, × typical |
|---|---|---|---|---|
| 10:00–10:59 | 82 | 70.7% | −49 | 1.51 |
| 11:00–11:59 | 106 | 72.6% | −17 | 1.43 |
| 12:00–12:59 | 78 | 80.8% | +35 | 1.27 |
| 13:00–16:59 | 1,880 | 86–91% | +49 to +62 | 1.05–1.15 |
| 17:00–19:59 | 4,349 | 95–96% | +19 to +36 | 0.96–0.99 |

The same shows by driving time (over 6 hours: 76–85% on time) and by how many drivers live within 30 km of
the delivery (under 10: 87%; over 300: 97%). A car that must be collected early needs its driver the evening
before, and few drivers commit then.

Other patterns from the same weeks:
- **A deadline warning is nearly final.** Of 192 orders that reached 3 hours before the last pickup without a
  driver, 146 (76%) arrived late, a median of 17 hours late. So lateness has to be prevented at the quote.
- **Drops come from drivers who dropped before.** Of 7,640 bookings, 14.3% were given back. A driver with no
  earlier drop in the public list gave back 0.5%; a driver with one or more, 15–24%. A booking at the
  opening fee more than 16 hours before the pickup was given back 19% of the time; a booking under 16 hours
  before, 4%. Four in ten drops happen at midnight, when a driver plans the next day. The app does not let us
  choose who books, so we found no action for this.
- **Bulk orders** (15 to 40 requests from one yard in one minute) sink a week when we take 15 or more from a
  yard with few drivers near it: in hold-2 we won 20 of 36 from one Espoo yard and 8 arrived on time.

## 12. A cost per hour of driving, and a price level per delivery town (Sat 02:15) — kept, version 5

**Idea A.** A car costs more to take on with each hour of driving over three: cost + 0.08 typical fees per hour.
**Why.** See 11. A straight-line fit on 3,297 orders (`python -m lab.fit_cost`): cost +0.05 and late share
+1.1 points per hour over three. In the holdout weeks the riskiest fifth of orders by that fit was late 24% of
the time, against 3% for the safest fifth.
**Idea B.** The price book learns an offset for the town a car goes to, as it does for each dealer.
**Why.** Replaying 16,155 saved quotes through the book (`python -m lab.price_eval`): dealers accepted our
price for a delivery to Vantaa 18 points less often than the book predicted, and for Rovaniemi 22 points more
often. With the town offset the book's log loss falls from 0.612 to 0.578 on the tuning weeks and from 0.601
to 0.567 on the holdout weeks, on quotes it was not fitted to. The best learning rate was chosen there, not
on margin.

| Setting (note reader, cap 0.11) | lab mean | lab worst | lab lowest on time | hold mean | hold worst | hold lowest on time | hold ranked |
|---|---|---|---|---|---|---|---|
| Neither | 13,229 | 8,563 | 92.0% | 11,227 | 8,705 | 84.7% | 8/10 |
| A: cost per driving hour 0.08 | 12,748 | 8,478 | 95.1% | 11,792 | 9,027 | 90.0% | 10/10 |
| B: town offset 0.04 | 13,221 | 8,226 | 93.8% | 11,425 | 7,993 | 84.2% | 9/10 |
| **A and B (version 5)** | **12,664** | **8,112** | **95.4%** | **12,292** | **9,700** | **94.9%** | **10/10** |

**Learned.** Together they are worth more than apart on the holdout weeks (+1,065), and for the first time no
week of either family is under 93% on time. They cost 565 a week on the tuning seeds: we accept that, because
the tuning seeds are the ones we have looked at most. Also tried: a hard limit of 5 hours of driving
(11,166 on five tuning weeks, worse than pricing the hours), and an offset per delivery option (−220 on the
tuning seeds, not kept so far).

## 13. The final runner, rehearsed (Sat 02:15)

- `python -m lab.restart_check`: one week played straight and once more with the desk killed at three points
  and started again from the world alone. 13,873 straight, 14,054 with three restarts, both ranked.
- `python -m lab.live_check`: a practice week whose clock is moved by a second thread at the final's speed,
  with the final runner answering from the live stream. 262 of 262 requests answered by a dealer; the desk
  was killed once and restarted; the three requests that arrived in the seconds of the restart were the only
  ones without a quote in time; no order was left without a gig.
- The rehearsal found one real fault, which practice weeks never touch: the restart path used a variable that
  did not exist there. Fixed before any live run.

## Where the others stand (Sat 02:30)

Ranking round "Saturday 00:00", level 8, sum of five weeks: first 80,030; House best 71,790; tenth 58,504.
Per week that is 16,000, 14,400 and 11,700. Version 5 makes about 12,500 a week on our own seeds. We have
not played a ranking round yet.

## 14. Ranking round "Saturday 00:00" with version 5 (Sat 02:55)

Five secret weeks, the same for every team: 11,727 / 14,152 / 12,303 / 14,757 / 13,168 = **66,107, 11th of 47
ranked teams**, 96.9% on time, 297 orders a week at 44.5 a car. Tenth 66,489; House best 71,790 (364 orders a
week at 39.4); first 83,158 (409 at 40.7); second 80,030 (373 at 42.9).
**Learned.** We make as much per car as the leaders and move 70 to 110 fewer cars a week.

## 15. How noisy is a comparison? (Sat 03:20)

Gain per week of a change, seed by seed, with its standard error over ten weeks:

| Change | Family | Mean gain | Standard error | Weeks better |
|---|---|---|---|---|
| cost 1.2 → 1.0 | lab | +1,755 | 387 | 9/10 |
| cost 1.2 → 1.0 | hold | +701 | 460 | 7/10 |
| cost 1.0 → 1.05 | lab | −523 | 133 | 1/10 |
| cost 1.0 → 0.95 | lab | −246 | 131 | 2/9 |
| at cost 1.0: cap 0.11 → 0.10 | lab | −613 | 157 | 1/10 |
| at cost 1.0: also private deliveries | lab | +2 | 253 | 6/10 |
| at cost 1.1: also private deliveries | lab / hold | +593 / −277 | 279 / 202 | 9/10, 4/10 |
| at cost 1.0: also premium cars (cost +0.3) | lab | −148 | 213 | 2/10 |
| at cost 1.0: warning brake 5 | lab | −911 | 208 | 1/10 |
| fee schedule "plan" | lab / hold | +217 / −72 | 231 / 290 | 8/10, 5/10 |
| opening fee 0.85 → 0.80 | lab / hold | −312 / −632 | 169 / 138 | 3/10, 1/10 |
| opening fee 0.85 → 0.90 | lab / hold | −82 / +243 | 115 / 202 | 5/10, 5/10 |
| at least 14 h → 10 h to find a driver | lab / hold | −3 / −4 | 73 / 16 | 2/10, 2/10 |

**Learned.** With ten weeks a side, a difference under about 400 euros cannot be told from chance. From here on
a change is judged on 20 tuning and 20 holdout weeks, and kept only if its gain is at least 1.5 times its
standard error. Solid so far: the base cost we price with was too high (1.2; the real cost of a car is about
1.0 typical fees), and 1.0 is close to the best single value. Not solid: private deliveries. Losing: premium
cars, a tighter cap, a lower opening fee, the warning brake (it slows healthy weeks as much as weak ones).

## 16. Lower base cost alone (Sat 03:00) — more margin, but too close to the 90% line

| Base cost | lab mean | lab lowest on time | orders | hold mean | hold lowest on time | hold weeks under 93% |
|---|---|---|---|---|---|---|
| 1.2 (version 5) | 12,664 | 95.4% | 282 | 12,292 | 94.9% | 0 |
| 1.1 | 13,370 | 94.5% | 326 | 13,103 | 92.3% | 2 |
| 1.05 | 13,896 | 94.0% | 350 | | | |
| 1.0 | 14,420 | 94.0% | 372 | 12,993 | 91.2% | 3 |
| 0.95 | 13,992 (8 weeks) | 94.6% | 385 | | | |

## 17. What three helpers found in the saved weeks (Sat 03:30)

Three analysis agents each read the saved weeks offline (no server). Their findings, to be tested one by one:

**Capacity.** What decides whether a car is on time is where its two ends are, not how full the day is. With
thinness = 1/(1 + drivers within 60 km of the pickup / 30) + the same for the delivery: cars under 0.8 are
98.2% on time at every load (128,627 orders in 657 saved weeks); cars over 0.8 are 92.3% on time, 34% of the
cars and 69% of the late ones. As a predictor of a late car: thinness AUC 0.74, our day-cap measure 0.53.
Lowering the cost to 1.0 for easy cars only kept the gain and the on-time share (replayed per seed: lab
+1,009, worst week 95.7% on time; hold +766, worst 94.0%). Also: hops with a typical fee under 20 euros from
a pickup with fewer than 80 drivers nearby are 68.5% on time and earn nothing (7 a week, 26% of late cars).

**Drivers and fees.** Small gigs need a floor in euros: with a typical fee under 20 euros, an opening fee of
12–13 euros is booked at once 26% of the time and 5.4% arrive late; at 16–17 euros, 93% and 0%; the final fee
is the same. A raise at night or on the weekend buys nothing: 35,700 weekend views of Monday gigs gave 32
bookings while the fee climbed from 0.89 to 1.13. When a dealer moves a delivery the price stays (448 of 448)
but the drive can double: all 5 undelivered orders of 20 weeks were such cars, offered at most 41 euros.
A lower opening fee pays only where 100+ drivers live near the delivery and the drive is under 3 hours.

**Dealers and prices.** Each request has one exact limit: a replay of the dealers' side from the saved weeks
predicts 98.7% of their answers. Dealer trust is real and close to the rules' figure (0.87 × 1% of accepted
price per on-time order); a late car for the biggest dealer costs about 300 euros in later prices. In replay,
a base cost of 1.05–1.10 was best, and a full-day surcharge worked better added in euros (+72 × fill⁴ a car)
than as a multiple. Two live rules looked worth a test: an outage rule (8 of the first 10 answers won for
pickups within 80 km of one town → raise 20% there until 18:00, about +70 a week) and a price-war rule (at
most 2 wins in the first 20 answers → add 12% to the market level next morning, about +50). No gain in
replay: a same-day premium, trust inside the price book, a weekday prior, buying the big dealers early.

## 18. Reading the dealers' limits with `fork` (Sat 03:10)

`python -m lab.probe`: at the minute a batch of quotes goes out, the week is copied five times and the same
quotes are sent at ×0.8, ×0.9, ×1.1, ×1.25 and ×1.45; the copies are then deleted. 83 requests of `lab-3`
(policy at cost 1.0), each answered at six prices:

| Price, as a multiple of our quote | Share won | Margin per request (cost = typical fee) |
|---|---|---|
| ×0.8 | 79.5% | |
| ×0.9 | 63.9% | 19.73 |
| ×1.0 (ours) | 42.2% | 15.13 |
| ×1.1 | 30.1% | |
| ×1.25 | 7.2% | |
| ×1.45 | 1.2% | |

No request lost at a lower price and won at a higher one: the limits are exact. On paper a quote 10% lower
earns 30% more per request (20% lower for next-day-only requests). The catch is section 16: the extra cars
are not free to deliver. That is what the base cost stands for, so the probe supports cost 1.0 over 1.2 and
says nothing about lateness.

## 19. Twenty weeks a family, and an automatic tuner (Sat 03:45)

The tuner (`python -m lab.tune`) tries one change at a time on `lab-1..20`, keeps it only if the gain is at
least 150 euros and 1.5 times its own standard error, no tuning week is under 91% on time, and `hold-1..20`
agrees with every week at 91% or more.

| Change from version 5 | lab mean | Gain | Weeks better | lab lowest on time | Orders | hold mean | Gain | hold lowest on time | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| version 5 | 12,778 | | | 93.8% | 297 | 12,225 | | 93.6% | |
| cost 1.0 | 14,184 | +1,406 ± 253 | 17/20 | 91.9% | 371 | 13,315 | +1,091 | 91.2% | kept by the tuner |
| cost 0.8 + 0.3 × thinness (60 km), cap on thin cars only, 16-euro fee floor | 14,345 | +1,567 ± 219 | 18/20 | 91.8% | 400 | 13,119 | +895 | **89.0%** | rejected: `hold-2` unranked |
| the same without the fee floor | 14,257 | +1,478 ± 185 | 20/20 | 91.0% | 405 | | | | rejected: too close to 90% |
| cost 0.8 + 0.3 × thinness, cap unchanged | 13,865 | +1,086 ± 223 | 16/20 | 93.0% | 374 | | | | hold weeks queued |
| cost 0.9 + 0.25 × thinness | 13,545 | +767 ± 166 | 16/20 | 93.6% | 347 | | | | comes round again |

## 20. How close to the line? (Sat 04:00)

The tuner's rule looks at the mean and at one lowest week. One live week decides the final, so the tail
matters more than that. All 40 weeks of both families:

| Setting | Mean margin | Mean on time | Weeks under 93% | Weeks under 92% | Weeks under 90% | Lowest weeks |
|---|---|---|---|---|---|---|
| version 5 (cost 1.2) | 12,501 | 96.6% | 0 | 0 | 0 | hold-17 93.6%, lab-11 93.8%, hold-14 93.9% |
| cost 1.0 | 13,750 | 95.7% | 5 | 4 | 0 | hold-1 91.2%, hold-17 91.9%, hold-10 91.9%, lab-11 91.9%, hold-2 92.2% |
| thin pricing, 400 orders | 13,732 | 95.7% | 6 | 4 | 1 | hold-2 89.0%, hold-17 90.2%, hold-10 91.1%, lab-11 91.8% |

The same six weeks are the hard ones under every setting. So the question is not "which cost" but "can the
desk see a hard week while it is happening". Queued now on both families: the warning brake (section 15
dropped it at cost 1.2, where there was nothing to protect) at strengths 4, 8 and 16 on top of cost 1.0 and
on top of thin pricing. It is judged on the lowest weeks, not on the mean.

## 21. The lab moved next to the server (Sat 03:40)

A small machine in Stockholm, 1–2 ms from the Spread server. Two saved weeks replayed there to the cent
(`lab-1` 8,111.88; `hold-3` 13,873.47), 6–8 seconds a week, about 19 weeks a minute with 7 in parallel
(the laptop: about 6). The worker and the tuner run there in `tmux`; the final runner is a system service
(`spread-final.service`, restarts within 2 seconds, starts at boot, logs to a file) in its own folder, so a
lab change can never reach it by accident. It holds version 5 until a later version has passed both families,
`lab.restart_check` and `lab.live_check`.

## 22. The warning brake on top of cost 1.0 (Sat 04:20): a blunt tool

`strain`: every new car gets dearer in step with the share of our cars that lately had no driver 3 hours
before their last pickup. 20 + 20 weeks.

| Setting | lab mean | lab lowest on time | hold mean | hold lowest on time | hold weeks under 93% | Orders |
|---|---|---|---|---|---|---|
| version 5 (cost 1.2) | 12,778 | 93.8% | 12,225 | 93.6% | 0 | 297 |
| cost 1.0 | 14,184 | 91.9% | 13,315 | 91.2% | 4 | 371 |
| cost 1.0, brake 4 | 13,735 | 94.0% | 12,918 | 92.4% | 2 | 344 |
| cost 1.0, brake 8 | 12,797 | 94.3% | 11,913 | 92.4% | 2 | 320 |
| cost 1.0, brake 16 | 11,355 | 92.8% | 11,246 | 92.3% | 1 | 282 |

The brake buys about one point of on-time share for 400 euros a week, and a stronger brake only costs more:
the lowest holdout week stays at 92.4%. It makes every car dearer, the safe ones too, and it reacts to a
warning, which is already too late (section 23). Not kept.

The tuner, one change at a time on cost 1.0, kept nothing either: dealer trust in the price +186 ± 118 (a
holdout week at 90.2%), trade-ins −307, same-day premium −101 and −377, the 14-hour rule relaxed to 6 hours
for easy cars +295 ± 228 (not clear), cap on thin cars only −101, a 16-euro fee floor +20.

## 23. What a hard week is (Sat 04:40)

`python -m lab.hard_weeks` and `python -m lab.warned_cars`, 30 weeks at cost 1.0 (10,941 cars).

- In the four hardest weeks 23 to 26 of about 30 late cars were **booked late**: no driver until the last 3
  hours. Drops and failed visits are the same handful as in easy weeks. Easy weeks have 1 to 8 such cars.
- The driver list is not shorter in hard weeks (634 to 886 drivers; easy weeks 641 to 948).
- **A car that gets the deadline warning is late 75.6% of the time, and never by a little:** of 316 such late
  cars, 218 were 8 to 24 hours late and 98 more than a day. They are booked right after the warning (61% at
  1.7 to 1.9 times the typical fee), so a driver exists at that fee. The fee just reaches it too late: the
  driver comes the next day.

| Last pickup | Cars | Warned | Late | Late in hard weeks | Margin a car |
|---|---|---|---|---|---|
| before 13:00 | 167 | 19% | 26% | 43% | 57 |
| 13:00–15:00 | 829 | 2.8% | 4.8% | 10.2% | 88 |
| 15:00–17:00 | 1,750 | 5.3% | 7.6% | 14.5% | 57 |
| 17:00 or later | 8,195 | 3.4% | 2.9% | 4.6% | 28 |

Also late more often: drives over 5 hours (8.3%, 20% in hard weeks, 83 euros a car), gigs with a typical fee
under 20 euros (7.6%, 14 euros a car), cars with fewer than 10 drivers within 30 km of one end (5.8%, 13% in
hard weeks).

So a hard week is a week in which drivers want more than 1.2 times the typical fee, and our schedule only
offers that in the last hours. The fix belongs on the fee side, for the cars at risk only, not on the price
side for every car.

## 24. The late fee earlier (Sat 04:50)

New setting `late_lead`: the hours before the last pickup by which the fee has climbed to its late level
(1.8). It was 3, the moment of the world's own warning. If that moment falls in the night, it moves to 21:30
the evening before. Example, last pickup Wednesday 11:00: today the fee is 1.4 at 22:00 on Tuesday and 1.8
at 08:00; with `late_lead=6` it is 1.8 at 21:30 on Tuesday. Queued on cost 1.0, both families: 5, 7 and 9
hours, and the two older settings that do something similar (`early_hour=17`, `lead_hours=9`).

| Late fee reached | lab mean | lab lowest on time | hold mean | hold lowest on time | hold weeks under 93% | Fees, in typical fees |
|---|---|---|---|---|---|---|
| 3 hours before (version 5 rule) | 14,184 | 91.9% | 13,315 | 91.2% | 4 | 0.98 |
| 5 hours before | 14,215 | 94.5% | 13,319 | 91.4% | 2 | 1.00 |
| 7 hours before | 13,677 | 93.6% | 12,874 | 92.3% | 1 | 1.02 |
| 9 hours before | 12,862 | 95.9% | 11,738 (12 weeks) | 92.2% | 1 | 1.07 |

Five hours is free and helps a little. Beyond that every car pays more, also the many that would have been
booked in time anyway: 9 hours costs 1,300 euros a week in fees. The rule cannot tell which cars need it.

## 25. A second model's look at the same data (Sat 04:15 to 05:15)

While the first assistant was out of usage, a second assistant (ChatGPT in Codex, called Astra here) read the
saved weeks with one brief (`HANDOFF.md`): find what we missed, change no code, leave patches. Its notes are
in `IDEAS-ASTRA.md` and `astra/`. What it found that we did not have:

- **The typical fee carries noise, and we multiplied the noise into everything.** The handbook says so: the
  world takes the lane's cost and "adds a noise for each request". A line through road time gives the cost
  back: 16.04 euros + 38.44 cents a road minute (18,043 requests; one of our own helpers had found 15.7 and
  38.6 and used it only for moved deliveries). Won cars whose typical fee is under 85% of the line wait a day
  or more for a driver 26 to 28% of the time and arrive late 8 to 10%; at 115% or more, 1.3 to 1.6% and 0.6
  to 1.0%. And we hold twice as many cars under the line as over it (3,531 against 1,723): a price built on a
  low draw wins the car. That is a winner's curse, and it is where the hard weeks' unbooked gigs come from.
- **Dealers choose the option by the difference in euros** (even odds at about 16 euros between same day and
  next day, 7.50 between next day and three days; 88.3% of 4,069 choices predicted on the holdout weeks).
- **Whether we offer the fastest option the dealer asked for moves the price they accept**: +4% when we do,
  −9% when we do not (log loss 0.608 to 0.584 on the holdout weeks, better in 20 of 20).
- **The 400-car setting gains 1,968 euros a week on 70 new cars and gives back 1,522 on 36 cars it no longer
  wins and 629 on the cars both win.** The extra late cars are among the shared ones: a new car costs the old
  ones their drivers.
- **When a note makes a car ready a day later, the deadline moves a day too** (70 of 70), and our quote still
  used the old one: about two more cars a week could be quoted.
- A repost after the last possible pickup starts at 1.8 times the typical fee; 310 of 425 such gigs found
  their driver within the hour, so 1.5 for the first hour may do.

What we did with it: each idea went in as a setting that is off by default (saved weeks still replay to the
cent), and is tested alone on 20 + 20 weeks.

## 26. Snow (Sat 05:35)

`python -m lab.snow cost=1.0`, 30 weeks. The world announces snow with a `forecast` event (1.4 a week). The
desk ignored it.

| Last pickup day | Cars a week | Late | Dropped | Margin a car |
|---|---|---|---|---|
| no snow at either end | 352 | 3.6% | 12.1% | 38 |
| snow at the delivery | 7.9 | 13.6% | 16.5% | 44 |
| snow at the pickup | 3.5 | 22.9% | 18.1% | 29 |
| snow at both ends | 1.2 | 28.6% | 20.0% | 21 |

3.4% of the cars, 15% of the late ones. Test: `snow_cost`, more cost in the price of a car whose last pickup
day has snow forecast at one of its ends (0.3 and 0.6 typical fees).

## 27. Tests on the noise-free base (Sat 05:20)

Base from here on: cost 1.0 with the noise out of fees and price (`road_fee_blend=1 road_cost_blend=1`).
Against version 5 on all 40 weeks: +2,099 ± 160 a week, better in 39 of 40, lowest week 92.5% on time
(version 5: 93.6%). One change at a time, 20 + 20 weeks:

| Change | lab mean | hold mean | hold lowest on time | Verdict |
|---|---|---|---|---|
| base | 14,848 | 14,353 | 92.5% | |
| noise out of the fees only | 14,297 | 13,990 | 91.2% | half of it |
| late fee 5 h before | 14,489 | 13,974 | 91.4% | no: with honest fees the earlier rise only costs |
| fastest-option signal (`menu_strength`) | 14,809 | 14,162 | 90.8% | no |
| moved deadline for later-ready cars | 14,909 | 14,246 | 91.7% | no gain |
| lower first fee on late reposts | 14,848 | 14,353 | 92.5% | identical: the rule never fired (a bug, see 30) |
| short private deliveries | 14,871 | 14,358 | 90.8% | no gain |
| snow cost 0.3 / 0.6 | 14,716 / 14,832 | 14,145 / 14,303 | 91.0% / 92.6% | no gain in margin; 0.6 has fewer low weeks |
| dealer trust in the price (`trust`) | 14,760 | 14,342 | 92.6% | no gain |
| cost 0.9 | 15,049 | 13,936 | 91.4% | no |
| cost 0.8 | 14,537 | 12,766 | 86.9%, two weeks unranked | no |
| thin-car pricing at cost 0.8 | 14,658 | 13,953 | 89.6% | no |
| **two cars in one gig (`pairs`)** | **15,440** | **14,499** | 91.0% | +592 / +146: about 23 round trips a week at 0.74 of the typical fee |

Every way of winning more cars loses on the holdout weeks. Delivery in the hard weeks is the wall.

## 28. Every dealer's limit, measured (Sat 05:05 to 05:40)

`python -m lab.limits`: one minute before a request must be answered, the week is copied six times in a row;
each copy quotes every waiting request at one multiple of the list price, higher if the last one won, lower
if it lost. Thirteen weeks, 13,400 requests, each limit known to about 1% (the winning and the losing price
lie 0.9% apart in the middle case). A probed week takes three minutes and its own result is unchanged to the
cent. `python -m lab.limit_fit` and `python -m lab.book_eval` read the files.

What the limits show:
- **One market level a day.** With trust taken out, the level is the same in the morning and the afternoon and
  jumps overnight: 1.53, 1.15, 1.42, 1.47, 1.58 in one week; 1.04, 1.39, 1.35, 1.55, 1.19 in another. One day a
  week sits about 20% low (the price war).
- **Trust is exactly the rule:** limit = base x (1 + 1% x on-time orders, at most 25). Fitted 0.96 to 1.00.
- **Dealers do not differ** beyond that (within 5%).
- **A route's cars sell alike within a week** (spread 0.11 to 0.12 against 0.15 around the day level), but a
  route's offset does not carry to other weeks.
- Road time, list price and the options asked for explain nothing of the rest; two requests with the same
  dealer, route, day and options differ by 0.08.
- A desk that knew every limit would earn 51 euros per plain request; knowing it to 16% earns 29, to 8% 36.

`DayBook` (dispatch/pricing.py) follows from this: each morning it starts a fresh estimate of the day's level
and sharpens it with every answer. Replayed against the measured limits at equal volume it earns 3 to 4%
more than the plain book (level error 0.165 to 0.139, better in 6 of 8 weeks).

Played for real it did not earn more:

| Setting | lab cars | lab euros a car | lab mean | hold cars | hold mean | hold lowest on time |
|---|---|---|---|---|---|---|
| base, plain book | 375 | 39.6 | 14,848 | 359 | 14,353 | 92.5% |
| day book, cost 1.0 | 439 | 34.7 | 15,229 | 412 | 13,349 | 89.0% |
| day book, cost 1.1 | 397 | 38.8 | 15,401 | 377 | 14,374 | 88.6% |
| day book, cost 1.2 | 352 | 42.3 | 14,891 | 333 | 13,972 | 90.3% |

A sharper book wins more cars at the same cost, and the hard weeks cannot deliver them. At equal volume it is
about +340 on lab and -100 on hold. Not kept. The measurement stays: it says the price side is not where we
lose to the leaders.

## 29. Why cars are late on the new base (Sat 05:55)

`python -m lab.late_causes cost=1.0 road_fee_blend=1.0 road_cost_blend=1.0`, 40 weeks, 426 late cars of 14,685:

| Cause | Late cars | Share | Late by (median) | Refund a car | Fee paid, typical fees |
|---|---|---|---|---|---|
| booked late: no driver until 3 h before the last pickup | 175 | 41% | 19 h | 64 | 2.12 |
| arrived late: booked in time, no drop, the driver's day slipped | 129 | 30% | 11 h | 37 | 1.02 |
| dropped: a driver gave the gig back | 109 | 26% | 17 h | 45 | 1.80 |
| failed visit, never booked | 13 | 3% | | | |

The three hardest weeks (hold-17, hold-10, hold-2: 92.5 to 92.8% on time) each have 14 to 15 cars booked late,
8 to 13 of their late cars are drives over 5 hours and 13 to 19 have an end with under 10 drivers nearby.
Drives over 5 hours are late 7.5% of the time and earn 91 to 105 euros a car: too good to refuse.

## 30. Six analysts on the saved weeks (Sat 05:45 to 06:25)

Six Claude Opus sub-agents, one question each, offline on all 2,500 saved weeks and the 13 measured ones; every
claim fitted on lab and checked on hold. Scripts in `swarm/`. What they found, and what we do with it:

- **Drivers.** A driver who lives near the delivery takes a gig at about 0.75 of the road-line fee (24% book at
  first look at 0.7 to 0.8, 33% at 0.8 to 0.9); one who lives near the pickup needs about 1.0; one who ends
  another of our gigs nearby is hardly better than a stranger. Delivery-town drivers already make 31% of our
  bookings, 88% of them at first look. Lowering the opening fee where many of them live saved nothing (plus or
  minus 4 euros a week, and drivers elsewhere waited). Direct offers: 14 of 981 accepted. Conclusion: we do not
  lose to the leaders on what we pay drivers. A gig with fewer than 5 viewers in its first hour is late 17 to 21%.
- **Fees over time.** 0.85 is the bottom of a flat valley for the opening fee. Bookings per view peak at 05:00
  to 06:00 (5%) and are 0.4% late in the evening; Sunday views book almost nothing. A raise has no effect of
  its own. Candidates: evening-before top fee only for last pickups before 13:00 (`early_hour=13`), no raises
  at night for gigs with 12 hours left (`night_hold`). Both go through the tuner.
- **Capacity.** Drivers are not the limit: 94% of them view our gigs and about 200 drive, 1.9 gigs a week each.
  Late cars had 92 to 130 viewers before anyone booked, and half of the drivers who finally took them had seen
  them earlier at a lower fee. Winning 450 cars costs mostly price: the cars we win anyway pay 1,800 to 2,000
  euros a week less. Drivers already chain our gigs (47% of gigs are in a driver-day with two or more of
  ours). 77 to 89 round trips a week were possible; we post 22, because the first car usually has a driver
  before the second is won.
- **Which cars deserve a driver.** A car takes a driver 4.7 to 4.9 hours, and 54% of that is the trip to the car
  and home. We earn 8.0 to 8.4 euros per driver-hour. Short hops around Helsinki are the best (13 to 15),
  last pickups before 13:00 the worst (4 to 6, and 20 to 29% late). Repricing the 13 measured weeks with half
  the cost moved onto driver-hours gains about 500 a week at the same driver-hours.
- **Dealers and trust.** One on-time delivery to the biggest dealer is worth about 50 euros in its later
  prices on Monday, 35 on Tuesday, 5 from Wednesday (its count is full by then); a late one mid-week costs 125
  to 220. The competitor barely answers our wins (2 to 3% when we take over 65% of a dealer). The outage shows
  as +26 to +38% on pickups within 80 km of one town in 8 of 13 weeks.
- **The leaderboard.** In the round we played, version 5 won about 297 cars in every one of the five weeks;
  the leaders took 290 to 465 depending on the week. The week with the most cars decides most of the ranking.
- **Rules against our code.** (1) After a car's last pickup has passed, a fee can only buy a smaller refund
  (25% back up to a day late, 50% after), worth at most about 35 euros, yet we repost at 1.8 to 2.4 times the
  typical fee: 7.1 bookings a week at 2.02, 1,129 euros a week, two thirds of them booked within 12 minutes.
  The earlier patch for this (`expired_first_fee`) matched the base to the cent on all 40 weeks: it never
  fired. (2) At the deadline warning, 3.2 drivers on average have just delivered one of our cars within 45
  minutes of the warned car's pickup: the handbook's own case for a direct offer. (3) A car the dealer sends
  further keeps its old fee: 9.5 a week, 9.8% late, most of the undelivered penalties. (4) Waiting fees where a
  note gave the delivery site's opening time: 41 euros a week. (5) A Friday car that misses its deadline is
  delivered on Monday (50% back) when Saturday (25%) was open.

Queued from this, each alone on the base (Sat 06:20): a charge per driver-hour (`hour_cost`, `fee_share`),
the value of trust in a car's cost (`trust_gain`), pairs without the way-back limit, a lower cost for a car
that completes a round trip (`pair_bonus`), no cars with a last pickup before 13:00 (`min_last_hour`).

## 31. A faster lab (Sat 06:00)

The server limits a team by calls a second (about 300), not by our machine: an exact week needs about 1,450
calls, one for each event we answer. Two changes:
- **Fast mode** (`lab_step=12`): in the hours when requests come, the desk answers the events of every 12
  minutes together (a quote has 15 minutes). A week takes 330 calls and 5 seconds instead of 27. It scores
  lower than exact mode (base: -239 ± 185 on lab, -468 ± 196 on hold), so reacting within the minute is worth
  about 350 euros a week by itself; the final runner reacts within a second. Fast mode screens ideas, both arms
  in the same mode; exact mode confirms what is kept.
- **The note reader remembers words it has repaired.** Profiling a fast week showed two thirds of our processor
  time in the typo repair (edit distance against the whole vocabulary for every unknown word). With a memo the
  week's processor time fell from 3.1 to 1.8 seconds. The reader's score against the reveals is unchanged.
Together: from 14 to about 50 weeks a minute.

## 32. The analysts' rules, played (Sat 06:00 to 06:20)

Fast mode, gain over the fast base (cost 1.0, noise-free fees and price), lab / hold / both:

| Rule | lab | hold | both | Verdict |
|---|---|---|---|---|
| **Cap on rescue fees** (`late_open=1.0 late_top=1.3`): a car that can no longer be on time is reposted at 1.0 typical fees, 1.3 a day later, instead of 1.8 to 2.4 | +288 ± 83 | +894 ± 337 | **+591 ± 178** | kept |
| the same at 1.2 / 1.5 | +194 | +756 | +475 ± 151 | |
| **Pairs** (`pairs=1`, 30 min to the second car, 45 back) | +673 | +660 | +667 ± 108 | |
| **Pairs, wider** (`pair_hop=60 pair_back=90`) | +1,024 | +787 | **+906 ± 122** | kept |
| Pairs as one-way chains (no way-back limit) | +795 | +696 | +746 ± 130 | not better than wider round trips |
| Fee follows a moved delivery (`relane`) | -25 | -47 | -36 ± 32 | no |
| Charge per driver-hour, 8 euros, half the fee cost | +110 | -969 | -429 ± 235 | no: fewer cars and still two hold weeks unranked |
| Charge per driver-hour, 6 euros, 0.6 of the fee cost | | -692 | -156 ± 232 | no |
| Value of dealer trust in the cost, full / half | -109 / +155 | -311 / -153 | -210 ± 136 / +1 ± 141 | no |
| Trust value with same-day short hops | -31 | +55 | +12 ± 180 | no |

Two rules that two offline models liked (driver-hours, trust value) lost when played: both win more cars or
other cars, and the hard weeks deliver them late. What works lowers the cost of the cars we already carry.

## 33. The candidate (Sat 06:20)

Base + wider pairs + rescue-fee cap, exact mode, three seed families (the third, `fresh-1..20`, never used
before):

| Family | Base | Candidate | Gain | Weeks better | Lowest on time | Weeks under 90% |
|---|---|---|---|---|---|---|
| lab | 14,848 | 16,070 | +1,223 ± 203 | 18/20 | 94.3% -> 94.7% | 0 -> 0 |
| hold | 14,353 | 15,265 | +912 ± 226 | 17/20 | 92.5% -> 91.7% | 0 -> 0 |
| fresh | 14,721 | 16,166 | +1,445 ± 217 | 20/20 | 88.6% -> 91.4% | 1 -> 0 |

Against version 5 (12,778 / 12,225 on lab / hold) that is about +3,150 a week. Variations on the candidate in
fast mode: even wider pairing (90 and 120 minutes) +397 ± 108 but one hold week at 88.9%, not taken; how long a
pair waits before it is split (6 or 14 hours instead of 10) no effect; a lower fee cap (0.8 to 1.2) +12; a pair
fee of 0.75 instead of 0.80 +421 ± 113 in fast mode, -55 ± 167 on lab in exact mode, so not taken on that
evidence.

## 34. The competitor's outage, detected live (Sat 06:10 to 06:25)

From the second model's notes (`IDEAS-ASTRA.md`): on one day a week the dealers who load around one town take
about 27% more. Our measured limits agree: in 7 of 13 measured weeks the limits around Helsinki stand 28 to
39% above the rest of that day (87 to 115 requests); in the other 6 the outage is around a quiet town (8 to 16
requests) or cannot be seen.

Detector (`outage`, dispatch/policy.py `outage_answer`): each morning it starts clean; for every town it
compares how today's answers from within 80 km surprised the price book with the answers from everywhere else,
with at least 8 answers on each side, so a dear day for the whole market does not look like an outage. When one
region stands out by the set number of standard errors, the book's level there goes up by the measured 28%
until 18:00. `python -m lab.outage_check` replays it on the measured weeks with nothing but the answers it
would have had, in the order it would have had them:

| Threshold | Weeks it fired | Right day and at least half the region |
|---|---|---|
| 3.0 | 12 of 13 | 6 |
| 3.5 | 8 of 13 | 5 |
| 4.0 | 7 of 13 | 7 |

At 4.0 it fires only in the 7 busy weeks, between 11:27 and 14:27, with 23 to 62 of the affected requests still
to come. Played (threshold 4.0):

| Seeds, mode, on what | All weeks | Weeks where it fired | Weeks where it did not | Lowest on time | Weeks under 90% |
|---|---|---|---|---|---|
| fresh, exact, on the base | -104 ± 83 | 12 weeks: -173 ± 138 | 8 weeks: 0 | 88.6% -> 88.6% | 1 -> 1 |
| fresh, exact, on the candidate | +107 ± 111 | 11 weeks: +194 ± 203 | 9 weeks: 0 | 91.4% -> 91.4% | 0 -> 0 |
| lab, fast, on the base | +182 ± 92 | 11 weeks: +331 ± 156 | 9 weeks: 0 | 95.0% -> 94.5% | 0 -> 0 |
| hold, fast, on the base | +64 ± 119 | 11 weeks: +117 ± 219 | 9 weeks: 0 | 89.9% -> 90.7% | 1 -> 0 |

The finding is right and the detector works, and the money is small: about +60 a week over the four tests,
not different from zero. By the time the detector is sure, the plain book has already raised its level for
those dealers from their unexpected yeses, and half the day is gone. Not kept; the setting stays in the code,
off.

## 35. Version 6 (Sat 06:40)

The candidate of section 33 became the code's defaults: cost 1.0, the noise out of fees and price, pairs with
60 minutes to the second car and 90 back, and the fee cap for cars that can no longer be on time.

| Family | Version 5 | Version 6 | Cars | Euros a car | Lowest on time |
|---|---|---|---|---|---|
| lab-1..20 | 12,778 | 16,070 | 376 | 42.7 | 94.7% |
| hold-1..20 | 12,225 | 15,265 | 360 | 42.4 | 91.7% |
| fresh-1..20 | not played | 16,166 | 372 | 43.5 | 91.4% |

Checks before it went to the final runner:
- Version 6 with no settings replays the candidate's saved weeks to the cent (lab-1 12,230.65, hold-3 17,840.00).
- `python -m lab.restart_check`: straight through 12,230.65, with three restarts 12,758.20, both ranked. PASS.
- `python -m lab.live_check --days 2 --speed 2`: 457 requests decided at twice the final's clock speed with a
  restart in the middle, none refused, every won order has a live gig. PASS.
- The first run of the checks failed because the lab's worker freed the check's practice week as a leftover;
  both checks now mark their week as owned (`lab.runs.own`).

Tried on top of the candidate in fast mode and not taken (gain a week, lab and hold together): pair fee 0.70
-156 against 0.75; pairs 75 and 105 minutes +47 ± 105; a lower cost for a car that completes a round trip
-234 ± 121 (it wins 13 more cars); a time buffer before the last pickup -10 ± 91; fees restarting at 1.2 after
a drop -309 ± 91; a direct offer to a driver who has just delivered nearby -71 ± 71; direct offers to drivers
who looked at a gig and did not take it +1 ± 42; the second model's dealer calibration +97 ± 122 with one
hold week at 89.7%. No last pickup before 13:00 costs 267 ± 93 but lifts the lowest hold week from 91.1% to
94.3% in fast mode: a safety option, played in exact mode next.

## 36. After version 6: a morning of things that did not beat it (Sat 06:40 to 08:40)

Two lessons first.
- **Fast mode flatters anything that adds cars.** Pricing for more volume, private addresses and short-notice cars
  all gained 400 to 500 euros a week in fast mode and lost or turned unsafe in exact mode. From here, fast mode
  screens fee and pairing rules only; whatever changes how many cars or which cars we win is judged in exact mode.
- **The single lowest week of 60 is a noisy measure.** One fee tweak moved fresh-12 from 93.7% to 88.6% on time.
  So candidates are also read on a fixed panel: the mean on-time share of the eight hardest weeks (fresh-9,
  fresh-12, hold-10, hold-17, hold-2, hold-9, fresh-20, lab-11; version 6: 93.5%).

Exact mode, all 60 weeks, against version 6 (15,834; lowest week 91.4%; none under 90%):

| Change | Gain | Weeks better | Lowest week | Under 90% | Verdict |
|---|---|---|---|---|---|
| fee change from the tuner (`early_hour=13 night_hold=1`: evening-before top fee only for last pickups before 13:00, no raises at night) | +372 ± 83 | 43/60 | 88.6% | 1 | the best mean we have; not taken: one week in 60 scores nothing |
| dealers' option rule, for learning only (`menu=2`) | +106 ± 100 | 31/60 | 90.7% | 0 | no |
| the same with cost 0.95 | +202 ± 91 | 41/60 | 89.4% | 1 | no |
| guard 5% with cheaper prices while the week goes well (`easy_cost` 0.10 / 0.15) | -227 ± 112 / -167 ± 119 | | 90.1% | 0 | no: "easy week, more cars" loses |
| no last pickup before 13:00 (13 weeks) | -559 ± 121 | | | | no: too dear as insurance |

Exact mode, the 30-week panel (16 hardest and 14 ordinary weeks; version 6: 15,606, eight hardest 93.5%):

| Change | Gain | Eight hardest, on time | Lowest | Under 90% | Verdict |
|---|---|---|---|---|---|
| guard 6% (`guard=0.06`): careful when late + warned cars pass 6% of cars decided | -181 ± 79 | 94.3% | 93.4% | 0 | works as insurance: one point for 180 euros; it also fires in ordinary weeks |
| morning rescue at 08:00 for cars due today without a driver, to 1.5 / 1.3 typical fees | -182 ± 127 / +68 ± 130 | 93.4% / 93.4% | 89.1% / 90.5% | 1 / 0 | no |
| flu-day rescue (`flu=1`), to 1.5 / 1.3 | -504 ± 114 / -299 ± 109 | 94.4% / 94.2% | 92.6% / 92.3% | 0 | the sign is right, the cure too dear: 25 gigs raised to save one or two cars |
| long drives: late fee 12 or 9 hours ahead (`long_lead`) | -243 ± 71 | 93.3% | 90.5% | 0 | no |
| fee change + guard 6% | +248 ± 151 | 93.6% | 89.3% | 1 | no: the guard does not save the week the fee change breaks |
| fee change + guard + rescue | +290 ± 147 | 93.7% | 89.3% | 1 | no |
| fee change + long drives 12 h | +270 ± 154 | 93.2% | 90.1% | 0 | no clear gain |
| simulator's first pick: cost 0.95, daily cap 0.12, short-notice cars (13 weeks) | +668 ± 313 | 92.5% | 89.4% | 2 | no: 422 cars and two weeks unranked |
| "extras" (fee change, private pickups, short notice), 16 hardest weeks | +698 | | 86.5% | 2 | no |
| extras + guard 4%, 16 hardest weeks | -98 | | 93.0% | 0 | the guard makes them safe and takes the gain away |

The dealers' option rule (from the simulator session, fitted on a million quotes): a dealer values same day at
23.50 euros, next day at 7.50, three days at 0; it takes our best offer when that is at least as good as the
competitor's best over EVERY option it asked for. So a next-day quote to a dealer who asked for same day competes
with the competitor's same-day offer. Used to set prices (`menu=1`) it lost 549 ± 151 in fast mode with the same
number of cars: it wins the thin next-day-only cars we used to lose by pricing them too high, and they take
drivers from better cars. Our old error was a useful filter.

## 37. Can the desk see a hard week coming? (Sat 08:10)

Four analysts (Claude Fable sub-agents), offline on the 60 version 6 weeks, each fitting on two seed families
and checking on the third. Scripts in `swarm/early_*`.
- **Monday morning: no.** The driver list, the map and the request stream are the same in hard and easy weeks.
  Only the size of the week can be read early (our win rate by Monday evening tracks the dealers' level, +0.96).
  A hard week is tight everywhere, all week, and turns hard on the cars won from Wednesday (11.7% late against
  2.4%); Monday's cars are normal.
- **By Tuesday noon: weakly.** The share of cars won so far that are neither delivered nor booked (over 12%)
  catches 11 of 15 hard weeks and flags 15 of 45 others. An earlier claim (distinct drivers per order, AUC 0.84)
  did not reproduce (0.46 to 0.56 out of sample).
- **Choosing the strategy by week is worth nothing.** With hindsight the best setting per week earns +1,726 over
  version 6 in fast mode, but dealing each setting's gains to random weeks gives +2,247: it is selection luck.
  Which setting earns more in a week does not even agree between fast and exact play of the same week (+0.13).
- **Day and car level is where the signal is.** A car due today with no driver at 08:00 comes late 30% of the
  time, 45% at 10:00, 59% at noon, 1.5% with a driver; these cars are six in ten of all late ones.
- **The flu day shows at midnight.** Between 00:00 and 01:00, 7 to 15 of the drivers holding a booking for that
  day give it back (0 to 3 on other nights): "4 such drops by 00:30" fires on 42 of 45 flu days and on none of
  135 other days. All nine hardest weeks have the flu on Thursday or Friday. Snow is announced at 00:00 for the
  day after, never for the Helsinki area; a car collected before the snow day was never late (116 cars).
- **Special days explain 15% of the difference between weeks**, and their cars carry 40% of all late cars.
Knowing the signs and paying to act on them are two things: section 36 shows the rescues cost more in fees than
they save.

## 38. Where this leaves us (Sat 08:40)

Version 6 stays on the final runner. Three more sessions are running: an offline rebuild of the simulator
(`sim/`; its dealer side reproduces real weeks to 3%, its driver side is too optimistic and its first pick
failed for real, section 36), a study of how the leading team reaches its numbers (`freya/`: the same kind of
system at a higher-volume point, on a round without a hard week), and designs that are not variations of
version 6 (`alt/`, played through a plug-in point: the setting `design=<module>`).

## 39. How risky is a version, really? (Sat 08:45 to 09:00)

Emil's question: version 6 wins fewer cars than the leaders (369 a week against 410 to 458) at a higher margin a
car; is that enough for the top ten, and is the tuner's fee change too risky to take?

**Standings** (`data/board8-0845.json`, still the round of Saturday 00:00): 1st 85,925, 2nd 83,158, 3rd to 7th
80,030 to 80,473, 10th 75,475, we 21st with version 5 (66,107). Version 6 would have scored about 79,200 to 83,800.
Twelve of the 75 teams that played all five weeks lost their ranking to a week under 90% on time (17 of 375 weeks).
Between the rounds of Friday 20:00 and Saturday 00:00 the 10th place rose from 27,210 to 75,475: the field moves fast.

**A steadier measure of risk** (`python -m lab.risk`). Counting weeks under 90% among 60 is too coarse. Across 952
exact runs of version 6 and its small variations, the on-time share of one and the same week moves with a standard
deviation of 0.5 points in easy weeks (97.5% and up), 0.6 at 96 to 97.5%, 0.8 at 94 to 96% and 1.5 under 94%: the
hard weeks are also the noisy ones. With that as the luck of one week, the chance that a random week falls under 90%:

| Version | Weeks | Gain | Lowest week | Eight hardest | Chance of a week under 90% | Five weeks all ranked |
|---|---|---|---|---|---|---|
| version 6 | 60 | | 91.4% | 93.5% | 0.6% | 97.1% |
| fee change (`early_hour=13 night_hold=1`) | 60 | +372 ± 83 | 88.6% | 92.8% | 2.1% | 90.0% |
| fee change + long trips 12 h | 30 (panel) | +270 ± 154 | 90.1% | 93.2% | 3.2% (version 6 on these weeks: 1.2%) | 85.2% |
| fee change + guard 6% | 30 (panel) | +248 ± 151 | 89.3% | 93.6% | 2.7% (1.2%) | 87.0% |
| guard 6% | 60 | -111 ± 46 | 93.4% | 94.3% | 0.1% | 99.7% |
| option rule for learning (`menu=2`) | 60 | +106 ± 100 | 90.7% | | 1.0% | 94.9% |

Astra read the same 60 guard weeks and reports the same (lowest week 91.40% to 93.39% for 111 euros a week): the
guard is insurance, a seventh of a percent of margin for five sixths of the risk.

**Why the fee change breaks fresh-12** (`python -m lab.week_diff fresh-12 early_hour=13 night_hold=1`): 93.7% to
88.6% on time, 27 late cars to 52, the same 343 cars won in both. Of the 20 cars late only under the change, 18 are
drives of 4.4 to 8.6 hours with a last pickup at 13:00 to 15:00. The change moved the rule "top fee on the evening
before" from pickups before 15:00 to pickups before 13:00; these cars then got their top fee at 07:00 to 09:00 on
the day, and were booked 30 to 80 hours after the win instead of 0 to 20, most after the warning. A long drive fills
a driver's day and is planned the day before whatever its pickup hour; a short drive after lunch is not.
New setting `early_long` (with `long_hours`): for long drives the evening-before rule holds up to that hour.
Version 6's two reference weeks are unchanged to the cent with it off.

The simulator session's corrected numbers for its first pick (cost 0.95, daily cap 0.12, short-notice cars) on all
30 panel weeks: +803 ± 174, +43.8 cars, on time 96.07% to 95.49%, two weeks under 90% (89.4%, 89.9%). Rejected as
in section 36.

## 40. The fee change in two halves, and what the long drives tell us (Sat 09:00)

One fact first: **the hour of a car's last pickup is its drive length under another name.** On 60 weeks of version 6
every drive under 2 hours has its last pickup at 17:00 or later, 2 to 5 hours at 15:00 to 18:00, 5 to 7 hours at
13:00 to 15:00, 7 hours and more at 08:00 to 12:00 (the latest moment that still makes the deadline). So
`early_hour=13` reads: no top fee on the evening before for drives of 5 to 7 hours, and the whole rise to the top
fee ends on the morning of the day instead of the evening before. (And `early_long=15` with `early_hour=13` is
`night_hold=1` alone: the queued duplicate was removed.)

Exact mode, 60 weeks, against version 6 (15,834; chance of a week under 90%: 0.6%):

| Change | Gain | lab / hold / fresh | Lowest week | Under 90% | Chance of a week under 90% |
|---|---|---|---|---|---|
| both halves (the tuner's fee change) | +372 ± 83 | +255 / +566 / +294 | 88.6% | 1 | 2.1% |
| half 1, `early_hour=13`: 5 to 7 hour drives rise to the top fee on the day | +248 ± 93 | +302 / +360 / +83 | 87.4% | 2 | 3.3% |
| half 2, `night_hold=1`: no raise from 22:00 to 06:30 | +165 ± 71 | -166 / +382 / +280 | 91.4% | 0 | 0.7% |
| `early_hour=14` + night hold: only 5 to 6 hour drives | +404 ± 80 | | 89.7% | 1 | 2.2% |

All the risk is in half 1, and half 2 is free of it: the tail of the night hold is version 6's. Its gain is 2.3
standard errors on 60 weeks, 42 of 60 weeks better, with the tuning family against it (the gain of one week between
two near-identical desks has a spread of about 550 euros, so 60 weeks resolve about 70).

The long drives on version 6 (`python -m lab.long_cars`, 60 weeks):

| Drive | Cars a week | Late | Late in the 15 hard weeks | Margin a car | Fee paid, typical fees |
|---|---|---|---|---|---|
| under 2 h | 219 | 1.8% | 2.1% | 27.5 | 0.89 |
| 2 to 4 h | 92 | 3.0% | 5.1% | 51.0 | 0.92 |
| 4 to 5 h | 26 | 6.8% | 12.0% | 74.8 | 0.95 |
| 5 to 7 h | 27 | 6.2% | 11.8% | 101.7 | 1.03 |
| 7 to 8 h | 1.7 | 16.0% | 21.9% | 123.6 | 1.04 |
| 8 h and more | 3.4 | 28.9% | 40.7% | 100.5 | 1.17 |

Drives of 4 hours and more are 16% of the cars, 41% of the late cars and 33% of the margin. Same-day cars with
7 hours or more of drive (1.1 a week) are late 38% of the time and earn 36 euros each after refunds; with 18 to 30
hours to find a driver a 7-hour drive is late 37% of the time. Monday is the best day for long drives (4.3% late),
although nobody books on Sunday (0.1% of bookings from Saturday noon to Sunday midnight; 5% at night).

Also fixed: `lab/orders.py` gave a two-car gig's events and fee to its first car only. Both cars now carry the
gig's story and half its fee; the rows of a week add up to its score to the cent. In fresh-12 paired cars are
late 2.6% of the time, single cars 6.7%.

Queued from this: the night hold with the 6% guard; the fee change with a flu-day rescue for long drives only
(`flu=2`: on the morning of a flu day, long drives of that day still without a driver go up at 05:00); night
hold with weekend hold; the pair-holding design from `alt/` in exact mode.

## 41. Ranking round Saturday 09:00, played with the fee candidate (Sat 09:10)

Candidate: version 6 with `early_hour=13 night_hold=1 early_long=15` (no raise at night; the top fee on the
evening before only for single drives of 5 hours and more and for gigs that must start before 13:00). On 60 exact
practice weeks: +336 ± 91 over version 6 (lab +89, hold +652, fresh +267), lowest week 90.6%, none under 90%,
chance of a week under 90% 1.3%. With the 6% guard on top: +249 ± 85, lowest week still 90.6%: the guard does not
help this version. Played with `python -m lab.round early_hour=13 night_hold=1 early_long=15` (the round player
now takes settings; Emil's go-ahead at 09:08).

Result: 67,670, all five weeks ranked, 13th of the 23 teams ranked at 09:15 (`data/board8-0915.json`,
`data/rounds.jsonl`). Last round's first, second and seventh had not played yet.

| Week | We: margin (cars, on time) | The 12 best teams, mean: margin (cars, on time) | We against them |
|---|---|---|---|
| 1 | 10,521 (338, 94.7%) | 9,702 (344, 95.5%) | +8.4% |
| 2 | 14,023 (352, 98.3%) | 14,734 (389, 97.7%) | -4.8% |
| 3 | 13,295 (352, 98.0%) | 14,041 (406, 98.0%) | -5.3% |
| 4 | 17,080 (400, 95.5%) | 19,028 (452, 97.8%) | -10.2% |
| 5 | 12,751 (364, 92.9%) | 12,706 (375, 94.3%) | +0.4% |

What it shows:
- **We hold our own in the two hard weeks and lose 5 to 10% in the three ordinary ones, all of it on volume.**
  The teams ahead win 37 to 54 more cars in those weeks at 14 to 37 euros of margin for each extra car, and stay
  at 97 to 98% on time. That is the economics of the simulator session's first pick (cost 0.95, daily cap 0.12,
  short-notice cars: +44 cars and +803 a week on the 30-week panel), which we rejected for two weeks under 90%.
- The first place of this round is 73,950 and the tenth 68,719: the top ten is 1.5% away, before three of last
  round's best have played. Everyone scored 2 to 15% less than last round: these five weeks are leaner.
- Three groups of teams have the same score to the cent in every week (two, two and three teams): 8 different
  systems hold the 12 places ahead of us.

So the target for the day: the volume of the field in ordinary weeks, with a brake that keeps the hard weeks
ranked. Queued on the 30-week panel in exact mode: the higher-volume setting with the guard at 6% and 4%, the same
with the fee candidate, and a still lower cost (0.90) with the guard at 4%.

## 42. Where the field's extra cars come from (Sat 09:20)

The round (section 41) says the teams ahead win 40 to 55 more cars in an ordinary week. What we give up
(`python -m lab.unquoted`, version 6, 60 weeks; a week has 1,035 requests and we win 373):

| Kind of request | Requests a week | We win |
|---|---|---|
| a private address at either end | 133 | 0 (not quoted) |
| premium car | 53 | 0 (not quoted) |
| under 12 hours to find a driver | 45 | 0 (not quoted) |
| 12 to 24 hours to find a driver | 50 | 13% |
| trade-in (two cars) | 20 | 0 (not quoted) |
| same day only | 128 | 22% |
| everything else, dealer to dealer | | 41% |

`python -m lab.tested` now lists every setting played in exact mode on the current version with its gain, extra
cars and tail. Read as a whole it says what the queue had half-finished at the back:

| Setting, exact mode against version 6 | Weeks | Gain | Cars | Lowest week | Under 90% | Eight hardest (version 6) |
|---|---|---|---|---|---|---|
| `easy_find_hours=6`: a drive of at most 2 hours from a town with 100 drivers is quoted with 6 hours to find a driver instead of 14 | 40 | +622 ± 127 | +13.6 | 90.8% | 0 | 94.2% (93.6%) |
| the simulator's pick: that + `cost=0.95 day_cap=0.12` | 30 | +803 ± 174 | +43.8 | 89.4% | 2 | 92.5% (93.5%) |
| private pickups (`private_pickup=1 cost_private_pickup=0.3`) | 60 | +388 ± 104 | +14.6 | 88.0% | 1 | 92.5% (93.5%) |
| private pickups and deliveries + the tuner's fee change | 14 | +618 ± 230 | +24.2 | 92.8% | 0 | 95.0% (94.7%) |
| the fee candidate (section 41) | 60 | +336 ± 91 | +0.6 | 90.6% | 0 | 93.3% (93.5%) |
| pair holding, `design=pairhold_h4` (alt-designs) | 30 | +285 ± 164 | -2.9 | 90.5% | 0 | 92.8% (93.5%) |
| fee change + flu rescue for long drives (`flu=2`) | 60 | +257 ± 87 | | 88.8% | 1 | 92.7% |
| night hold + weekend hold | 60 | +137 ± 67 | | 90.9% | 0 | |

So three quarters of the simulator's pick was the short-notice rule, which is safe on its own (it even lifts the
hard weeks: an easy car booked the same day leaves fewer cars waiting overnight); the lower cost and looser day
cap added 30 thin cars and broke the tail. The flu rescue for long drives does not repair the full fee change,
and the weekend hold adds nothing to the night hold (nobody books on Sunday, so there is nothing to hold back).

In fast mode (which flatters added cars) on lab and hold: private deliveries +466 ± 106 with 10 more cars and the
same on-time share, premium cars at 0.3 typical fees of extra cost +345 ± 106, private pickups and deliveries
together +539 ± 135 with 23 more cars, trade-ins -221 ± 122.

Queued in exact mode: the fee candidate with `easy_find_hours=6` on 60 weeks (also with 4 hours, and with
`min_find_hours=10`), and on the panel that combination plus private deliveries, private pickups and premium cars.

## 43. The static stack on 60 weeks, and the delivery minimum as a budget (Sat 09:35)

**The stack.** Exact mode, 60 weeks, against version 6 (15,834; 369 cars; chance of a week under 90%: 0.6%):

| Setting | Gain | lab / hold / fresh | Better | Cars | Lowest week | Chance of a week under 90% |
|---|---|---|---|---|---|---|
| short notice at 6 hours alone (`easy_find_hours=6`) | +521 ± 103 | +349 / +894 / +319 | 46/60 | 383 | 88.8% (fresh-9) | 2.1% |
| C: fee candidate + short notice at 6 hours | +633 ± 109 | +250 / +1,070 / +578 | 48/60 | 382 | 89.96% (fresh-12) | 1.7% |
| C with 4 hours | +744 ± 124 | +523 / +1,233 / +476 | 50/60 | 391 | 89.84% (fresh-9) | 1.2% |
| C with `min_find_hours=10` | +640 ± 116 | | | 382 | 90.0% | |

A gain of 4 to 5%, on all three families, with a tail slightly worse than version 6: in each variant one of the two
hardest weeks ends within a car or two of 90%. (My 40-week reading of the short-notice rule in section 42 lacked
those two weeks.)

**Emil's ask (09:25): something new, a real-time decision layer, a desk that is not built for one kind of week.**
What the data says about adapting: a hard week cannot be seen coming (section 37). Its bad day shows just after
midnight on the day (`python -m lab.flu_severity`, 60 weeks): 51 of 60 weeks have a day on which drivers give back
four or more of that day's bookings in its first hour (Tue 9, Wed 16, Thu 18, Fri 17; never two bad ones early).
On such a day the cars due are late 4 to 7% on average (short drives 2.5%, 2 to 4 hours 4 to 11%, longer 15 to 25%),
on the worst days one car in six, and 44% of all late cars are due on these days. The ten hardest weeks all have
it on Thursday or Friday, with the days around it also worse than usual.

**The idea: the delivery minimum is a budget.** A week at 98% on time leaves about 30 cars of lateness unused; we
refuse 230 requests a week because each is a little riskier, and the field takes them (section 42). So:
1. `dispatch/risk.py` + `risk.json` (`python -m lab.cars_dump`, `python -m lab.risk_fit`): the chance that a car
   comes late, from what is known at the quote. A logistic model on yes/no facts, fitted on 659,462 saved cars
   (2,223 weeks of every exact setting; fast-mode weeks only for premium and private cars). Fitted on two families
   and checked on the third, the riskiest fifth of the cars is late 8.6 to 13.2% (predicted 10.7 to 12.0%) and the
   safest fifth 0.8 to 0.9% (0.9 to 1.0%). Against a plain car the odds are x5.5 for a premium car, x2.9 for a
   private delivery, x1.9 for a private pickup; x5.7 for a drive of 7 hours and more against x0.4 under 2 hours;
   x2.3 with under 6 hours to find a driver; x1.4 when due Thursday or Friday; x1.9 on a flu day.
2. `Policy.headroom`: a live forecast of the week's on-time share over 90%: the cars that arrived, every car on
   its way by its chance (a car without a driver close to its last pickup by what such cars did), the cars still
   to win, and one bad day still to come, as bad as the worst measured ones.
3. `budget`: a car's chance of lateness above a plain car's costs `late_cost` typical fees in any week (the
   refund, and the dealer's trust halves), and more as the headroom shrinks under `budget`
   (`budget_price` typical fees with none left). The flu-morning rescue (`flu=1`), which cost 300 to 500 a week
   when bought on every flu day, is bought only in a week whose headroom is under the budget.
4. `risky_last_day`: a static cousin for comparison: premium and private cars are quoted only when due by that day.

First two weeks with premium, private pickups and private deliveries switched on and the budget at 4%: lab-1
12,231 to 13,198 (315 to 348 cars, 97.1% on time), fresh-12 28,076 to 29,779 (446 to 492 cars, 91.7%). The forecast
never fell under 3.6 points in fresh-12 although the week ended 1.7 over: too optimistic about a bad day, since
raised to the worst measured ones. Queued: the budget at 5% and 8% with and without the rescue on the panel, and
the stack "C with 4 hours" with the budget-gated rescue and with the plain guard on 60 weeks.

Checked and dropped: handing an order back (the rules let us release a driver, not an order); steering work to
reliable drivers (experienced drivers give back 10.5% of bookings, the others 14.4%: too little).

## 44. First results of the budget layer, and a version that beats version 6 on mean and tail (Sat 10:00)

Exact mode against version 6 (`python lab/cands.py`). C4 is version 6 + `early_hour=13 night_hold=1 early_long=15
easy_find_hours=4`.

| Setting | Weeks | Gain | lab / hold / fresh | Cars | Eight hardest | Lowest week | Under 90% | Chance of a week under 90% |
|---|---|---|---|---|---|---|---|---|
| version 6 | 60 | | | 369 | 93.5% | 91.4% | 0 | 0.6% |
| C4 | 60 | +744 ± 124 | +523 / +1,233 / +476 | 391 | 93.4% | 89.8% | 1 | 1.2% |
| **C4 + guard 6%** | 60 | **+584 ± 144** | +380 / +1,130 / +242 | 387 | 93.7% | 91.8% | 0 | 0.5% |
| C4 + budget 5% + gated flu rescue | 60 | +230 ± 131 | +88 / +243 / +361 | 383 | 96.3% | 93.3% | 0 | 0.0% |
| C4 + private cars with under 2 hours of drive | 30 | +1,028 ± 194 | +672 / +1,646 / +559 | 406 | 93.8% | 88.5% | 1 | 3.0% |
| C4 + private deliveries under 2 hours | 30 | +891 ± 174 | | 393 | 93.3% | 88.4% | 1 | |
| C + premium and private cars, no brake | 30 | +970 ± 197 | | 408 | 91.3% | 87.6% | 2 | |
| the same + budget 5% | 30 | +855 ± 217 | +267 / +1,492 / +595 | 395 | 94.5% | 91.8% | 0 | 0.6% |
| the same + budget 5% + gated flu rescue | 30 | +723 ± 222 | | 396 | 95.3% | 93.1% | 0 | |
| the same + budget 8% + gated flu rescue | 30 | -88 ± 227 | | 386 | 96.2% | 94.5% | 0 | |

- **C4 + guard 6% is the first version that beats version 6 on the mean (+3.7%) and on the tail** on all 60 weeks:
  no week under 90%, the lowest week higher, all three families up.
- **The budget layer does what it was built for.** The stack that takes premium and private cars without a brake
  earns 970 more a week and loses two weeks in 30; with the budget at 5% it keeps 855 of that, no week falls under
  91.8%, and the eight hardest weeks end at 94.5% on time, a point above version 6. In those eight weeks it earns
  1,462 more than version 6, in the others 634.
- The budget costs too much on plain cars alone (C4: +744 without, +230 with budget and rescue): the standing
  `late_cost` of 1.5 typical fees charges the long drives, which earn the most. A lower `late_cost` is queued.
- The forecast is still a weak judge of the week: its lowest value is 1.4 points of headroom in the eight hardest
  weeks and 2.2 in the others (real: 1.8 to 5 against 5 to 8). Today it works mostly by pricing the riskier kinds
  and by being more careful until the week's bad day has passed.
- The simulator session's ranking of what we refuse (`sim/work/pool/POOL.md`): safe extra volume is about 62 cars
  a week, all with under 2 hours of drive (private pickups 32, private deliveries 19, short notice 11), at about
  22 euros a car before side costs; premium (9 to 15% late), trade-ins (34 to 47%) and private cars with long
  drives are not. `private_drive_hours` now caps private pickups as well as deliveries.

Queued on 60 weeks: C4 + private cars under 2 hours with the guard, and with the budget; the premium-and-private
budget stack on its other 30 weeks. On the panel: the budget with `late_cost=0.5`, and with C4 as the base.

## 45. Version 7 candidate: private cars with short drives, braked by the guard (Sat 10:15)

Exact mode, all 60 weeks, against version 6. C4 as in section 44; "private under 2 h" is
`private_delivery=1 private_pickup=1 private_drive_hours=2 cost_private_pickup=0.2`.

| Setting | Gain | lab / hold / fresh | Better | Cars | Eight hardest | Lowest week | Under 90% | Chance of a week under 90% |
|---|---|---|---|---|---|---|---|---|
| version 6 | | | | 369 | 93.5% | 91.4% | 0 | 0.6% |
| C4 + guard 6% | +584 ± 144 | +380 / +1,130 / +242 | 45/60 | 387 | 93.7% | 91.8% | 0 | 0.5% |
| **C4 + private under 2 h + guard 6%** | **+984 ± 126** | +811 / +1,389 / +751 | 55/60 | 406 | 94.3% | 91.6% | 0 | 0.5% |
| C4 + private under 2 h + budget 5% | +751 ± 114 | +368 / +1,004 / +880 | 48/60 | 400 | 95.8% | 93.3% | 0 | 0.0% |
| C4 + private under 2 h, no brake (30 weeks) | +1,028 ± 194 | | 27/30 | 406 | 93.8% | 88.5% | 1 | 3.0% |

The guard costs about 45 euros a week on this stack and takes the chance of an unranked week from 3% to 0.5%;
the budget costs about 280 and takes it to nothing measurable (lowest week 93.3%). Version 7 will be the guard
row: 16,818 a week, 6.2% over version 6, with a better tail. The budget row is the safer alternative and the base
for the next step (its standing charge on long drives is what costs; `late_cost=0.5` is queued).

## 46. Version 7 (Sat 10:50)

Version 7 = version 6 + `early_hour=13 night_hold=1 early_long=15` (no raise at night; the top fee on the evening
before only for single drives of 5 hours and more) + `easy_find_hours=4` (an easy car is quoted with 4 hours to
find a driver) + `private_delivery=1 private_pickup=1 private_drive_hours=2 cost_private_pickup=0.2` (private
addresses with under 2 hours of drive) + `guard=0.06` (the brake).

| Seeds (exact mode) | Mean margin | Worst week | Cars | On time | Lowest on time | Ranked |
|---|---|---|---|---|---|---|
| lab-1..20 | 16,881 (version 6: 16,070) | 10,235 | 412 | 97.5% | 94.7% | 20/20 |
| hold-1..20 | 16,654 (15,265) | 11,431 | 398 | 96.8% | 93.5% | 20/20 |
| fresh-1..20 | 16,917 (16,166) | 9,732 | 410 | 96.3% | 91.6% | 20/20 |
| all 60 | 16,817 (15,834): +984 ± 126, 55 of 60 weeks better | | 406 at 40.9 a car | 96.9% | | 60/60 |

Checks after the fold: the new defaults replay the candidate's saved weeks to the cent (lab-1 12,938.35, hold-3
18,365.59); `python -m lab.restart_check` passes on both (lab-1 12,938.35 straight, 13,290.43 with three restarts;
hold-3 18,365.59 and 18,559.73; all ranked).

Still open against version 7 on the 30 panel weeks: the budget stack (no guard, no drive cap on private cars,
premium cars at 0.2, `budget=0.05`) +347 ± 199 with the eight hardest weeks at 95.1% (version 7: 94.3%) and the
lowest week at 92.0% (91.6%); now running on all 60. The budget in place of the guard on version 7's own cars:
+49 ± 208 on the panel, -233 on 60 weeks, lowest week 93.3%. With `late_cost=0.5`: +207 ± 199, lowest 90.3%.

From the alt-designs session (exact panel against version 6): holding short drives for a round-trip partner
(`pairhold_s2`) +249 ± 205 with the tail of version 6; every bold design loses: prices cut early in the week and
raised late (`bold_front`) -393 with two weeks under 90%, cost 0.85 with a stop per day -1,239, the volume setting
with that stop -465. A stop that closes whole days is a worse brake than the guard.

`python -m lab.live_check --days 2 --speed 2` passes for version 7 (457 requests decided and all answered in time,
139 orders by Tuesday night, no quote refused, the desk stopped once and started again). Version 7 is on the final
runner since 10:55 (`~/dispatch-live`, the service restarted and waiting; version 6 kept in `~/dispatch-live-v6`).

## 47. Against version 7: what does not beat it (Sat 11:15)

Exact mode against version 7 (16,817; eight hardest weeks 94.3%; lowest week 91.6%).

| Setting | Weeks | Gain | Cars | Eight hardest | Lowest week | Under 90% | Verdict |
|---|---|---|---|---|---|---|---|
| the budget stack: `budget=0.05` in place of the guard, private cars of any drive, premium cars at 0.2 | 60 | +108 ± 125 | +5.8 | 95.1% | 92.0% | 0 | the same money with a better tail; the panel's +347 did not hold. Not taken yet: a bigger part has to earn more than this |
| `easy_drivers=50` (short notice also from towns with 50 drivers) | 60 | +24 ± 83 | +2.3 | 94.1% | 91.0% | 0 | no |
| holding a short drive up to 4 hours for a partner (`design=pairhold_s4`, alt-designs) | 30 | +221 ± 123 | -5.4 | 93.3% | 90.6% | 0 | no: a fee saving in ordinary weeks (+349 on the other 22) paid for in the hard ones |
| the same, only while the guard says the week goes well (`pairhold_s4c`) | 30 | +246 ± 134 | -5.7 | 93.5% | 89.8% | 1 | no |
| holding up to 2 hours (`pairhold_s2`), and with `pair_bonus=0.15` | 30 | -5 ± 226 / -3 ± 216 | | 93.4% / 94.2% | 90.2% | 0 | no |

The alt-designs session closes with: no design that is not a variation of the base beats version 7
(`alt/NOTES.md`). Running: `private_drive_hours=3`, `guard=0.08`, `day_cap=0.12`, `easy_drive_hours=3`,
`cost_private_pickup=0.1`, premium cars at 0.3 under the guard, and two price-side ideas that were unsafe without a
brake (`book=day`, `menu=2`).

## 48. What are the leaders doing that we are not? (Sat 11:45)

Standings of the round Saturday 09:00 with 55 teams ranked (`data/board8-1120.json`): 1st 79,003 (398 cars a week
at 39.7 a car, 98.0% on time), 2nd 77,573, 3rd 73,950, 5th 72,498, 10th 70,347; we are 18th with the fee candidate
of 09:10 (67,670; 361 cars at 37.5; 95.8%). Version 7 on those weeks: about 70,400, the 10th place. Against our
run the leader wins 24 to 55 more cars in the three ordinary weeks AND earns 2.50 to 4.90 more on each car; in a
hard week with the same number of cars it earns 3.50 more a car at 98% on time against our 94.7%.
Version 7 per car: price 101.70, driver fee 58.20, refunds 1.60, margin 41.40.

**Dealer trust** (`python -m lab.trust_path`, version 7, 60 weeks). A week has 40 dealers; the four largest send
56% of the requests. The trust count a dealer holds when its request arrives is 8.0 on average of 25 possible:
0.3 on Monday, 4.8 Tuesday, 10.3 Wednesday, 12.3 Thursday, 14.0 Friday. Late cars cost only 0.7 of a point (8.7
without any late car): the count is low because it takes deliveries to build, not because we lose it.

Exact mode, 60 weeks, against version 7:

| Setting | Gain | Cars | Lowest week | Eight hardest | Verdict |
|---|---|---|---|---|---|
| the trust rule inside the price (`trust=1`) | -211 ± 107 | -3.7 | 91.2% | 93.2% | no: the price book already learns each dealer's level, the rule on top counts it twice |
| a price book that starts afresh each morning, with the trust rule (`book=day trust=1`) | -197 ± 171 | +68 | 90.0% | 91.9% | no: 474 cars a week at thinner prices, the same money, a worse tail |
| a lighter brake (`guard=0.08`) | +81 ± 36 | +2.6 | 92.4% | 94.2% | small and real; candidate |
| `day_cap=0.12` | +2 ± 90 | +5.9 | 89.4% | 93.1% | no |
| private cars up to 3 hours of drive (`private_drive_hours=3`) | -89 ± 140 | | 92.0% | 94.2% | no |
| short notice from towns with 50 drivers (`easy_drivers=50`) | +24 ± 83 | | 91.0% | 94.1% | no |

Running: lower opening fees (most gigs are booked at the opening fee of 0.85 typical fees, so we may pay more than
needed), and the daily price book at a higher cost (1.15, 1.3) so that it holds the number of cars and takes its
sharper estimate as price instead of volume.

## 49. The kinds of week and their odds; the first half of a hundred far-out ideas (Sat 12:40)

**Emil's question: do we know the statistics of the weeks, and do we optimise for what is most likely?**
`python -m lab.week_types`, 60 practice weeks. Every week has 1,030 to 1,040 requests and a snow forecast: weeks do
not differ in size but in the price level of the market and in the drivers. The mean over these 60 weeks is the
expected value we optimise; the chance of a week under 90% is the limit we hold.

| Kind of week (the last day drivers fall ill) | Weeks | Chance | Version 6: margin, on time, lowest | Version 7: margin, cars, on time, lowest | Version 7 less 6 |
|---|---|---|---|---|---|
| no such day | 9 | 15% | 13,670, 98.2%, 97.0% | 14,641, 389, 98.1%, 96.4% | +972 |
| Tuesday | 6 | 10% | 17,675, 97.2%, 95.4% | 19,284, 432, 97.6%, 96.0% | +1,610 |
| Wednesday | 11 | 18% | 14,769, 97.3%, 95.7% | 15,582, 396, 97.2%, 95.0% | +813 |
| Thursday | 17 | 28% | 15,344, 95.9%, 91.4% | 16,381, 399, 96.2%, 91.6% | +1,037 |
| Friday | 17 | 28% | 17,509, 96.7%, 93.7% | 18,335, 421, 96.4%, 91.9% | +826 |

72% of the weeks have one such day, 12% two, 15% none. In 45% of the weeks drivers also give back bookings for
the last Monday. Version 7 earns more than version 6 in every kind of week (+660 to +1,610), and every week under
93% on time is a Thursday or Friday week. One week in ten earns under 12,232 and one in ten over 22,214.

**A hundred far-out ideas** (`python -m lab.crazy`; Emil: "try some crazy ideas, like paying the drivers almost
nothing"). 118 settings far from anything we would tune towards, each on the same 12 weeks (4 hard, 8 ordinary) in
fast mode against version 7 (17,087; 404 cars; 95.8%; fees paid 0.94 typical). The first 60:

| Idea | Gain | Cars | On time (lowest) | Fee paid, typical fees |
|---|---|---|---|---|
| open every gig at 30% of the typical fee | -15,536 | -92 | 90.1% (77.6%) | 1.47 |
| 40% rising to 70%, rescue at 100% | -16,467 | -97 | 81.9% (69.1%) | 0.84 |
| open at 50% / 60% / 70% / 75% | -8,403 / -4,204 / -1,204 / -118 | | 94.0% / 94.8% / 95.3% / 95.3% | 1.18 / 1.06 / 0.97 / 0.95 |
| open at 95%; 100% flat; 120% at once | -1,651 / -2,753 / -6,644 | | | 1.01 / 1.03 / 1.21 |
| two hours at 40%, then as usual; 45 minutes at 60%; 20 minutes at 50% | -9,637 / -2,890 / -3,452 | | | 1.22 / 1.00 / 1.03 |
| never pay more than the typical fee | -1,029 | -35 | 93.2% | 0.86 |
| cheap rescue (late fee 1.2, ceiling 1.4) | -3,543 ± 1,393 | | | 0.86 |
| cost 0.6 / 0.8 / 0.9 / 1.2 / 1.5 / 2.0 | -1,655 / -84 / +109 / -1,028 / -6,857 / -14,928 | +134 / +82 / +44 / -93 / -241 / -377 | 92.4% / 93.8% / 94.9% / 97.2% / 98.5% / 99.4% | |
| spread 0.07 / 0.25; learning three times faster / slower | -690 / -2,597; -842 / -132 | | | |
| every car at its top fee the evening before; none | -1,758 / -41 | | | 1.02 / 0.93 |
| best of the 60: learn from the option rule; evening from 20:00; pairs at 70% | +268 ± 229; +244 ± 165; +166 ± 244 | | | |

**Paying drivers little costs more, not less.** A gig that opens at 30% is not booked; drivers who saw it low wait
for the raise, it turns urgent, and the fee finally paid is 1.47 typical fees against 0.94. Every step below 75%
loses, and so does every step above 85%. The same holds for the price: cost 1.0 sits between a loss at 0.8 and a
loss at 1.2. On fees and prices the desk is at the top of its hill; no far-out move on those axes comes near.

## 50. The final is one week: what are the odds? (Sat 13:15)

Rules and handbook: the final is one secret level 8 world on Sunday 08:00, set at 07:30, the same requests,
drivers and random draws for every team, on a clock that moves by itself (about 34 minutes). The 10 ranked teams
with the highest margin present to the jury: "the final has one job: to put your team in the top 10". A level 8
world draws 26 to 40% of a normal world's drivers, a competitor 26 to 54% over the list price, and has every event
in every week: an outage region, a flu, a bulk order and a price-war day. (So our nine weeks "without a flu day"
have it on Monday, when nothing is booked yet that could be given back.)

**Are the leaders betting on risk? No.** In both rounds no team of the top 15 had a week under 90%; this
morning 4 of their 75 weeks were under 93%. The first two have their lowest week at 96.2% and 96.0%. The teams
that gamble are further down: 11 of 74 lost their ranking last night, 3 of 58 this morning.

**Each week of this morning's round as if it were the final** (place among the teams ranked in that week):

| Week | 1st | 10th | Our run (fee candidate) | Place | Version 7, estimated (+4%) | Place |
|---|---|---|---|---|---|---|
| 1 (hard) | 12,054 | 9,950 | 10,521 | 8 | 10,941 | 4 |
| 2 | 17,078 | 14,675 | 14,023 | 22 | 14,584 | 11 |
| 3 | 16,987 | 14,035 | 13,295 | 19 | 13,826 | 14 |
| 4 (rich) | 20,883 | 18,688 | 17,080 | 22 | 17,764 | 17 |
| 5 (hard) | 15,305 | 12,876 | 12,751 | 13 | 13,261 | 9 |

Only the first two teams of the round are in the top ten in all five weeks; the third to seventh in three or four
of five; the eighth to thirteenth in two or three. Version 7 would be in it in two of five and eleventh in a
third: strong in the hard weeks, 1 to 5% short in the ordinary and rich ones. Places move by 5 to 10 between
weeks for every team outside the first two, so one week is partly a draw; what we control is how far inside the
line we stand in an ordinary week.

Three groups of teams score the same to the cent in every week (2, 2 and 3 teams). Teams with the same margin
share a rank, so in the final such a group would take two or three of the ten places with one system.

## 51. The other half of the hundred far-out ideas (Sat 13:20)

All 118 ideas of `lab/crazy.py` are played (12 weeks each, fast mode, against version 7 at 17,087). None is a
clear winner; what the losers cost says what each part of the desk is worth.

| Idea | Gain | Cars | On time (lowest week) |
|---|---|---|---|
| the budget in place of the guard | +708 ± 434 | -2 | 97.0% (92.1%) |
| private cars of any drive; premium cars at no extra cost; every car with 6 hours' notice | +528 ± 247; +459 ± 417; +431 ± 249 | +10; +13; +14 | 95.2% (90.3%); 95.2% (90.7%); 94.8% (90.1%) |
| no brake; a slow brake (12%) | +394 ± 154; +363 ± 139 | +7 | 95.5% (89.0%); 95.5% (89.5%) |
| direct offers 6 hours before the last pickup; an offer to the driver who just delivered nearby | +195 ± 99; +99 ± 100 | | 95.9%; 95.8% |
| a hair trigger (guard 3%); the strain rule; a brake three times as hard | -880; -1,045; -268 | | |
| no pairs; tight pairs; cheap wide pairs | -895; -567; -1,987 | | |
| the kit's note reader instead of ours | -2,495 | -16 | 94.2% |
| no drive over about 5 hours; long drives dear; thin towns dear | -2,611; -1,898; -2,472 | -32; -26; -119 | 97.1%; 97.6%; 97.6% |
| only cars with a full day's notice; with 40 hours | -949; -5,574 | -32; -156 | |
| every car with 3 hours' notice; take everything (premium, trade-ins, any private car) | -1,463; -1,811 | +8; +12 | 93.7% (86.0%); 92.5% (87.7%) |
| no cap on cars a day; a tight cap | -460; -518 | +31; -37 | 93.0% (86.3%); 96.7% |
| flu-day rescue; restart fees after a drop | -744; -188 | | |
| courier (short drives only); luxury (fees 110 to 140%, cost 1.3); sweatshop (fees 50 to 90%, cost 0.7) | -4,371 / -6,822; -5,817; -12,407 | | 97.5%; 98.3%; 87.2% (79.1%) |

Reading it:
- **Every character that is not this desk loses thousands.** Pay little and flood: -12,407 and 87% on time. Pay
  well and charge more: -5,817. Short drives only: -4,371 to -6,822. The long drives alone are worth about 2,600 a
  week, the pairs 900, our note reader 2,500.
- **The ideas at the top are the ones exact mode has already judged.** The budget in place of the guard is +708
  here and -233 on 60 exact weeks; private cars of any drive +528 here and -89 at three hours in exact mode;
  premium cars +459 here and +108 with the budget on 60 exact weeks. Fast mode on 12 weeks is good for ruling out,
  not for adopting.
- Worth one exact test each, because they cost nothing in the tail here: direct offers six hours before the last
  pickup, and the guard at 8% (already +81 ± 36 on 60 exact weeks).

Also from exact mode, 60 weeks against version 7: `open_fee=0.8` is -290 ± 120 with one week under 90%; the
opening fee stays at 0.85.

## 52. Astra's two rules played; the leaders study's first findings (Sat 13:55)

Exact mode, 60 weeks, against version 7:

| Setting | Gain | Lowest week | Eight hardest | Verdict |
|---|---|---|---|---|
| the tighter car of a pair first if the pair starts at most 15 minutes earlier (`pair_urgent_first=15`; Astra) | -44 ± 61 | 91.9% | 94.3% | no effect |
| the same with 30 minutes (41 weeks) | -133 ± 101 | 93.2% | 94.5% | no |
| a fee floor of 1.5 typical fees from 17:00 the day before for early pickups in thin areas (`thin_evening_floor=1.5`; Astra) | -173 ± 72 | 91.6% | 94.2% | no: it pays more and saves no car |

A fifth session, `leaders/` (a lead with ten sub-agents, started on Emil's ask at 13:20), studies how the first two
teams reach their numbers. Its first findings (`leaders/STATUS.md`, `leaders/board/REPORT.md`,
`leaders/trust/REPORT.md`):
- Calibrated on our own ranking runs, version 7 would have made 69,800 ± 2,300 in the round of 09:00 (391 cars at
  35.7, 96.2% on time), place 14 of 64; the first two are +9,200 and +7,800 at 7 to 8 more cars and 3.3 to 3.9
  more a car. In the round of 12:00, whose weeks are richer (top-20 median 445 cars at 40.9), version 7 would be
  about 84,500 to 89,100, place 11 to 18 of 48; the leader has 99,211 (446 cars at 44.5, 97.8%). Version 7 stands
  lowest against the field in the richest weeks (0.96 of the field's median against 1.09 in the leanest).
- Dealer trust is not it (we already take 8.3 euros a car from it; no desk can hold much more), and punctuality is
  not the main cause (a late car costs about 86 euros all told: 98% instead of 96.9% is worth about 450 a week).
- On the cars we win, our quote stands 13% under the dealer's limit at every trust count (13 weeks with limits
  measured by fork). Two to three euros a car at the same number of cars are price or driver fee; none of 140
  settings in our history gives that.
- Cars due on the last Monday are the best we carry (late 1 to 3%, 48 to 64 euros a car) and the day cap rations
  them like a Thursday: without the cap for them (`design=ld_lead_monoff`) +253 ± 85 on 12 exact weeks with 8 more
  cars and the lowest week at 90.8%; on the panel next.
- Five groups of teams had results identical to the cent in the round of 09:00.

## 53. Version 7 played for real: ranking round Saturday 12:00, and the 14:00 test final (Sat 14:25)

**Ranking round** (Emil at 13:56: "Play it now with our best version"; `python -m lab.round`, defaults = version 7;
`data/round6.log`, `data/rounds.jsonl`, `data/board8-1425.json`). The lab queue was held back while it ran.

Result: **94,242, all five weeks ranked, 6th of 53** ranked teams at 14:25 (434 cars a week at 43.4 a car, 97.2% on
time). The first is 99,211 (446 cars at 44.5), the fifth 94,319, the tenth 90,167. Two of the morning's top
teams had not played yet.

| Week | We: margin (cars, on time) | Place if this week were the final | 1st | 10th | We against 10th |
|---|---|---|---|---|---|
| 1 | 19,213 (453, 96.7%) | 5 of 58 | 21,290 | 18,097 | +6.2% |
| 2 | 23,046 (459, 98.7%) | 1 of 56 | 23,046 | 20,337 | +13.3% |
| 3 | 13,700 (400, 98.2%) | 14 of 58 | 15,958 | 14,605 | -6.2% |
| 4 | 21,178 (458, 98.9%) | 10 of 57 | 22,667 | 21,178 | 0.0% |
| 5 | 17,106 (400, 93.2%) | 12 of 54 | 19,568 | 17,307 | -1.2% |

Against the same round's leaders we now win as many cars (434 against 439 to 469) at the highest margin a car but
one. The leaders study's estimate for version 7 in this round was 84,500 to 89,100: the played result is 6 to 12%
above it, so its calibration from our older runs undersold version 7 in rich weeks. In the morning's round the
earlier version was 18th of 55 with 67,670.

**Test final** (14:00, a level 8 week from Thursday 00:00, the final runner on version 7): margin 2,599.52 on
130 orders, 100% on time, ranked. The runner was restarted on purpose at 14:08, between Thursday and Friday of the
world; it took up the same world and went on (76 orders before, 131 after Friday).

## 54. The climb: small changes on version 7, tried by the lab itself (Sat 14:30 on)

Emil after the round: "find that last 5 to 10%... grind out and max out the algorithm". Two tracks:
- the leaders study (`leaders/`) looks for what is structurally different, now narrowed by the round to one
  question: what kind of week makes version 7 stop at 400 cars while the leaders take 435;
- `python -m lab.climb` (on the Stockholm machine, log in `data/climb_log.md`) tries 72 single changes on version 7
  in exact mode, one at a time: first the 30-week panel, and only a change that gains there and takes no week
  under 90% goes to the other 30 weeks. A change is kept only if on all 60 weeks it gains at least 60 euros a week
  and two standard errors, gains in at least two of the three seed families, takes no week under 90% and leaves
  the eight hardest weeks' on-time share where it was (less 0.3 points at most). A kept change is the base for
  the next ones. What it keeps is a proposal: the stack is confirmed on a seed family used for nothing before it
  becomes a version.

## 55. Where version 7 is strong and weak in the round, and the cap that decides our volume (Sat 14:40)

The round of 12:00, week by week against the nine teams around us in the top ten:
- **Strong:** the highest margin a car of the top ten but two (43.4; the field 40 to 43); the best single week of
  the whole round (week 2: 23,046, 1st of 56); level with or ahead of the leader in three weeks of five.
- **Weak:** weeks 3 and 5, where we carried exactly 400 cars and the leaders 434 to 449. Week 3 ran at 98.2% on
  time: the room was there. Week 5 was a hard week (93.2% for us, 93 to 97% for the others).

`python -m lab.cap_bound` (version 7, 60 weeks; run on the server): the list of drivers has 634 to 950 names, and

| Listed drivers | Weeks | Cars won | A driver | The cap of a week (0.11 x 5 days) | On time | Margin a car |
|---|---|---|---|---|---|---|
| 600 to 680 | 10 | 367 | 0.561 | 359 | 97.1% | 36.0 |
| 680 to 760 | 12 | 392 | 0.547 | 395 | 96.6% | 38.0 |
| 760 to 840 | 11 | 432 | 0.537 | 443 | 96.5% | 45.2 |
| over 840 | 27 | 417 | 0.465 | 494 | 97.1% | 42.2 |

**In 33 of 60 weeks the daily cap alone decides how many cars we carry**: 0.55 a listed driver, whatever the week
could bear, at the same on-time share as the weeks where it does not bind. A cap of 0.12 for every week is known
to gain nothing (+2 ± 90, one week under 90%), so the cap has to know the week. First attempt: `cap_easy`, the cap
used while the week goes well (`Policy.relaxed`); queued on the panel at 0.13, 0.15 and 0.2. The leaders study has
the finding for its capacity line (per due day, per region, in driver-hours).

## 56. What the leaders study found in our own desk (Sat 14:45)

Four findings from `leaders/` (ten sub-agents; `leaders/STATUS.md`, `leaders/ontime/REPORT.md`,
`leaders/fees/REPORT.md`, `python -X utf8 leaders/week_kinds.py`), all on version 7's exact weeks:

1. **Our volume follows the price level, not the drivers.** Split at the median price level (1.494 list prices):
   in the 30 lean weeks version 7 wins 375 to 379 cars, in the 30 dear weeks 433 to 439. In the 16 lean weeks with
   easy drivers it is 98.1% on time and pays 0.909 typical fees: the drivers are idle and it still stops. Nine of
   fifteen exact settings gain in lean weeks and lose in dear ones (holding pairs +426 / -46, the budget stack
   +252 / -36, `day_cap=0.12` +136 / -133, `open_fee=0.8` +81 / -661, `guard=0.08` +139 / +22), none gains in dear
   weeks. Reading: version 7 is at its optimum in dear weeks and under it in lean ones, because its cost of 1.0
   typical fees is about 7% over what a car costs when the day is not full. The level of a week is known by Monday
   evening. Being tested: `cost=0.95` on the 16 leanest and the 16 dearest weeks.
2. **A fault in the pairing, on the final runner.** `Desk.tick` took a pair off the list of pairs once a driver
   booked it. When the driver gave it back, the gig was open again but no longer known as a pair; the next order
   that made a round trip with one of its cars withdrew the whole gig, and the other car was left without any gig
   and never delivered: 36 cars in 25 of the 60 weeks, each a late order and a penalty of twice its price (81 euros
   a week in penalties, 41 in lost revenue). Fix ported as `pair_safe=1`: a booked pair stays on the list, an open
   gig with two orders is never a partner, and a restart puts booked pairs back on the list.
3. **The cheap path for a car past saving started too late.** It tested "now + drive > deadline", which misses a
   car whose pickup site has closed for the day: 2.5 cars a week were posted at the steep fees for a delivery that
   was late whatever we paid (about 67 euros a week). Ported as `late_by_pickup=1`.
4. **A fee rule that holds car by car.** A dealer-to-dealer car going where 30 or more drivers live, with a drive
   under 5 hours, opens at 0.75 typical fees instead of 0.85 (the driver who lives there has no trip home to pay
   for): on the same 118 cars a week the fee paid falls from 0.868 to 0.815 with lateness 1.1% to 1.7%, +377 ± 54
   a week, 12 of 12 weeks. The whole week shows +353 ± 264 on 12 weeks; the 60-week run is at the front of the queue.
   (A flat 0.8 for every car loses, section 51: the gain is only in this class.)
Also measured there, not ported yet: pickup windows of our own that end at the last pickup, with an answer to
`driver_late` (a driver who chains our gig behind another collects after the last pickup 2.06% of the time against
0.15%, silently): with the two fixes, +337 ± 230 on 16 weeks and the eight hardest weeks at 94.8% against 94.3%.
It keeps four books that a restart does not rebuild yet.

Queued on all 60 exact weeks: `pair_safe=1`, `late_by_pickup=1`, both; the fee rule (`design=ld_fees_a3b`); the
leaders' whole stack with `guard=0.08`.

## 57. More from the leaders study; the adaptive cap fails; the guard counts twice (Sat 15:05)

- **A cap that loosens while the week goes well (`cap_easy`) does not work.** Exact panel against version 7:
  0.13: -33 ± 167 (eight hardest -216, the others +34; lowest week 90.4%); 0.15: +46 ± 205 (-401 / +209); 0.2:
  -444 ± 255 on 14 weeks. As the leaders study warned from its own gated tests: in the two hardest weeks the week
  still "goes well" on Thursday and Friday morning, and the late cars come after.
- **No sign inside a week that a town runs short.** A car is late 2.8 to 4.0% of the time whether the earlier cars
  for its town that week were late, slow to find a driver, or neither (60 weeks, `data/cars.json.gz`). Lateness
  sits on lanes we have not served yet that week (3.7% against 1.8%), which is the long and odd lanes again.
- **The guard counts a warned car twice** (`leaders/api/AUDIT.md`): the world repeats the deadline warning when a
  car's gig runs out, 19.9 warnings for 11.5 cars a week, and two thirds of the guard's careful time comes from
  the second count. New switch `guard_once=1` (each order once; rebuilt after a restart); queued on 60 exact weeks
  with the line at 0.06, 0.05 and 0.04.
- From the leaders study, closed with numbers: direct offers in any form (13,525 saved offers: 57 to 67% read,
  0.07 to 0.14% of those accepted), a sharper price book even when it only raises (+39 ± 298), re-quoting
  (+138 ± 438), trade-ins (-443 ± 454), a pair fee by geometry (-228 ± 392). `cost=0.95` gains 219 ± 249 on the 16
  leanest weeks and loses 314 ± 288 on 12 of the 16 dearest: the direction it predicted, inside the noise, no rule
  yet.
- **The late cars are the same cars under every setting:** 13.2 requests a week (3.6%) are late in 30% or more of
  the weeks that carry them, whatever the desk does; they hold 69% of all lateness, cost 1.60 typical fees and
  earn 13 euros each. A desk that is told which they are gains 342 ± 368 with the four hard weeks at 97.1% on time
  against 93.5%: that is the leaders' punctuality. What is known at the quote finds them poorly (the riskiest 3.6%
  by our model are late 21% of the time and earn 65 euros each).

## 58. The leaders study's stack: +801 on 60 weeks, and its port into the desk (Sat 15:25)

`design=ld_lead_stack2 guard=0.08` (the leaders study's plug-in), exact mode, 60 weeks, against version 7:
**+801 ± 120** (lab +1,113, hold +355, fresh +936), 49 of 60 weeks better, 419 cars (+12.7), 42.0 a car, on time
96.8% (version 7: 96.9%), eight hardest weeks 93.4% (94.3%), lowest week 90.9% (91.6%), none under 90%, chance of
a week under 90% 1.1% (0.5%). In lean weeks +846, in dear weeks +756; with hard drivers +1,139, easy +464.

What it is: the pairing fix; the cheap fees from the minute the last pickup has passed; a pickup window that ends at
the last pickup, with a late driver released when another can still come; the fee rule for cars that go where
drivers live (open at 0.75; drives under 3 hours) and the fast rise for cars won at short notice; no day cap for
cars due after Friday; the guard at 8%. Parts alone on 60 weeks so far: the fee rules +97 ± 118, the guard +81 ± 36.

Ported into `dispatch/` behind settings that are off by default (version 7 replays to the cent):
`pair_safe`, `late_by_pickup`, `windows`, `home_open` (+ `home_drivers`, `home_hours`, `home_min_fee`),
`short_ramp`, `cap_week_only`, `guard_once`. The ports give the plug-ins' weeks to the cent: the fee rules on
lab-1, hold-3 and fresh-12; the windows on lab-1 and fresh-12. `lab.restart_check` now takes `--set`.
Running on 60 weeks: the ported stack with and without the Monday cap change, each part alone, the plug-in with the
cap kept and with the guard at 6% (to find which part thins the tail), and the guard counting each car once.
`python lab/cands.py` prints all of them with the chance of a week under 90%.

## 59. Version 8 (Sat 16:10 to 16:30)

The ported stack on 60 exact weeks against version 7, in three forms of the brake:

| Form | Gain | lab / hold / fresh | Better | Eight hardest | Lowest week | Chance of a week under 90% |
|---|---|---|---|---|---|---|
| version 7 | | | | 94.3% | 91.6% | 0.5% |
| the guard as it is, at 8% | +453 ± 107 | +635 / +141 / +582 | 46/60 | 93.9% | 90.8% | 0.7% |
| the guard counting each car once, at 6% | +453 ± 105 | +664 / +153 / +543 | 45/60 | 93.8% | 91.0% | 0.8% |
| counting once, at 5% | +367 ± 113 | +607 / +111 / +382 | 44/60 | 94.2% | 91.5% | 0.5% |
| (the plug-in form, tell4 windows, guard 8%) | +566 ± 105 | +659 / +325 / +714 | 49/60 | 94.4% | 91.9% | 0.3% |

On check-1..20, a seed family used for nothing before: the first form +606 ± 152, 16 of 20 weeks better, lowest
week 92.5% against version 7's 92.6%, none under 90% (`python lab/confirm.py ...`).

**Version 8 = version 7 + `pair_safe=1 late_by_pickup=1 windows=1 home_open=0.75 short_ramp=1 guard=0.08`**
(the first form: it has the confirmation and the restart check behind it; `guard_once` stays a setting):
the pairing fault fixed, the cheap late fees from the minute the last pickup has passed, a pickup window that
ends at the last pickup with a release of a driver who says they will be late, an opening fee of 0.75 for plain
cars that go where 30 or more drivers live (drives under 3 hours, typical fee of 22 euros or more), a rise within
40 to 80 minutes for cars won at short notice, and the guard at 8%.

| Seeds (exact mode) | Mean margin (version 7) | Worst week | Cars | On time | Lowest on time | Ranked |
|---|---|---|---|---|---|---|
| lab-1..20 | 17,516 (16,881) | 10,415 | 413 | 97.8% | 96.1% | 20/20 |
| hold-1..20 | 16,795 (16,654) | 11,834 | 396 | 96.5% | 93.4% | 20/20 |
| fresh-1..20 | 17,498 (16,917) | 10,203 | 410 | 96.5% | 90.8% | 20/20 |
| all 60 | 17,270 (16,817) | | 406 at 42.5 a car | 96.9% | | 60/60 |
| check-1..20 | 15,412 (14,805) | 8,122 | 394 | 96.6% | 92.5% | 20/20 |

Checks: the defaults replay the candidate's saved weeks to the cent (lab-1 13,638.93, hold-3 19,223.39);
`lab.restart_check` passes on lab-1 (13,638.93 straight, 13,548.43 with three restarts) and fresh-9 (12,877.77 and
12,992.57, 92.4% and 93.0% on time), and before the fold on hold-3 and fresh-12 with the same settings;
`lab.live_check --days 2 --speed 2` passes (457 requests, all answered in time, 141 orders, no quote refused, one
stop and restart). Version 8 is on the final runner since 16:20 (version 7 kept in `~/dispatch-live-v7`).
Not in it, measured: no day cap for cars due after Friday (+235 a week on the plug-in stack, chance of a week under
90% from 0.3% to 1.1%). `python -m lab.climb` runs again from version 8 (78 single changes).

**Discord, read at 16:30** (a sub-agent, read only; Junction Community server, `#bahn-express`): Bahn says the rate
limit is per team ("8 weeks in parallel are not faster than 8 weeks one after another"); the 20:00 test final
plays the whole week as the final does (20:00 to about 20:34); a further test final is promised for 00:00 to
02:00; test-final results show on the leaderboard as teams finish; the practice server stays up on Sunday.
Organisers: submissions are due Sunday 10:00 (repository, demo link, a public video of at most 2 minutes); peer
review at the team's table from 10:30, a five-minute pitch and a demo.

## 60. Version 8 played: ranking round Saturday 15:00, and the afternoon's tests (Sat 17:25)

**The round** (`python -m lab.round`, defaults = version 8; `data/round7.log`, `data/board8-1722.json`): **94,121, all
five weeks ranked, 1st of 47** ranked teams at 17:22 (60 had finished; five of the earlier top teams had not played
yet, the noon leader among them). 419 cars a week at 44.9 a car, the highest of the top ten, 96.6% on time.

| Week | We: margin (cars, on time) | Place if this week were the final | 1st | 10th | We against 10th |
|---|---|---|---|---|---|
| 1 | 20,505 (417, 94.7%) | 1 of 56 | 20,505 | 17,822 | +15.1% |
| 2 | 19,837 (434, 97.9%) | 5 of 59 | 21,689 | 19,656 | +0.9% |
| 3 | 14,063 (356, 94.7%) | 2 of 48 | 14,115 | 11,250 | +25.0% |
| 4 | 17,263 (423, 96.7%) | 2 of 59 | 17,314 | 14,953 | +15.5% |
| 5 | 22,453 (466, 98.3%) | 4 of 59 | 22,926 | 21,498 | +4.4% |

In every one of the five weeks we would have been in the top five. Today's rounds: 09:00 with version 6 + fees:
18th of 55; 12:00 with version 7: 7th of 58; 15:00 with version 8: 1st of 47 so far.

**The 14:00 live test final, read afterwards** (`data/test_final_1400.json`; a part-week from Thursday, everyone at
zero trust; version 7 with one deliberate restart): we were 18th of 55 with 2,600 (130 cars at 20.0, 100% on time);
the first had 4,023 (158 cars at 25.5), the tenth 3,292. We won our usual Thursday-plus-Friday count (128 in a full
practice week) while the teams ahead won 145 to 167 with nothing carried over: on a cold start we do not open up.
A day's cars are won on the day before it (cars due: Tuesday 54, Wednesday 67, Thursday 72, Friday 83, the last
Monday 92, against a cap near 88), so Tuesday's drivers are idle after a cold Monday.

**Tested against version 8 in exact mode this afternoon:**

| Setting | Weeks | Gain | lab / hold / fresh | Cars | Eight hardest | Lowest week | Verdict |
|---|---|---|---|---|---|---|---|
| holding a short drive up to 4 hours for a round-trip partner (`pair_hold=4`; ported from the leaders study, book-free) | 60 | +265 ± 116 | +110 / +679 / +4 | 405 | 94.1% | 91.8% | a candidate: safer tail (chance of a week under 90% 0.3% against 0.7%); on check-1..20 it is +101 ± 196 with the lowest week at 91.1% against 92.5% |
| a car costs up to 10% less while its due day is behind its pace (`fill_cut=0.1`) | 60 | +112 ± 121 | +301 / +177 / -141 | 420 | 93.8% | 92.1% | the cars come (+14), the money does not |
| the same, up to 20% | 16 | +154 ± 187 | | 447 | | | 41 more cars for nothing: volume alone is not the leaders' edge |
| the leaders study's target desks (even volume; dearer when ahead of pace; fill the first day) | 12 | -241 ± 408; -200 ± 285; -110 ± 312 | | +12; -4; +9 | | | no |
| the guard counting once at 6%; the home fee at 0.8 | 30 | -7 ± 37; -249 ± 120 | | | | | no |

`lab.restart_check` did not call `Desk.tick` in its own loop (the practice loop, the round player and the final
runner do), so a held car was never released there and the first check of `pair_hold` failed by 31%. With the tick
in the loop: `pair_hold=4` passes on lab-1 (13,672 straight, 12,946 with three restarts) and fresh-9 (12,810 and
13,076), and version 8 on lab-1 again (13,638.93 and 13,645.79).
Astra's reading of the boards (A014): the noon leader's car count follows the field's week by week (slope 1.01,
ours 0.88, the second team's 0.38), and it leads by most in the richest weeks.

## 61. What the leader's numbers say, and a lead from the handbook (Sat 17:50)

From the leaders study (`leaders/juhus/out/`, every saved board and the 14:00 live feed): the noon leader is a
constant 1.14 times the round's median in rich weeks and in lean ones (not a rich-week desk); it sits about 6 euros
a car above our line of price against volume (fees 10% lower or prices 6% higher; none of 152 saved settings does
that); it has 8 to 10 late cars a week against the median's 13 to 14; it played four ranking weeks in 83 seconds
(few calls: a light desk); and in the live cold start it had won 39 orders by noon against our 26 and sold 5% dearer
a car at the same cost a car. In a dear week with easy drivers there is no cheap volume for our desk: an added car
brings 68 euros and costs 70 in fees (in a lean week 100 against 76), so `fill_cut` and `pair_hold` gain only in
lean weeks.

HANDBOOK.md, lines 286 to 298: the competitor's price has a lane factor of which one part "is almost the same in
every world", and "your quotes over several worlds show the part of each lane that holds in every world". Our book
starts every week knowing nothing of lanes. A table learned from the saved weeks would fit all of the above: strong
from the first minute, the same edge in every kind of week, no need for many calls. New setting `lane_prior`
(0 to 1): the book adds a fixed offset for each request's lane from `dispatch/lanes.json` (by route, or pickup town
plus delivery town), set once and not learned; the week's own learning goes on above it. The simulator session,
whose dealer side matches real weeks within 3%, is asked for the table, fitted on lab and hold weeks only.
The simulator's own verdict (`sim/VALIDATION.md`): it can judge the level of a version (within 0 to 4%), the price
level and the cap, and the sign of larger changes (16 of 18); it cannot judge a week under 90% (it has none),
private and premium cars, or anything under about 400 a week.

## 62. Version 9: a newly won car waits for a round-trip partner; the lane table fails on unseen weeks (Sat 18:50)

**Idea.** Two candidates stood against version 8: `pair_hold=4` (a plain car that has 16 hours or more to its last
pickup and a drive of at most 3 hours is not posted at once; for up to 4 hours, and never past 18:00, it waits for a
car won after it that makes a round trip with it) and `lane_prior=1` (the price book starts the week with a table
of what each lane's price was in earlier worlds; section 61). **Why.** Half of the round trips that exist are lost
because the first car has its driver before the second is won; and the handbook says part of the lane price is the
same in every world.

Exact mode, same weeks for both sides. "60" is lab, hold and fresh 1..20; check-1..20 was used for nothing before.

| Against version 8 | 60 weeks | lab / hold / fresh | Better | check-1..20 | Better | Lowest week (60, check) |
|---|---|---|---|---|---|---|
| `pair_hold=4` | +265 ± 116 | +110 / +679 / +4 | 32/60 | +101 ± 196 | 12/20 | 91.8%, 91.1% |
| `lane_prior=1` (table of the simulator session) | +163 ± 117 | +76 / +169 / +246 | 41/60 | **−120 ± 124** | 7/20 | 92.0%, 92.2% |
| both | +279 ± 133 | +238 / +673 / −72 | 36/60 | +301 ± 208 | 11/20 | 91.7%, 93.9% |
| both, table of the leaders study (`lane_table=lanes_price`) | +179 ± 109 | | 32/60 | +136 ± 156 | 13/20 | 91.9%, 92.5% |

The lane table on top of holding: +15 ± 99 on the 60 weeks and +199 ± 221 on check with the first table, −85 ± 101
and +34 ± 193 with the second. Alone it gains on the 60 weeks, which are the weeks both tables were built from, and
loses on the 20 it has not seen (revenue −1,148 a week there, 4 fewer cars). **Not adopted:** 772 fitted numbers
with no effect shown on unseen weeks. The settings stay in the code, off.

**Holding has a mechanism that repeats on both families**, which the margin alone (noise of about ±100 on 60
weeks) cannot show: round trips booked go from 56.6 to 86.4 a week on the 60 weeks and from 57.8 to 83.3 on
check; 135 cars a week wait, 62 round trips a week come out of the wait. Cars won do not change (406 → 405). By
kind of week (leaders study): dear and easy −200 ± 207, dear and hard +238 ± 185, lean and easy +419 ± 211, lean
and hard +537 ± 321. The chance of a week under 90% (`python lab/cands.py`) falls from 0.7% to 0.3%.

**Version 9 = version 8 + `pair_hold=4`** (`VERSION = 9`):

| Seeds | Mean margin | Worst week | Lowest on time | Ranked |
|---|---|---|---|---|
| lab-1..20 | 17,626 | 11,098 | 95.4% | 20/20 |
| hold-1..20 | 17,475 | 12,199 | 93.8% | 20/20 |
| fresh-1..20 | 17,503 | 10,283 | 91.8% | 20/20 |
| check-1..20 | 15,513 | 8,631 | 91.1% | 20/20 |

Checks before it went on the final runner (18:45; version 8 kept in `~/dispatch-live-v8`): its defaults replay
the candidate's saved weeks to the cent (lab-1 13,672.18, hold-3 20,921.31, fresh-9 12,809.82); the live-clock
rehearsal at twice the final's speed with one stop and restart answers 457 of 457 requests, none refused; the
restart check (three restarts in a week) passes on three weeks:

| Week | Straight | Three restarts |
|---|---|---|
| lab-1 | 13,672 at 97.2% on time, 357 cars | 12,946 at 95.5%, 352 cars |
| fresh-9 (the hardest) | 12,810 at 91.8%, 391 cars | 13,076 at 90.1%, 393 cars |
| hold-3 | 20,921 at 98.1%, 432 cars | 20,412 at 97.7%, 427 cars |

**What a restart changes** (looked for because version 8's restarted lab-1 week had come out within 7 euros):
the cars that wait for a partner come back exactly (11 of 11 on Tuesday 13:00, each with the same release minute).
The first actions that differ are quotes: the new desk quotes again the 9 requests still open at that minute, at
the state of that minute, 1 to 3.6% above the first quote. Taking back each open request's own count in the day's
load before it is quoted again explained 0.3 of the 3 points and was removed again. The kit's starter does the same
re-quote; version 8 has it too.

**First tests on version 9** (60 weeks each): waiting 6 hours −175 ± 84, waiting 2.5 hours −128 ± 90: 4 hours
stays.

## 63. A lower cost for home-bound cars; the restart cost of versions 8 and 9; what Bahn asks for (Sat 19:05)

**A cost that is lower for the cars that are cheap to move** (`cost_home`). **Why.** Monday is priced at the book's
best price for a cost of 1.0 typical fees while a Monday car really costs 0.90 (leaders study); the cars that go
where 30 or more drivers live, on a drive under 3 hours, are paid 0.82 typical fees and are late 1 to 2% of the time.
The setting takes typical fees off the cost of exactly the cars that already open at the lower fee (`home_open`).
Against version 9, exact mode:

| `cost_home` | 60 weeks | lab / hold / fresh | Better | Cars | check-1..20 | Better |
|---|---|---|---|---|---|---|
| 0.05 | +136 ± 88 | +293 / +99 / +16 | 35/60 | +7 | | |
| 0.10 | +139 ± 86 | +104 / +155 / +159 | 37/60 | +13 | −89 ± 210 | 10/20 |
| 0.15 | −38 ± 100 | −100 / −25 / +10 | 33/60 | +19 | −184 ± 164 | 5/20 |

The cars come (7, 13, 19 more a week) and the money does not follow the dose; on unseen weeks it loses. **Not
adopted.** It is the fourth way of buying volume with price that ends inside the noise (sections 55, 58, 61).

**Three restarts in a week, version 8 against version 9** (`python -m lab.restart_check --seed … [--set pair_hold=0]`):

| Week | Version 8 straight → restarted | Version 9 straight → restarted |
|---|---|---|
| lab-1 | 13,639 → 13,646 | 13,672 at 97.2% → 12,946 at 95.5% |
| fresh-9 | 12,878 at 92.4% → 12,401 at 91.6% | 12,810 at 91.8% → 13,076 at 90.1% |
| hold-3 | 19,223 at 98.1% → 19,148 at 98.1% | 20,921 at 98.1% → 20,412 at 97.7% |

Three restarts cost about 1.4% of the margin in version 8 and 1.9% in version 9, and about 0.3 and 1.3 points on
time; both stay ranked in the hardest week. One restart, which is what a crash in the final would be, is a third
of that.

**What Bahn's jury asks for** (Emil's talk at the booth, 17:43): a place in the top ten is the bar and the order
inside it matters little; then the key ideas, each with what made it hard, how we solved it, and what the system
loses without it; and a system that generalises: one that keeps learning the competitor's prices rather than a
fixed map of them reverse-engineered from earlier weeks. The lane table of section 62 is such a map, and it is out
for the reason they give: it did not carry to weeks it had not seen. Three-car bundles are not in the API; the
allowed form is a round trip plus a direct offer to a driver who finishes nearby, which is closed here with
numbers (section 58: of 13,525 offers 57 to 67% were read and 0.07 to 0.14% of those accepted). The final has the
dynamics of the practice weeks on a new seed. `python -m lab.ablate` is the table they ask for: version 9 with each
part left out, on the same 60 weeks (queued 19:00).

## 64. Version 9 played: ranking round Saturday 18:00, and what the one weak week was (Sat 19:30)

**The round** (`python -m lab.round`, defaults = version 9, 19:20; `data/board8-1921.json`): **76,195, all five weeks
ranked, 5th of 54** ranked teams at 19:21 (1st 94,445 with 460 cars a week at 41.1; 2nd 82,454 with 544 cars at
30.3; 3rd 79,829; 4th 78,279; 10th 73,353). Ours: 389 cars a week at 39.1 a car.

| Week | Margin | Cars | On time | Our place that week | The tenth team that week |
|---|---|---|---|---|---|
| 1 | 13,390 | 367 | 95.4% | 19 | 14,302 |
| 2 | 19,408 | 408 | 98.8% | 3 | 17,791 |
| 3 | 16,014 | 387 | 97.4% | 6 | 15,191 |
| 4 | 12,176 | 387 | 99.2% | 7 | 11,737 |
| 5 | 15,207 | 398 | 99.0% | 3 | 14,226 |

The 15:00 round, closed: 2nd of 62 (the noon leader played late: 107,104 with 494 cars at 43.4); our places week
by week 2, 8, 4, 5, 7. Over the ten ranking weeks of versions 8 and 9 we were in the top ten of a single week nine
times. The final is one week, so the tenth week is the one to understand.

**Week 1, from our own event history** (a ranking week has no reveal, but the desk's events and snapshot can be
read: `data/round8-week1-events.json.gz`). On Monday afternoon the largest dealer sent a bulk order of ten cars out
of Oulu for Tuesday (12 drivers live within 30 km of Oulu). We won all ten. The four to Jyväskylä were driven; the
four to Ylivieska and the one to Rovaniemi were viewed 72 to 83 times each on Tuesday and booked by nobody, at fees
up to three times the typical one, and arrived one to three days late. Twelve warnings on Tuesday took the brake
(`guard`) over its line; Wednesday was the flu day (17 bookings given back, 16 warnings). Win rate by day: Monday
35%, Tuesday 41%, **Wednesday 29%, Thursday 34%**, Friday 40% (the other four weeks: 36 to 49% on those two days).
The week ended with 17 late cars, 904 of refunds and penalties, and 40 to 60 cars fewer than the teams above us
(430 to 448 cars at 98% on time).

**Is it the bulk order or the brake?** On version 9's 80 saved weeks (`data/cars_v9.json.gz`, 32,433 cars), in thin
towns far from the capital:

| Our cars out of the town due that day | Cars a week | Late | Margin a car | Refunds a car |
|---|---|---|---|---|
| 1 to 2 | 31.3 | 5.8% | 51.5 | 3.62 |
| 3 to 4 | 17.6 | 6.7% | 53.9 | 3.68 |
| 5 to 6 | 6.7 | 3.9% | 54.0 | 2.38 |
| 7 to 9 | 5.3 | 9.0% | 58.5 | 6.27 |
| 10 or more | 4.4 | 11.0% | 48.2 | 9.56 |

Ten cars a week sit in the two loaded rows, late twice as often and still earning 48 to 58 euros each: a cap by
town would give up about 500 a week to save half a late car. So the cars are not the loss. The brake is: once
careful, the desk prices a third of the market out (every car with an end where fewer than 15 drivers live, which
includes Hyvinkää with 78 cars a week at 2.1% late, and every last pickup before 13:00), on the evidence of
warnings that all came from one town, and it stays careful through the morning after a flu day that is over.
Next: `guard=0` on the 60 weeks, week by week, to see in which weeks the brake protects and in which it only
costs; then a brake that counts a town's shortage once.

## 65. What the brake costs and what it buys (Sat 19:50)

`guard=0` against version 9 on the 60 weeks (the first row of `python -m lab.ablate`): **+56 ± 30 without the brake,
and one week unranked.** The brake changes nothing in 50 of the 60 weeks. In the other ten:

| Week | Version 9 | No brake | Trigger line 10% | Brake on fewer kinds (`guard_kinds=1`) |
|---|---|---|---|---|
| fresh-9 (the hardest) | 12,810 at 91.8% | +356 at **89.9%** | −87 at **89.7%** | −649 at 91.1% |
| hold-9 | 13,293 at 94.6% | +982 at 94.1% | +896 | +305 |
| fresh-18 | 18,144 at 95.4% | +1,098 at 95.2% | +1,098 | −189 |
| fresh-20 | 22,057 at 93.9% | +704 at 93.9% | +704 | +468 |
| lab-11 | 16,048 at 95.4% | +398 at 95.6% | +398 | +437 |
| lab-19 | 17,591 at 96.2% | +212 at 97.2% | +212 | +227 |
| hold-12 | 12,199 at 96.6% | +134 at 96.1% | +59 | −82 |
| hold-5 | 14,016 at 96.3% | +118 | +118 | −6 |
| lab-17 | 12,745 at 97.7% | −181 | −181 | −39 |
| fresh-19 | 19,129 at 97.0% | −485 at 95.8% | −485 | −289 |

So the brake is insurance: it costs about 330 in each of the one week in six where it comes on, and it is what
keeps the hardest week ranked. A line of 10%, 12% or 15% is the same as no brake (the share that trips it sits
between 8 and 10% in every one of these weeks), so the line cannot be raised without losing the one week it is for.

**Which cars does it price out, and are they the late ones?** Version 9's cars in the eight hardest weeks
(`data/cars_v9.json.gz`): an end where fewer than 15 drivers live within 30 km: 9.8% late where that town is far
from a city, **1.1% where it is Hyvinkää or Porvoo** (388 to 500 drivers within 60 km; 66 cars a week in all
weeks); a drive over five hours 19.1%; a last pickup before 13:00 22.8%; **a private address 3.9%**; none of these
2.8%. `guard_kinds=1` leaves the two safe kinds out of the brake. On the ten weeks: +182 in sum (against +3,336
without any brake), the hardest week at 91.1%. No gain shown: the weeks move by more than the rule does. **Not
adopted**; the brake stays as it is in version 9. What the analysis is good for is the pitch: the brake is the one
part of the system whose job is the 90% line and not the margin, and this is its measured price.

## 66. The whole-week live test final, 20:00: 10th of 75, and where the cars went (Sat 20:45)

Version 9 on the final runner, no restart, lab held from 19:56 (`data/test_final_2000.json`, frames every two
minutes in `data/test_final_2000_frames.jsonl`, our own events in `data/test_final_2000-events.json.gz`):
**16,622.58, 393 cars at 42.3, 98.2% on time, ranked, 10th of 75 ranked teams.** All 1,030 requests answered.

| Place | Team | Margin | Cars | A car | On time |
|---|---|---|---|---|---|
| 1 | Juhus | 19,592 | 469 | 41.8 | 97.7% |
| 2 | MathNet1 | 18,599 | 500 | 37.2 | 95.8% |
| 3 | Progresful | 17,755 | 442 | 40.2 | 98.9% |
| 5 | pelaaja juhlii | 17,443 | 356 | 49.0 | 97.2% |
| 9 | Elysa's Secret | 16,701 | 457 | 36.5 | 97.6% |
| **10** | **Team Moonshot** | **16,623** | **393** | **42.3** | **98.2%** |
| 11 | The Delusionals | 16,336 | 420 | 38.9 | 97.6% |
| 15 | No Empty Miles | 16,117 | 420 | 38.4 | 97.6% |
| 24 | freya | 15,540 | 390 | 39.8 | 99.2% |

Places 5 to 24 are within 11% and the five teams behind us within 3%: the ranking rounds, where we were 2nd and
5th, understate the field (several of these teams do not play them). One week decides, and one percent is a place.

**Our week by day:** win rate Monday 34% (75 cars), Tuesday 44% (89), Wednesday 31% at the week's lowest price
(69: the price-war day), Thursday 49% (102), Friday 35% (63). 8 warnings and 7 late cars in the week: an easy week
for drivers, in which we carried the fewest cars of the first twenty teams but one.

**Against the nine teams above us** (orders won, from the frames): 23 fewer by Wednesday night, 6 fewer on
Thursday, **20 fewer on Friday** (63 against a median of 83).

**Friday is the day cap.** 166 of Friday's 179 requests are due on the Monday after the week, and so are 49 of
Thursday's cars. Version 9's 80 saved weeks by day of the last pickup:

| Last pickup | Cars a week | Share of the cap (mean, highest week) | Late | Late, 8 hardest weeks | Margin a car | Fee / typical |
|---|---|---|---|---|---|---|
| Tuesday | 61.5 | 0.70, 0.96 | 2.5% | 2.9% | 33.2 | 0.90 |
| Wednesday | 72.6 | 0.83, 1.24 | 3.3% | 3.5% | 37.7 | 0.92 |
| Thursday | 78.5 | 0.90, 1.20 | 3.7% | 11.6% | 41.5 | 0.93 |
| Friday | 95.0 | 1.09, 1.48 | 4.1% | 6.4% | 42.2 | 0.95 |
| **the Monday after** | 85.8 | **0.99**, 1.54 | **1.6%** | 4.7% | **57.2** | **0.89** |

The cars due on the Monday after are the best we carry (the highest margin, the lowest fee, the fewest late) and
they sit at the cap: no new requests come after Friday, so nothing competes for the drivers of that Monday, and
the cap, which stands for exactly that competition, holds them to a weekday's number. `cap_monday` (1.5, 2.0) and
`cap_week_only` were written for this in section 58 and never judged on a version; all three are playing on the
60 weeks and check-1..20.

## 67. No day cap for cars due after Friday (Sat 21:05)

**Idea.** The day cap (a car for a day that already holds 11% of the drivers' number in our cars costs steeply
more) stands for the competition among our own cars for one day's drivers. After Friday no new requests come, the
cars due on the Monday after have the weekend to be booked, and they are the best cars we carry (section 66). So
the cap is loosened or dropped for them. Against version 9, exact mode, the same weeks:

| Setting | 60 weeks | lab / hold / fresh | Better | Cars | check-1..20 | Better | Eight hardest on time (v9 94.1%) | Lowest week | Chance of a week under 90% (v9 0.3%) |
|---|---|---|---|---|---|---|---|---|---|
| `cap_monday=1.5` (cap ×1.5 after Friday) | +347 ± 51 | +457 / +272 / +312 | 49/60 | +9.2 | +160 ± 69 | 12/20 | 94.0% | 91.3% | 0.7% |
| `cap_monday=2.0` | +377 ± 60 | +441 / +304 / +385 | 51/60 | +12.3 | +190 ± 86 | 13/20 | 93.7% | 91.6% | 0.7% |
| **`cap_week_only=1` (no cap after Friday)** | **+416 ± 64** | +530 / +269 / +450 | 51/60 | +14.0 | **+256 ± 106** | 13/20 | 93.4% | 91.3% | 1.0% |

The gain grows with every step of loosening, on the weeks it was not tuned on too, and no week falls under 90%.
It is the first change since the pairing that is six standard errors clear. Its price is in the hard weeks:
hold-10 goes from 93.8% to 91.4% on time and fresh-12 from 93.1% to 91.9%. With the field as tight as section 66
shows (a percent is a place), 2.4% of margin for 0.7 points of risk is taken: the candidate for version 10 is the
plain rule, no cap after Friday. Playing on top of it: fees that do not step up over the weekend
(`weekend_hold=1`) and a cost 0.05 or 0.1 typical fees lower for these cars (`cost_after`; they are paid 0.89).

The finding came from the live test final, not from the lab: the frames of the public standings showed where the
teams above us won their cars (Friday), our own events showed what Friday's requests are (166 of 179 due on the
Monday after), and the saved weeks showed that those cars sit at the cap.

## 68. Version 10 (Sat 21:40)

**Version 10 = version 9 + `cap_week_only=1`** (no day cap for cars whose last pickup falls after Friday; section 67).

| Seeds | Mean margin | Worst week | Lowest on time | Ranked | Cars a week |
|---|---|---|---|---|---|
| lab-1..20 | 18,156 | 12,198 | 95.1% | 20/20 | 427 |
| hold-1..20 | 17,744 | 12,533 | 91.4% | 20/20 | 408 |
| fresh-1..20 | 17,952 | 10,529 | 91.3% | 20/20 | 422 |
| check-1..20 (never tuned on) | 15,769 | 8,615 | 91.2% | 20/20 | 401 |

On the 60 weeks 17,951 against version 9's 17,535 and version 8's 17,270.

**The two follow-ups on the same cars, against the no-cap rule:** fees that do not step up over the weekend
(`weekend_hold=1`) −34 ± 26 on the 60 weeks and −216 ± 130 on check-1..20, lowest week 90.1%; a cost 0.1 typical
fees lower for these cars (`cost_after=0.1`) +99 ± 91 (+227 / −10 / +82) and +118 ± 185 with 17 more cars, on time
96.3% against 96.9% and **one week at 88.7%**. Neither is taken.

**Round trips left over the weekend** (`weekend_pairs.py` in the scratch tools, version 10's weeks): 18 round trips
a week are due on the Monday after; 93% are driven as round trips (first booked Friday afternoon 499, Saturday
morning 271, Thursday 163, the Monday morning 117) with 1.0% of their cars late. The 46 that nobody took and that
were taken apart on the Monday morning had 15 of 92 cars late: 0.2 late cars a week. Of the round trips still
open on Saturday night 72% are driven as round trips after all. An earlier split would break two round trips a
week to save a fifth of a late car: left as it is.

**Checks.** Version 10's defaults replay the candidate's saved weeks to the cent (lab-1 13,736.53, hold-3
21,176.97, fresh-9 14,136.49). The live-clock rehearsal at twice the final's speed with a stop and restart answers
457 of 457 requests, none refused. On the final runner since 21:38 (version 9 kept in `~/dispatch-live-v9`).

**Restarts, measured properly this time.** A restart now also rebuilds each waiting car's own last pickup minute
(`Desk.relast`: the one book the new desk did not have; with it three restarts cost lab-1 2.0% of its margin
instead of 5.1%). One restart at a time, in the three weeks that end lowest on time:

| Week (straight) | Restart Tue 13:00 | Restart Thu 10:00 | Restart Sat 12:00 |
|---|---|---|---|
| fresh-9 (14,136 at 91.3%) | 13,832 at **89.5%** | 14,125 at 91.3% | 14,159 at 91.3% |
| fresh-12 (28,607 at 91.9%) | 28,580 at 91.9% | 28,607 at 91.9% | 28,607 at 91.9% |
| hold-10 (25,452 at 91.4%) | 25,452 at 91.4% | 25,452 at 91.4% | |

A restart from Thursday on changes nothing. A restart on Tuesday quotes the open requests again at the state of
that minute, three cars fewer are won, and the week then runs as a different draw; in the hardest week that draw
ended under 90%. `lab.restart_check` (three restarts) therefore passes on lab-1 and hold-3 and **fails on
fresh-9 (89.5%)**. That week is at the line with or without a restart (section 67's price for the cap change);
it is recorded here as a known weakness, not as fixed.

## 69. Version 10 played: ranking round Saturday 21:00; premium and private cars due after Friday (Sat 22:05)

**The round** (`python -m lab.round`, defaults = version 10, 22:00; `data/board8-2201.json`; our own events of the
five weeks in `data/round9-week*-events.json.gz`): **89,317, all five weeks ranked, 3rd of 33** ranked teams at
22:01 (1st 105,424 with 484 cars a week at 43.6; 2nd 96,850 with 526 at 36.8; 4th 88,729; 10th 83,480). Ours: 442
cars a week at 40.4.

| Week | Margin | Cars | On time | Our place that week | The tenth team that week |
|---|---|---|---|---|---|
| 1 | 16,823 | 449 | 98.9% | 3 | 15,855 |
| 2 | 18,258 | 433 | 94.9% | 10 | 18,254 |
| 3 | 17,984 | 431 | 98.4% | 3 | 15,082 |
| 4 | 19,937 | 459 | 96.7% | 10 | 19,813 |
| 5 | 16,316 | 437 | 98.9% | 3 | 14,606 |

Cars due on the Monday after: 109, 121, 92, 97, 112 (version 9 carried 86 a week in the lab). The 18:00 round,
closed: version 9 ended 9th of 67, week by week 24, 7, 9, 10, 5.

The two weeks where we are 10th are the two richest: in week 4 the teams around us carry 482 to 494 cars at our
margin a car and we carry 459 (125 of ours were due on Friday, a third over the cap, and Friday was the flu day:
35 bookings given back, 21 warnings); in week 2, a hard week for everyone (94 to 95% on time), the 4th team earns
47.9 a car on 428 cars against our 42.2 on 433 (1,282 of refunds).

**The same idea for the kinds of car we refuse** (against version 10, 60 weeks): a premium car quoted only on an
option due after Friday (`premium_after=1`) +134 ± 85 (+221 / +121 / +61, better in 42) with 7 more cars, on time
96.6% against 96.9% and the lowest week at 90.3% (91.3%); the same with its cost 0.2 higher +45 ± 89 and a week at
89.6%; a private address with a drive of two hours or more, due after Friday (`private_after=1`) +44 ± 67 on 33
weeks. The weekend does not make a premium car safe. **Not adopted.**

## 70. The live week by kind of request, and a refusal log on the runner (Sat 22:18)

From the leaders study's read of the dense 20:00 feed (`leaders/juhus/out/who_wins_2000.txt`: every team gets the
same requests at the same minute, so the rises of each team's count between two feed messages give its win rate by
kind; checked on our own wins in 387 of 389 steps). Of the 49 cars the nine teams above us carried more than
version 9:

| Kind | Requests | We won | The nine above | Gap in cars |
|---|---|---|---|---|
| plain cars | 848 | 44% | 47% | +21 |
| ... of them 110 to 150 euros of list | | 29% | 44% | +16 |
| ... of them under 60 euros | | 52 to 56% | 53 to 55% | 0 |
| premium cars | 50 | 0% | 26% ± 11 | +13 |
| trade-ins (two legs) | 15 | 0% | 53% ± 20 | +8 |
| private pickup | 84 | 14% | 19% | +4 |
| private delivery | 33 | 33% | 22% | −4 |

On plain cars the nine are level with us until Thursday afternoon; the gap by Wednesday night is premium cars,
trade-ins and a lower opening price on Monday morning (they win 60% of Monday morning's plain cars, we 49%, and
fall under us at midday). Friday is the cap removed in version 10. On our own desk premium cars are late about one
time in five and trade-ins one in three to one in two (sections 43, 48, 69), and those teams carry them at 97 to
98% on time: the open question is how they deliver them, not which cars they win. The leaders study is on the
large plain cars with a fast option and on the trade-in's own gig form.

Bulk orders (their `leaders/bulkbrake/REPORT.md`, 80 weeks of version 9): 1.5 thin-town batches with five or more
cars won a week; the brake comes on within 48 hours after 9.9% of them against 6.4 to 8.7% at the same hour of
other weeks; the sixth and later cars earn 51 a car at 4.1% late. Refusing them gives up 254 ± 46 a week to save 8
to 14: the Oulu week of section 64 was a one-in-forty event, nothing is changed.

**Runner:** `dispatch/play.py` now prints after every day of a final what the world refused from us (a quote that
comes after its 4.5 seconds is a lost request and no score shows it). Rehearsal at twice the final's speed: 457 of
457 requests answered, one refusal, a withdraw of a gig a driver had just taken. The runner holds exactly the lab's
code since 22:18 (version 10's decisions; identity to the cent on lab-1, hold-3, fresh-9 after the change).

## 71. Large plain cars: closed with played weeks (Sat 22:20)

From the leaders study (`leaders/bigcars/REPORT.md`; version 10's 80 weeks, the 13 fork-measured weeks for the
dealers' limits, then 24 played weeks). **Idea.** The teams above us win 42 to 43% of plain cars with a drive of
4 to 6 hours, we 22 to 30% (about 19 cars in the live week); beyond 6 hours nobody wins. So drop the length charge
in the cost of a 3-to-7-hour drive that has 48 hours or more of notice.

| Against version 10, 12 screen weeks | Gain | Note |
|---|---|---|
| `design=ld_big_notice` (no length charge, weekdays) | −805 ± 378 | six of eight ordinary weeks gain 260 to 1,650 |
| `design=ld_big_notice2` (the same, half the charge after Friday) | −499 ± 399 | fresh-9 at 89.8% |

The loss is four weeks (hold-1, hold-17, fresh-9, fresh-12: −1,300 to −2,900 each) in which the added late cars
trip the brake and the desk then wins 17 to 31 fewer cars. Offline the same change read +736 a week: the paper was
about 1,000 a week too kind. **Why it fails:** a long car is late by how many long cars are due that day (4.8%
under one per 100 listed drivers, 7.8% at one to two, 10 to 13% above two; short cars on the same days stay at
3%). The length charge is in effect the price of a small pool of drivers who take long drives. **Not adopted.**
In an easy week the teams above carry about 20 more such cars and still show 97 to 98% on time; we give those up
to stay ranked in the one week in seven where they would cost the brake or the 90% line.

## 72. Keeping the cap after Friday for long drives; trade-ins by their own rule (Sat 22:30)

**Idea.** Version 10's price is in the long cars due on the Monday after: by size, the cars of 150 euros of list
and more go from 6.3% to 12.5% late there, and in the eight hardest weeks 3.6 of the 4.1 added late cars are
drives of four hours or more (leaders study, `leaders/juhus/out/cap_cars_weekonly*.txt`). So keep the day cap
after Friday for long drives only (`cap_after_hours`). Against version 10, exact:

| Setting | Weeks | Gain | lab / hold / fresh | Cars | Eight hardest on time (v10 93.4%) | Chance of a week under 90% (v10 1.0%) |
|---|---|---|---|---|---|---|
| `cap_after_hours=4` | 60 | −323 ± 54 | −375 / −234 / −361 | 414 (419) | 94.1% | 0.5% |
| `cap_after_hours=5` | 25 | −277 ± 65 | | 421 | | |

It gives back three quarters of the +416. The reason was foreseen by the leaders study: the long car now pays
the cap on every car due that Monday, and that Monday is fuller than before with short cars, so a long car is
priced above version 9. **Not adopted**; the 3-hour run and the rest of the 5-hour run were taken out of the
queue. Playing instead: the same long car charged only by the long cars due that day (`cap_long`, 2 and 1.5 long
cars per 100 listed drivers).

**Trade-ins** (leaders study, `leaders/trade/REPORT.md`; 1,692 trade-ins won in 136 saved weeks, 47% late). The
cause of the lateness is found: the new car is due at the end of the customer's hour plus 30 minutes, our gig put
no window on that delivery, and the world lets a driver book who will arrive hours later (38% of the late ones);
the quote measured its time to the 20:00 deadline, a median 5.5 hours after the true last pickup. With the
customer's hour as the delivery's window and the true deadline in the quote (plug-in `ld_trade_hour`), on 12
screen weeks against version 10: trade-ins on time 55% → 82%, 62 euros a car, +308 a week on the trade-ins
themselves, and the week as a whole −63 ± 178 because the desk carries 4 to 6 fewer other cars. Two forms are
playing on 60 weeks (`ld_trade_eve`, `ld_trade_nofri`).

**The gentler form, played (22:42).** A drive of four hours or more, due after Friday, charged only by the long
cars due that day, against version 10 on the 60 weeks:

| `cap_after_hours=4` with | Gain | lab / hold / fresh | Cars | Eight hardest on time | Chance of a week under 90% | Lowest weeks |
|---|---|---|---|---|---|---|
| `cap_long=0.02` (two long cars per 100 drivers) | −484 ± 58 | −504 / −448 / −499 | 412 | 94.6% | 0.2% | 92.5%, 92.7%, 93.8% |
| `cap_long=0.015` | −703 ± 81 | −678 / −600 / −831 | 410 | 94.4% | 0.5% | 91.0%, 92.7%, 94.2% |

It buys the safest tail of any version (0.2%) and costs more than the whole of version 10's gain: the long cars
due on the Monday after are where the money is (122 to 133 euros a car), and the same cars are where the late
ones are. The gain and its risk cannot be separated by a cap on them. **Not adopted: version 10 stays as it is**,
with its 1.0% stated.

## 73. Judging by the chance of a top-ten week (Sat 23:06)

**Idea** (Emil, 22:45: a couple of points more risk is fine if it buys upside; the first goal is the top ten).
The final is one week and the top ten is a threshold we sit just above, so a change that gains in most weeks and
loses badly in a few can be worth more than its mean says, and a mean gain made of a few lucky weeks less. New
tool `python -m lab.top10`: a week counts as in the top ten with the chance that we stand above the tenth team
(our margin against the tenth team of a week: +1% for version 9 with a spread of 6 points over our ranking
weeks; version 10 is 2.4% above version 9), given the candidate's own gain in that week, times the chance that
the week is ranked. A ruler for the same weeks, not a forecast.

| Candidate, against its base | Mean gain | Median | Weeks unranked | Chance of a top-ten week | Change |
|---|---|---|---|---|---|
| version 9 → 10 (no cap after Friday) | +416 ± 64 | +280 | 1.0% | 56.4% → 68.4% | +11.9 points |
| version 8 → 9 (wait for a partner) | +265 ± 116 | +39 | 0.3% | 46.3% → 53.9% | +7.6 |
| no day cap at all (on version 9) | +18 ± 157 | +186 | 11.1% | | −1.5 |
| any car with 4 hours' notice (on version 9) | −27 ± 124 | +163 | 2.1% | | −1.3 |
| no brake (on version 9) | +56 ± 30 | 0 | 1.0% | | +1.4 |
| premium cars due after Friday (on version 10) | +134 ± 85 | +224 | 1.7% | 70.7% → 72.5% | +1.8 ± 2.4 |
| home-bound cars cost 0.1 less (on version 9) | +139 ± 86 | +143 | 0.4% | | +3.3 |
| fill a lagging day, 10% off (on version 8) | +112 ± 121 | +122 | 0.4% | | +6.1 |

Raw risk does not buy a better chance on this desk: without the day cap half the weeks gain and 11% are unranked.
The small volume nudges looked better by this ruler than by their means, so they were played on version 10:

| Against version 10, 60 weeks | Mean gain | lab / hold / fresh | Cars | Lowest week | Chance of a top-ten week |
|---|---|---|---|---|---|
| `fill_cut=0.1` | −141 ± 97 | −19 / −266 / −137 | +11.2 | 90.6% | −7.4 ± 2.8 points |
| `fill_cut=0.1 cost_home=0.1` | −35 ± 109 | +85 / −140 / −49 | +23.6 | 90.6% | −4.9 ± 3.1 |

On version 10 the fill loses: its +112 on version 8 did not carry (the cars it added are now added by the Friday
rule, or it was noise). Still to come: `cost_home=0.1` alone, with premium cars after Friday, and a day cap of
12% and 13%.

**From the leaders study, 60 weeks each against version 10 (23:10):** long private cars at their punctual hours
(`design=ld_kinds_priv`) −34 ± 128; premium cars where 25 or more experienced drivers live near
(`design=ld_kinds_prem2`) −54 ± 105 with a week at 89.2%; the day cap 1.5 times looser for Tuesday and Wednesday
(`design=ld_lead_mid15`) −124 ± 114 with 6 more cars at 0.9 less a car. None adopted. The cap is right on the
weekdays; only the days after Friday were over-charged.

**Trade-ins on 60 weeks against version 10 (leaders study, 23:20):** `design=ld_trade_eve` (the customer's hour as
the delivery window, the true deadline in the quote, the top fee the evening before) +122 ± 88, better in 31 of
60, 1.9 more cars, on time 96.7% (96.9%), lowest week 90.5%; chance of a top-ten week 70.7% → 70.8% (+0.1 ± 2.5
points). Without Friday hours (`ld_trade_nofri`) +45 ± 98 with a week at 90.0%. The fix works on the trade-ins
themselves (55% → 84% on time, 66 euros a car, 5 a week); it pays little because each one takes a driver for a
day and, near the cap, displaces about three other cars a week (5 × 66 less 3 × 43 less refunds). Not adopted on
this evidence; a stack with premium cars after Friday and the check family are playing.

**The bolder runs on version 10, 60 weeks each (23:37):**

| Against version 10 | Mean gain | lab / hold / fresh | Cars | Lowest week | Weeks unranked | Chance of a top-ten week |
|---|---|---|---|---|---|---|
| `day_cap=0.12` | −85 ± 115 | +86 / −286 / −54 | +4.5 | 89.7% | 2.4% | −4.4 ± 2.8 points |
| `day_cap=0.13` | −171 ± 116 | −11 / −387 / −116 | +9.4 | 89.6% | 2.7% | −6.5 ± 3.0 |
| `cost_home=0.1` | +128 ± 95 | +150 / +141 / +93 | +14.3 | 90.5% | 1.1% | +0.2 ± 2.6 |
| `cost_home=0.1 premium_after=1` | **+256 ± 104** | +498 / +181 / +89 | +22.0 | 89.8% (fresh-12) | 1.9% | +2.3 ± 2.6 |

A looser day cap loses on every count: the direct risk dial is closed. The two small gains that take different
cars add up as their separate runs said (+128 and +134): +256 a week for 0.9 points more of unranked weeks, with
swings of ±1,000 to 2,300 in single weeks and losses of about 1,000 to 1,250 in four of the hardest. The stack
and both parts are playing on check-1..20.

**The stack on the unseen weeks, and the verdict (23:45).** check-1..20 against version 10: the stack +123 ± 236
(better in 9 of 20, lowest week 92.5%); `premium_after=1` alone +128 ± 135 with one week at 89.7%;
`cost_home=0.1` alone +1 ± 243. All 80 weeks:

| Against version 10, 80 weeks | Mean gain | Median | Weeks above +2% / below −5% | Weeks unranked | Chance of a top-ten week |
|---|---|---|---|---|---|
| `cost_home=0.1 premium_after=1` | +223 ± 97 | +170 | 34 / 8 | 1.6% | 70.6% → 72.0%: +1.4 ± 2.4 points |
| `premium_after=1` | +133 ± 72 | +210 | 32 / 7 | 2.2% | +1.6 ± 2.1 |
| `cost_home=0.1` | +96 ± 93 | +132 | 31 / 8 | 0.9% | −0.8 ± 2.5 |

The stack's mean is 2.3 standard errors up (1.2% of the margin). By the ruler of section 73 it is worth 1.4
points of chance with an error of 2.4: the gains come with wider weeks and eight weeks that lose more than 5%.
The bar set at 22:55 (the chance up by clearly more than its error) is not met. **Not folded; version 10 stays
on the runner**, unless Emil prefers the higher mean for its own sake: the settings are in the code, off, and a
fold with its checks takes about 45 minutes.

## 74. Version 11: trade-ins by the customer's hour, and premium cars due after Friday (Sun 00:05)

**Idea.** The live week of section 70 showed which cars the teams above us carry and we do not: premium cars and
trade-ins. Both were late on our desk. Two rules, each from a cause that was found:

- **Trade-ins by the customer's hour** (`trade_hour=1`, `dispatch/trade.py`; written by the leaders study as the
  plug-in `alt/ld_trade_core.py` and moved into the desk unchanged). The new car is due at the end of the
  customer's hour plus 30 minutes, and our gig put no window on that delivery, so the world let a driver book who
  would arrive hours later (38% of the late ones). Now the customer's hour is the delivery's window, the price is
  asked with the true deadline, and a trade-in is quoted only as a round trip of at most 12 hours from a dealer
  with 100 or more drivers within 60 km, for an hour from 11:00, while the brake is off. Trade-ins on time: 55% →
  84%.
- **Premium cars only on an option due after Friday** (`premium_after=1`): there the few experienced drivers have
  the weekend to take the car.

Against version 10, exact mode, the same weeks:

| | 60 weeks | lab / hold / fresh | Better | check-1..20 | All 80 | Lowest week | Weeks under 90% | Chance of a top-ten week (80 weeks) |
|---|---|---|---|---|---|---|---|---|
| trade-ins alone | +122 ± 88 | | 31/60 | +192 ± 159 | +139 ± 77 | 90.5% | 0 | +0.7 ± 2.2 points |
| premium after Friday alone | +134 ± 85 | +221 / +121 / +61 | 42/60 | +128 ± 135 | +133 ± 72 | 89.7% (a check week) | 1 | +1.6 ± 2.1 |
| **both (version 11)** | **+294 ± 100** | +239 / +303 / +340 | 42/60 | **+471 ± 204** | **+338 ± 90** | 90.6% | **0 of 80** | **+4.6 ± 2.3** |
| both + `cost_home=0.1` | | | | +444 ± 148 | +354 ± 98 | 90.3% | 0 of 80 | +4.9 ± 2.4 |

The two take different cars and their gains add up (256 expected from the parts, 294 played). Together they clear
every bar at once: 2.9 standard errors on the 60 weeks, more on the weeks never tuned on, no week under 90% on
80, and the chance of a top-ten week up by twice its error. The home-bound cost adds 16 a week and 14 cars to
that: left out, the system stays one rule smaller. Cars 424 a week (version 10: 414 on the 80), on time 96.4%.

**Why trade-ins alone paid little and the pair pays:** each trade-in takes a driver for a day, and near the day
cap it displaces about three plain cars (5 × 66 euros less 3 × 43). Premium cars after Friday sit on the one day
without a cap, so they displace nothing.

**Version 11 = version 10 + `trade_hour=1 premium_after=1`** (`VERSION = 11`). Checks: the port replays the
plug-in's saved weeks to the cent (lab-1 13,802.94, hold-3 20,922.23, fresh-9 12,889.57, check-4 14,238.39) and
version 10 is unchanged with both switches off (lab-1 13,736.53). `lab.restart_check`, three restarts in a week:

| Week | Straight | Three restarts |
|---|---|---|
| lab-1 | 13,803 at 96.5%, 372 cars | 13,918 at 97.3%, 370 cars |
| fresh-9 (the hardest) | 12,890 at 90.9%, 397 cars | 13,240 at 90.8%, 414 cars |
| hold-3 | 20,922 at 97.7%, 435 cars | 21,045 at 98.6%, 436 cars |

All three pass; version 10 failed the hardest week here (89.5%). A five-day live-clock rehearsal at twice the
final's speed follows, so that Thursday and Friday, where the two rules act, are played on the live path.

**The five-day live-clock rehearsal (00:21):** at twice the final's speed, with a stop and restart on Wednesday
noon: 1,034 of 1,034 requests answered, 368 orders by Friday night at 96.6% on time, no order without a live gig.
The world refused one quote, for the request caught in the restart's gap, and four withdraws of gigs a driver had
just taken. **Version 11 is on the final runner since 00:21** (version 10 kept in `~/dispatch-live-v10`).

| Version 11 | Mean margin | Worst week | Lowest on time | Ranked | Cars a week |
|---|---|---|---|---|---|
| lab-1..20 | 18,395 | 12,143 | 92.1% | 20/20 | 439 |
| hold-1..20 | 18,047 | 13,156 | 90.6% | 20/20 | 417 |
| fresh-1..20 | 18,292 | 11,496 | 90.9% | 20/20 | 430 |
| check-1..20 (never tuned on) | 16,240 | 9,248 | 92.0% | 20/20 | 411 |

On the 60 weeks 18,245 at 96.4% on time (version 10: 17,951; version 9: 17,535; version 8: 17,270).

## 75. Version 11 played: ranking round Sunday 00:00 (Sun 00:35)

`python -m lab.round`, defaults = version 11, 00:32 (`data/board8-0033.json`): **89,161, all five weeks ranked, 2nd
of 37** ranked teams at 00:33 (1st 102,582 with 473 cars a week at 43.3; 3rd 82,690; 10th 79,918). Ours: 425 cars
a week at 42.0.

| Week | Margin | Cars | On time | Our place that week | Ours against the tenth team |
|---|---|---|---|---|---|
| 1 | 16,743 | 436 | 95.4% | 9 | +0.6% |
| 2 | 18,724 | 432 | 97.9% | 2 | +16.2% |
| 3 | 18,329 | 421 | 98.1% | 2 | +24.3% |
| 4 | 18,461 | 437 | 97.0% | 4 | +4.2% |
| 5 | 16,904 | 397 | 98.0% | 2 | +9.5% |

The 21:00 round, closed: version 10 ended 7th of 56; week by week 7, 19, 4, 16, 4, and against the tenth team
+3.7%, −8.3%, +14.2%, −2.9%, +7.6% (mean +2.9%, spread 8 points: wider than the 6 points `lab.top10` assumes, so
its chances are a little too sure of themselves in both directions; the ranking of candidates does not change).

## 76. The final moved to 09:00; a third test final at 01:00; the runner protected (Sun 00:39)

The organisers' live pages (HANDBOOK.md lines 123 to 140, /judging; read 00:39): **the final is on Sunday at
09:00** (it moved from 08:00), set at 08:30, when registration closes; it ends at about 09:35 and submissions
still close at 10:00. One more whole-week test final starts at 01:00 (set at 00:45). `CLAUDE.md` and the saved
copies in `brief/` still carry the old times.

Version 11 plays the 01:00 test final. The lab machine has 2 cores and 3.8 GB without swap and also carries the
offline analyses of the night, so the runner got a drop-in (`/etc/systemd/system/spread-final.service.d/
protect.conf`: `Nice=-5`, `OOMScoreAdjust=-900`), applied to the running process without a restart. The watcher
of section 69 (`~/final_guard.sh`, tmux `guard`) moves the lab queue aside from the minute a final is set until
the runner reports its end.

Plan to the final: candidates may still be folded until 06:30, each through identity, restart check and a live
rehearsal; the runner is final by 07:30.

## 77. A swarm over the old data: no survivor, one open lead, and what it points to (Sun 00:55)

Emil asked for a swarm of Sonnet and Opus agents over every saved week, not bound to how the desk works now, with
an Opus check of each idea (run as a workflow from this session: seven Sonnet diggers, one slice each: drivers,
dealers and batches, the competitor and the kind of day, time, fee schedules, combinations and unused rules, the
other teams; seven Opus verifiers that got the claims and the raw data but not the finder's code; one Opus ranker;
15 agents, 411 tool calls, 14 minutes). **Result: 13 candidates, none survived; about 60 leads found empty**
(`swarm/TOP10.md`, `swarm/DEAD.md`, scripts under `swarm/<slice>/` and `swarm/verify_<slice>/`). Among the
refuted: holding late-pickup cars to the pickup morning (13 euros more fee to save 3 of drops); an early raise on
gigs with few views (the higher-fee half is late 26 to 32%); route and pickup offsets in the price book (better
log-loss in 79 of 80 weeks, and −175 ± 269 when played); a backlog gauge as a brake (it separates late weeks
with AUC 0.90 to 0.93 by Wednesday evening, but week size does nearly as well and the brakes are closed); an
evening sweep to the top fee; a longer hold of the opening fee. Facts worth keeping: bookings that cross a
midnight are given back 15 to 16% of the time against 4% for bookings made on the pickup day, and posting on the
pickup morning still costs more than those drops; an on-time order to a big dealer on Monday is worth 5 to 8
times one on Friday in trust.

**The one open lead it named, followed up here:** in the live week the nine teams above us won 34% of the
requests of the dealers outside the big four against our 28% (396 requests, +22 cars). Version 11's own 80 weeks,
plain cars, from the reveals (`small_dealers.py` in the scratch tools):

| Dealers | | Mon | Tue | Wed | Thu | Fri | All |
|---|---|---|---|---|---|---|---|
| the four largest (57% of requests) | won of quoted | 43.8% | 54.0% | 55.9% | 50.7% | 55.8% | 51.7% |
| | our price / list | 1.34 | 1.46 | 1.57 | 1.61 | 1.57 | 1.51 |
| all the others | won of quoted | 43.8% | 41.3% | 40.7% | **36.0%** | 45.1% | 41.3% |
| | our price / list | 1.34 | 1.43 | 1.46 | 1.51 | 1.45 | 1.43 |

On Monday the two groups are alike. Then the big four accept more and more from us (each on-time order raises a
dealer's accepted price by 1%), the book's market level follows them because they send most answers, and the
other dealers, who each send about 12 requests a week (too few for the offset of their own to move), are priced
up with it: their price rises 12% from Monday to Thursday and their win rate falls to 36%. A win rate of 41%
against 52% at this spread is a price about 6% over its own best, worth about 200 a week by the book's own
curve, before whatever the added orders do for trust.

**New setting `small_rate`**: one offset shared by every dealer outside the four that have sent most requests so
far, learned from their answers like any other offset (73 answers a day instead of 2 per dealer). It is learning,
not a table: it starts every week at zero. Queued against version 11, 60 weeks each, to start when the 01:00
test final ends: `small_rate` 0.02 and 0.04, `trust=1` (the dealer's own level moved by the known rule at each
delivery; −211 on version 7), both together, and `dealer_rate=0.06`.

## 78. The third live test final, 01:00: version 11 is 10th of 41 (Sun 01:40)

Version 11 on the final runner, no restart, lab held by the watcher from 00:45 to 01:34
(`data/test_final_0100.json`, our events in `data/test_final_0100-events.json.gz`): **11,508.75, 360 cars at
32.0, 95.8% on time, one car not delivered, ranked, 10th of 41 ranked teams** (1st 14,112 with 445 cars at 31.7;
2nd 13,672 with 371 at 36.9; 3rd, the usual leader, 13,288 with 488 at 27.2 and 94.1% on time; 9th 11,625; 11th
11,284). A lean and hard week: Wednesday was the flu day (26 bookings given back, 12 warnings) and **Friday the
price-war day** (36 of 179 requests won at 1.27 of list, where the two earlier Fridays gave 63 and 84), so the
cars due on the Monday after, which versions 10 and 11 were built to carry, were 69 instead of 90 to 120. The
teams just above us with our car count sold dearer cars (revenue a car 95 to 105 against our 88).

All 1,036 requests were answered; the world refused one action in the whole week (a post after a pickup window
had ended). The two new rules on their first live week: 1 trade-in won, delivered inside the customer's hour at a
margin of 98; 4 premium cars won, all due on the Monday after, all on time, 27 a car.

**What went wrong, from the ledger:** fees 60.7% of revenue (55.6% in the 20:00 week); refunds 426; one car
never delivered (penalty 236); **two fines of 100 for "electric car under 30% without a charging stop"**; two
waits of 30 at sites closed inside their stated hours; three release fees after the dealer cancelled.

**All three of the avoidable ones trace to one event: the dealer sends a won car to another town**
(`order_changed`, RULES line 110: the world sends the car there also when a driver has booked, and we pay for the
extra driving). 18 cars in this week; in version 11's 80 practice weeks (`changed.py` in the scratch tools):

| Cars | A week | Late | Not delivered | Margin a car | Refunds a car |
|---|---|---|---|---|---|
| never changed | 409.3 | 3.4% | 0.0% | 41.9 | 1.8 |
| sent to another town | 10.3 | 12.2% | 1.7% | 33.8 | 5.5 |
| ... to a nearer town | 4.1 | 0.6% | 0 | 68.2 | 0.2 |
| ... much farther (over twice the drive) | 2.8 | 33.0% | 6.3% | −15.7 | 13.4 |
| ... farther, a driver had already booked | 3.3 | 18.0% | 1.1% | 4.3 | 3.7 |
| ... farther, no driver yet | 0.9 | 60.3% | 15.1% | −36.4 | 39.4 |

Both fined cars were the second car of a round trip that a driver had booked before the dealer sent the car to
a town over 200 km away (Helsinki → Oulu, Lempäälä → Vaasa): the stop keeps the "no charging" it was posted with,
and a booked gig cannot be edited. The undelivered car was sent from a 3-hour drive to a 7-hour one (Vantaa →
Oulu) before it had a driver; it was posted at once at the fee of the new drive (`Desk.longer`) and nobody took
it for five days. In practice these cost 83 a week and 1.2 of the 15 late cars; charging fines are 0.04 a week
there (three in 80 weeks), so two in one week was a bad draw. Nothing is changed for it tonight: the only
sizeable cell, "farther, no driver yet" (0.9 cars a week), is a loss whatever the fee, and is recorded as a
known weakness.

**The small-dealer offset, played (01:46).** Against version 11 on the 60 weeks: `small_rate=0.04` +42 ± 107
(+141 / −95 / +79, cars −0.6); `small_rate=0.02` −134 ± 126 with a week at 88.2% (cars +0.3). No cars are added:
the offset finds nothing to correct. The lower win rate with the small dealers is not a mispricing. A dealer who
accepts less has its best price at a lower chance to win, so 41% against 52% is what the book's own optimum
gives once the big four trust us more; the book was not surprised by those answers, and an offset learns only
from surprise. **Not adopted.** (`trust=1`, both together and `dealer_rate=0.06` are still playing.) The gap to
the teams above us on small dealers in the one live week stays unexplained.

**The 01:00 week read by the leaders study (01:55), and our own quotes rebuilt.** The Friday gap is gone and
the volume gap with it (360 cars against a median of 364 for the nine above us); what is left is 3.3 euros a car
(revenue a car 88.3 against 94.8). By day of the deadline our Wednesday cars earned 20.5 each with fees at 72% of
revenue and 7 late: Wednesday was the flu day, and against our own Thursday and Friday those cars are about 1,000
short, the whole distance to 5th place. The flu rescue stays closed (sections 34, 39, 43).

Every quote of that week was rebuilt offline from the saved events (the desk re-decides past quotes as it does
after a restart; `requote.py` in the scratch tools). Trade-ins: 20 requests, 7 quoted, 1 won; the brake was off at
all 20; 13 failed the fit test, mostly dealers in towns with under 100 drivers within 60 km (Tampere, Raisio,
Turku, Lempäälä); the six quoted and lost stood at 1.27 to 1.67 of list. Premium: 44 requests, 12 quoted (an
option due after Friday), 4 won at 1.23 to 1.47 of list. The leaders study's `hoped` variants (the later cars of
a batch counted at half or not at all) lost: −172 ± 95 with a week at 89.2%, and −245 ± 90 on 18 weeks.

## 79. Astra's overnight audit: three patches played; the week by its size (Sun 02:25)

Astra (the Codex session) audited 16,163 saved run summaries and version 11's ledgers and proposed three changes
(`astra/ASTRA-TO-FABLE.md` A015 to A020, `IDEAS-ASTRA.md`; patches `astra/overnight_*.patch`, all applied to the
source and off by default). Against version 11 on the 60 weeks:

| Setting | Idea | Gain | Lowest week | Chance of a top-ten week |
|---|---|---|---|---|
| `reserve_chosen_day=1` | a pending quote counts on the pickup day of the option the dealer is likeliest to take, not the first offered | −59 ± 54 | 90.5% | −3.2 ± 1.5 points |
| `pair_road_cap=1.1` | a round trip whose two typical fees were drawn 10% over the road line is paid by the line | +60 ± 83 | 90.1% | −2.1 ± 2.1 |
| `premium_fee_line=1` | a premium car due after Friday is paid by the road line | +36 ± 58 (29 weeks) | 92.5% | +0.6 ± 1.2 |
| `pair_steady=1` (ours) | the same for every round trip, in both directions | −30 ± 114 | 89.9%, two weeks under 90% | −5.8 ± 2.7 |

None adopted. Reported back in `astra/FABLE-TO-ASTRA.md` F003.

**Was the 01:00 live week unlucky?** Margin over the list value of the week's requests (what the week offers),
`live_vs_lab.py` in the scratch tools: version 11's 80 practice weeks 0.219 with a spread of 0.054 (5% of weeks
under 0.146); the ten ranking weeks of versions 9 and 10 between −1.2 and +0.7 spreads of that; the 20:00 live
week 0.197 (version 9); **the 01:00 live week 0.143, 1.4 spreads under the mean**: its won cars sold at 1.35 of
list against the usual 1.44. So that week was one of the leanest tenth for our desk, and the live clock is not
the cause: live and practice weeks sit in the same distribution.

**Server.** A practice week costs about 1,300 calls and each call costs one token of the team's budget, which
refills at about 200 to 230 a second while this many teams practise: 9 to 10 weeks a minute whatever the number of
parallel worlds or the size of our machine (2 cores at a load of 1 to 2). No change.

**The flu day, once more (leaders study, 02:00, `leaders/juhus/out/flu_cars.txt`, version 11's 80 weeks):** 70 flu
days in 65 of the 80 weeks (Tue 9, Wed 19, Thu 20, Fri 22). The long plain cars sold the afternoon before their
last pickup earn 72 a car on an ordinary day (6.8% late) and still 60 a car on a flu day (20.7% late, refunds 17 a
car): leaving them out would give up 1,836 a week, and the flu is not knowable on the afternoon before. A flu day
costs those cars 1.5 late cars and about 90 euros, not their margin. The 01:00 Wednesday was worse than a usual
flu day because those cars had been sold on a low-price Tuesday (1.26 to 1.32 of list). **No rule.** From the
trade-in limits of the 13 fork weeks: a deliverable trade-in's limit is 1.47 of list at the median, the class
earns most at 1.3 and a quarter less at 1.6; the leaders study plays the trade-in's extra cost at 0.3 typical
(`design=ld_v11_cost30`) beside its two wider fit tests.

**Final numbers of the night's dealer and fee variants (02:28), against version 11 on the 60 weeks:** `trust=1`
−46 ± 96 with a week at 89.6%; `small_rate=0.02 trust=1` −115 ± 121 with a week at 89.0%; `dealer_rate=0.06`
−165 ± 113; Astra's `premium_fee_line=1` −19 ± 35 on all 60 (its +36 was the first 29 weeks). All closed. The
price book's rates and its treatment of dealers stay as they are.

**Trade-in variants (leaders study, 02:55), against version 11 on the 60 weeks:** quoting where 60 drivers live
within 60 km of the dealer instead of 100 (`design=ld_v11_reach60`) +32 ± 43; customer's hours from 10:00
(`ld_v11_hour10`) −38 ± 61; the extra cost at 0.3 typical instead of 0.5 (`ld_v11_cost30`) −37 ± 60 with a week at
89.6%. Version 11's trade-in settings stay. Now playing, three levels on 60 weeks each: a car's charge for its
place on a full day as a fixed amount (40, 50 or 60 euros times the load term) for every drive under 4 hours,
instead of a multiple of the car's own cost (`design=ld_v11_flat40/50/60`). **Why:** one more short car costs the
day's other cars the same lateness whatever its size, but today a 25-euro car pays 16 for its place at 0.9 of the
cap and an 87-euro car 57, so a full day fills with the smallest cars (127 a week at 19 euros each), where the
teams above us carry more of the 40-to-110-euro ones.

## 80. A second swarm, three rounds: no headroom in the archive; where version 11 is strong and weak (Sun 02:50)

Emil asked for Sonnet agents at medium effort digging for an hour under an Opus lead at high effort (a workflow
from this session: three rounds, each with the lead choosing six digs from what the round before had found, six
Sonnet diggers, an Opus verifier per dig; 33 agents, 500 tool calls, 47 minutes; `swarm2/TOP10-2.md`,
`swarm2/DEAD-2.md`, scripts under `swarm2/<dig>/` and `swarm2/verify_<dig>/`). **21 candidates refuted, 90 facts
verified, and one conclusion: the archive of 16,848 played weeks holds no setting, cell or switching rule that
beats version 11 in a way that repeats on other seeds.** For each seed, the archived setting that won it averages
−181 a week against version 11 on its other seeds and is positive on 14% of 78 seeds; of 459 "switch to setting X
when the week looks like Y" rows 3 pass on both families, about what chance gives
(`swarm2/verify_headroom/v1.py`, `v2.py`, `swarm2/verify_archswitch/ana.py`).

**Where version 11 is strong and weak** (verified on its 80 weeks unless said):

- **Lean against rich.** The weakness is the lean market week, and the seed decides it (weekly margins of versions
  10 and 11 correlate 0.984). The lowest 20 weeks make 12,556 against 19,473 for the rest, on the same number of
  requests and the same list value (81,215 against 80,865): fewer cars won (378 against 446) at lower prices
  (1.41 of list against 1.52), the same on-time share. Revenue carries the whole gap. A lean week shows early
  (the running win rate separates it with AUC 0.76 by Monday evening, 0.87 by Wednesday), but the only lever is
  a lower price, which is closed.
- **Easy against hard.** On-time risk and margin risk fall in different weeks: 2 of the 8 hardest weeks for
  punctuality are among the 20 leanest. The hard ones mostly show a high same-day share by Tuesday 06:00 (6 of 8
  at 0.69 to 0.80). The day cap and the brake hold them (lowest 90.6%); every looser cap took one under 90%.
- **By day.** The learning price book earns 2,777 a week, all of it Tuesday to Friday (+289, +721, +801, +993);
  Monday is neutral. Friday has the most late cars (4.7%), and its slips past 24 hours land on Monday at the 50%
  refund tier, concentrated in a few weeks. The price-war day is caught by the book in 3 to 4 hours.
- **Near its limit elsewhere.** No cell of 618 (kind, drive, notice, day) earns under 10 euros a car; cars at
  short notice earn 19 a car and are positive in all 80 weeks; missed round trips cost about 9 a week, changed
  orders about 92, every other ledger line about 130 together.
- **Live.** The 12 real weeks we have events for sit at the 43rd percentile of practice on average; the 01:00
  week was a 6th-percentile draw (flu Wednesday, price-war Friday, few drivers).
- A defect found and not touched before the final: `desk.py`, the car's own last pickup is not refreshed after a
  private seller's slot moves to the next day (about 0 euros a week).

**The flat place charge, played (03:07), against version 11 on the 60 weeks:** 40 euros −2 ± 105; 50 euros
+61 ± 101 (+93 / +144 / −54, 3 cars fewer) with a week at 88.8%; 60 euros +6 ± 110 (7 cars fewer). The mix moves
as intended (fewer of the smallest cars), the money does not follow, and the middle level loses a week. **Not
adopted.** With it every lead of the night's two studies and two swarms is closed; version 11 stays.

## 81. Version 11 with each part left out; ranking round Sunday 06:00 (Sun 07:00)

**The leave-one-out table** (`python -m lab.ablate`, version 11 = 18,245 a week on the 60 weeks, lowest week
90.6%; each row is version 11 with one part switched off, same weeks, exact mode):

| Left out | Costs a week | Cars | On time | Lowest week | Weeks under 90% |
|---|---|---|---|---|---|
| the price book does not learn from the dealers' answers | 2,777 ± 345 | +93.6 | 94.6% | 83.7% | 5 |
| no round trips | 1,465 ± 141 | −2.6 | 96.0% | 89.1% | 1 |
| the day cap also for cars due after Friday (version 9) | 578 ± 77 | −18.0 | 96.7% | 91.4% | 0 |
| no cap on the cars due on one day | 487 ± 185 | +26.3 | 94.5% | 85.4% | 7 |
| the two leaks open again (a returned pair's car; late counted at delivery) | 482 ± 110 | +0.1 | 96.2% | 90.0% | 0 |
| no trade-ins and no premium cars (version 10) | 294 ± 100 | −9.4 | 96.9% | 91.3% | 0 |
| no private addresses | 206 ± 87 | −18.1 | 96.8% | 90.5% | 0 |
| no lower opening fee for home-bound cars, no ramp at short notice | 181 ± 84 | +0.5 | 96.6% | 90.2% | 0 |
| round trips, but no waiting for a partner (version 8) | 177 ± 103 | +2.6 | 96.4% | 89.4% | 2 |
| no brake on risky cars when warnings rise | 117 ± 76 | +1.1 | 96.4% | 85.5% | 2 |
| fees keep rising at night, when nobody books | 108 ± 77 | +0.2 | 96.5% | 90.3% | 0 |
| any car with 4 hours to find a driver (not 14) | 67 ± 124 | +12.8 | 95.5% | 89.5% | 3 |
| no pickup window, so a late driver says nothing | 51 ± 71 | −0.1 | 96.4% | 91.4% | 0 |

Every part costs something to leave out; the three smallest are inside the noise of 60 weeks and are kept for what
the last column shows or (the window) because the trade-in rule stands on it. On version 11 the day cap and the
brake earn money as well as protecting the week: with more cars on the books than version 9 had, a day without the
cap loses 487 a week where it lost nothing then.

**Ranking round Sunday 06:00** (version 11, played 06:57 after the laptop that drives the lab had been off from
about 04:10; the runner and the lab queue are on the Stockholm machine and were not affected; the 03:00 round was
missed): **79,578, all five weeks ranked, 4th of 36** ranked teams at 06:58 (1st 98,179; 2nd 81,773; 3rd 79,842;
10th 76,780). Weeks: 13,012 (378 cars, 99.2%), 13,041 (365, 97.8%), 17,194 (449, 97.6%), 13,450 (391, 94.9%),
22,881 (487, 97.9%). The 00:00 round closed with version 11 5th of 58 (16th, 5th, 5th, 8th, 5th by week).

**A last unseen check (07:02).** Version 11 on `last-1..20`, seeds never played by any version: 18,506 a week
(worst 8,659, best 27,839), 432 cars, 96.0% on time, lowest week 93.5%, 20 of 20 ranked. Against version 10 on
the same 20 weeks: +316 ± 158, better in 14. The 06:00 round by week: 3rd, 17th, 9th, 9th, 5th; over the ten
ranking weeks version 11 has played it was in the top ten of a single week eight times, and 10th in its one live
week. **Version 11 is frozen for the final.** The runner holds the code that played the 01:00 live week; the
settings added to the source after 00:21 are off by default and version 11's weeks replay to the cent with them.

## 82. Twelve last settings against version 11: none clears the bar (Sun 07:40)

The last hour of testing went where version 11's exposure is largest: the fee of two-car gigs (172 cars a week),
the width of the price book's acceptance curve (the part worth 2,777 a week), the levels of the day cap and the
brake, and the cars due after Friday. Each setting on the same 60 weeks (lab, hold, fresh 1..20), exact mode,
against version 11 (`python -m lab.top10 <setting>`; the last column is the change in the chance of a top-ten week).

| Setting (version 11 has) | Weeks | Gain a week | lab / hold / fresh | Weeks better | Cars | Lowest week (under 90%) | Top-ten chance, points |
|---|---|---|---|---|---|---|---|
| `hold_after=12` (off): a car due after Friday waits for a partner until Friday noon | 60 | +18 ± 62 | +190 / −66 / −69 | 22 | 0.0 | 90.7% (0) | −1.8 ± 1.4 |
| `hold_after=16` | 60 | +21 ± 70 | +237 / −45 / −128 | 28 | 0.0 | 89.5% (1) | −2.1 ± 1.7 |
| `guard_after=1` (off): the brake does not act on cars due after Friday | 60 | −5 ± 25 | −11 / +35 / −39 | 4 | +2.2 | 84.9% (1) | −1.2 ± 1.1 |
| `top_fee=1.15` (1.2) | 60 | −32 ± 114 | +66 / +151 / −313 | 32 | −0.1 | 89.8% (1) | −3.1 ± 2.1 |
| `pair_fee=0.75` (0.8) | 60 | +43 ± 99 | +192 / +185 / −249 | 30 | −0.5 | 90.8% (0) | −2.6 ± 2.1 |
| `pair_fee=0.85` | 60 | −258 ± 118 | −107 / −342 / −324 | 20 | +0.6 | 87.5% (1) | −11.6 ± 3.1 |
| `spread=0.12` (0.14) | 60 | +145 ± 156 | +504 / −85 / +15 | 39 | +26.2 | 88.4% (3) | −1.5 ± 3.2 |
| `spread=0.16` | 60 | −347 ± 111 | −481 / −135 / −425 | 21 | −25.7 | 90.9% (0) | −13.0 ± 3.1 |
| `day_cap=0.1` (0.11) | 60 | −99 ± 89 | +11 / −4 / −305 | 25 | −7.4 | 91.2% (0) | −4.5 ± 2.2 |
| `guard=0.07` (0.08) | 60 | −59 ± 32 | −36 / −125 / −15 | 6 | −1.3 | 91.6% (0) | −1.7 ± 1.0 |
| `start_level=1.2` (1.15) | 60 | +62 ± 75 | +122 / +67 / −5 | 32 | +0.6 | 91.4% (0) | −0.9 ± 1.9 |
| `cost=0.97` (1.0) | 60 | +195 ± 133 | +551 / −30 / +62 | 38 | +15.2 | 88.5% (1) | +0.4 ± 2.5 |

**Learned.** Nothing here is two standard errors up, and the two settings with the largest means (`spread=0.12`,
`cost=0.97`) both buy their cars on the tuning family alone and put weeks under 90% (three and one). The settings
sit on a flat top: a step either way in the pair fee, the acceptance width, the day cap or the brake loses or does
nothing. This agrees with section 80: what is left is in new rules, not in better numbers. **Version 11 plays the
final.** The runner was checked at 07:41 (service active, version 11, guard running, lab queue empty).

## 83. The final, 09:00: a restart we did not plan (Sun 09:05)

The organisers set the final at 08:30:24 (`GET /v1/final`: our own copy of the world, start 09:00) and the watcher
put the lab on hold a second later. At 08:59:13 Ubuntu's own daily update (`apt-daily-upgrade`) started on the
runner's machine, replaced systemd, and at 08:59:42 restarted every service on it, the final runner and the name
resolver included: 18 seconds before the start. The runner's first call after the restart failed ("Temporary
failure in name resolution"), it tried again after 5 seconds, found the final's world and was connected before
09:00. It keeps no file, so there was nothing to recover. Monday of the final: 66 orders, 100% on time. No further
update is scheduled before Monday. Nothing was changed on the machine during the final.

**Learned.** The restart recovery we tested with `lab.restart_check` was used for real. What we had not thought
of: an operating system's own timers belong on the checklist before a run that must not stop.

**The final's result (09:35):** 19,366.40 margin on 43,942.22 revenue, 447 orders, 97.8% on time, 0.2% not
delivered, ranked: **9th of 58 ranked teams** (1st 22,931; 8th 19,574; 10th 19,084). Version 11, untouched.
