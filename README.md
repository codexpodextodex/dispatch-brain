# Dispatch Brain

Team Moonshot's desk for **Spread**, Bahn Express's challenge at Junction 2026: run a car transport company
for one simulated week in Finland. A dealer asks for a price; if we win the car, we post the drive as a gig
and a freelance driver takes it, or not. The score is gross margin, and at least 90% of the cars must arrive
on time.

## The idea

**Price every car at its best expected margin, and let the week teach us both sides of that margin.**

    expected margin = chance the dealer says yes at this price × (price − what the car will cost us)

- **The chance** comes from one number we learn from our own quotes: the price level a dealer accepts. It is a
  market level times an offset for the dealer and for the town the car goes to. Every
  yes or no moves these numbers a little ([`dispatch/pricing.py`](dispatch/pricing.py)). This follows the day,
  each dealer's trust, a price war and an outage without knowing which of them is happening.
- **The cost** is the driver's fee and the risk of a late car. A car costs more with each hour of driving and
  on a day that is already full: drivers can move only so many cars a day, and the driver list, public from
  the first minute, says how many drivers the week has ([`dispatch/policy.py`](dispatch/policy.py)).

So, apart from a minimum time to find a driver, no rule says "take this car" or "leave it". A hard car gets a
high price, and we win it only from a dealer who pays that much.

### One request, step by step

1. **Request.** A dealer asks for a price on a car, with one or more delivery options.
2. **In time?** An option is quoted only if 14 hours remain to find a driver before its last possible pickup
   (4 for a short drive out of a town full of drivers). With no option left we decline. `Policy.quote`
3. **Cost.** One typical fee, plus 0.08 for each hour of driving over three, times
   `1 + (our cars due that day / (0.11 × listed drivers))⁴`. Cars due after Friday skip the last factor. `Policy.cost`
4. **Chance.** The price level this dealer accepts: market × dealer × delivery town, learned this week. `PriceBook.level`
5. **Quote.** The price where chance × (price − cost) is highest, tried in steps of 1% of the list price. `PriceBook.best_markup`
6. **Yes or no?** Either answer moves the three levels by how much it surprised us. `PriceBook.learn`
7. **Won.** The car is ours to deliver on time.
8. **Wait?** A car with time waits up to 4 hours, never past 18:00, for a second car that makes a round trip. `Desk.post`
9. **Gig.** Opens at 0.85 of the typical fee (0.75 where drivers live); a round trip is one gig at 0.8 of the two fees. `Policy.fees`
10. **Booked?** Until a driver books, the fee rises towards the deadline and stands still from 22:00 to 06:30. `Policy.schedule`
11. **Late?** A booked driver who reports late is released while another can still come.
12. **Delivered.** On time, the dealer accepts 1% more next time (the game's rule), and the answers teach us that too.

Around that one idea, the parts of version 11, each with what it is worth: the same 60 practice weeks with that one
part switched off (`python -m lab.ablate`; version 11 makes 18,245 a week and no week is under 90% on time).

| Part | What it does and why | Left out, a week | Weeks under 90% (of 60) |
|---|---|---|---|
| The price book learns | Starts every week from one guess (1.15 of list price) and moves with every yes or no. No table of old prices: one built from earlier weeks gained on those weeks and lost on unseen ones | −2,777 | 5 |
| Round trips | Two cars that make a round trip go as one gig at 0.8 of two fees: the driver has no empty way back | −1,465 | 1 |
| ... and waiting for the partner | A newly won car that has time waits up to 4 hours for a car won after it. Round trips booked: 57 → 86 a week | −177 | 2 |
| The day cap | A day that already holds many of our cars makes the next one dearer: drivers can move only so many cars a day | −487 | 7 |
| ... lifted after Friday | No new requests come after Friday, so nothing competes for the Monday after; those are our best cars | −578 | 0 |
| Fixes after the win | A pair that its driver gives back stays a pair; "late" is counted at the last pickup | −482 | 0 |
| Trade-ins and premium cars | A trade-in gets the customer's hour as its delivery window (on time 55% → 84%); a premium car is taken only when due after Friday | −294 | 0 |
| Private addresses | Taken when the drive is under two hours | −206 | 0 |
| Fees that follow the drivers | Open at 0.85 of the typical fee (0.75 where drivers live), stand still at night, rise to the deadline | −181, −108 | 0 |
| The brake | When late and warned cars pass 8% of the cars done, the kinds that come late are priced out | −117 | 2 |
| Notice | A car needs 14 hours to find its driver, 4 for a short drive out of a town full of drivers | −67 | 3 |
| The pickup window | A booked driver who will come too late says so, and is replaced while another can still come | −51 | 0 |
| Notes | A reader for the dealers' notes in Finnish, Swedish and English ([`dispatch/notes.py`](dispatch/notes.py)) | | |

What did not work is in [`EXPERIMENTS.md`](EXPERIMENTS.md) too, with its numbers: a fixed map of the competitor's
lane prices, paying drivers less, direct offers to drivers, winning volume with a lower price, a looser day cap,
long drives without their charge. What would break it: a week in which a dealer sends many won cars to far towns,
a bulk order out of one small town, and a very rich week, where other teams carry more cars than our day cap lets
us take.

Posting, retries after a failed visit and reposting an expired gig are the kit starter's own plumbing, which
[`dispatch/desk.py`](dispatch/desk.py) inherits; trade-ins are in [`dispatch/trade.py`](dispatch/trade.py).


## Results

**The final (Sunday 09:00): 9th of 58 ranked teams, €19,366 margin at 97.8% on time, 447 cars.** Best ranking
round: 2nd of 62 (Saturday 15:00).

Level 8 practice weeks, margin in game euros per week. `lab` seeds are the ones we tuned on; `hold` seeds were
never tuned on. Every number is in [`EXPERIMENTS.md`](EXPERIMENTS.md), with the ideas that did not work.

| System | Seeds | Mean margin | Worst week | Lowest on time | Ranked |
|---|---|---|---|---|---|
| Kit starter | lab-1..10 | −63,748 | −75,667 | 42.9% | 0/10 |
| Kit starter | hold-1..10 | −71,997 | −97,858 | 33.9% | 0/10 |
| Dispatch Brain, version 5 (played the Saturday 00:00 ranking round) | lab-1..20 | 12,778 | 7,442 | 93.8% | 20/20 |
| Dispatch Brain, version 5 | hold-1..20 | 12,225 | 7,054 | 93.6% | 20/20 |
| Dispatch Brain, version 6 | lab-1..20 | 16,070 | 8,941 | 94.7% | 20/20 |
| Dispatch Brain, version 6 | hold-1..20 | 15,265 | 10,512 | 91.7% | 20/20 |
| Dispatch Brain, version 6 | fresh-1..20 (used for nothing before) | 16,166 | 9,498 | 91.4% | 20/20 |
| Dispatch Brain, version 7 | lab-1..20 | 16,881 | 10,235 | 94.7% | 20/20 |
| Dispatch Brain, version 7 | hold-1..20 | 16,654 | 11,431 | 93.5% | 20/20 |
| Dispatch Brain, version 7 | fresh-1..20 | 16,917 | 9,732 | 91.6% | 20/20 |
| Dispatch Brain, version 8 | lab-1..20 | 17,516 | 10,415 | 96.1% | 20/20 |
| Dispatch Brain, version 8 | hold-1..20 | 16,795 | 11,834 | 93.4% | 20/20 |
| Dispatch Brain, version 8 | fresh-1..20 | 17,498 | 10,203 | 90.8% | 20/20 |
| Dispatch Brain, version 8 | check-1..20 (used for nothing before; version 7: 14,805) | 15,412 | 8,122 | 92.5% | 20/20 |
| Dispatch Brain, version 9 (a newly won car waits up to 4 hours for a round-trip partner) | lab-1..20 | 17,626 | 11,098 | 95.4% | 20/20 |
| Dispatch Brain, version 9 | hold-1..20 | 17,475 | 12,199 | 93.8% | 20/20 |
| Dispatch Brain, version 9 | fresh-1..20 | 17,503 | 10,283 | 91.8% | 20/20 |
| Dispatch Brain, version 9 | check-1..20 (never tuned on) | 15,513 | 8,631 | 91.1% | 20/20 |
| Dispatch Brain, version 10 (no day cap for cars due after Friday) | lab-1..20 | 18,156 | 12,198 | 95.1% | 20/20 |
| Dispatch Brain, version 10 | hold-1..20 | 17,744 | 12,533 | 91.4% | 20/20 |
| Dispatch Brain, version 10 | fresh-1..20 | 17,952 | 10,529 | 91.3% | 20/20 |
| Dispatch Brain, version 10 | check-1..20 (never tuned on) | 15,769 | 8,615 | 91.2% | 20/20 |
| Dispatch Brain, version 11 (trade-ins by the customer's hour; premium cars due after Friday) | lab-1..20 | 18,395 | 12,143 | 92.1% | 20/20 |
| Dispatch Brain, version 11 | hold-1..20 | 18,047 | 13,156 | 90.6% | 20/20 |
| Dispatch Brain, version 11 | fresh-1..20 | 18,292 | 11,496 | 90.9% | 20/20 |
| Dispatch Brain, version 11 | check-1..20 (never tuned on) | 16,240 | 9,248 | 92.0% | 20/20 |

## Run it

Python 3.9 or later, no packages. Put the team key in `.env` (copy `.env.example`).

```sh
python -m dispatch --seed lab-1     # one level 8 practice week
python -m dispatch --final          # the final or a test final, from the live stream
```

If the desk stops during the final, start it again with the same command. It keeps no file: it reads the
week's events again, relearns every price level from them, and goes on.

## How we tested

```sh
python -m lab.worker                                # plays queued practice weeks, 7 at a time
python -m lab.sweep --both --grid day_cap=0.09,0.11 # the same 20 weeks for each setting
python -m lab.patterns --both --by last_pickup_hour # which cars make and lose money
python -m lab.notes_score                           # the note reader against the reveal
python -m lab.price_eval                            # the price book's predictions against the answers
python -m lab.ablate                                # version 11 with each part left out, on the same 60 weeks
python -m lab.top10 day_cap=0.12                    # a candidate by its chance of a top-ten week
python -m lab.restart_check                         # a week with three restarts
python -m lab.live_check                            # a rehearsal of the final on a ticking clock
```

A practice world is deterministic, so two settings played on the same seed differ only by their decisions.
A change was kept only if it raised the mean margin by two standard errors on the 60 weeks we tuned on, held on 20
weeks never tuned on (`check-1..20`), and took no week under 90% on time.

## Layout

```
dispatch/   the desk: policy.py (the two decisions), pricing.py, notes.py, geo.py, desk.py, play.py
lab/        the test bench: worker, sweep, patterns, notes_score, price_eval, restart_check, live_check
spread/     Bahn's kit, unchanged: the API client and the starter that desk.py inherits
```

MIT license. All code was written at Junction 2026.
