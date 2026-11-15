# Designs not of version 6's shape

Side session, Sat 14 Nov. The question: can a desk built on a different idea beat version 6 (15,834 a week on
60 exact weeks, 369 cars at 42.9, 96.9% on time, lowest week 91.4%)? Each design is a module in `alt/`, played
with `design=<module>`; everything not named in a design is version 6. Comparisons use `alt/analysis/bar.py`
(the same seeds for both, version 6 as the base, the bar's eight hardest weeks listed).

The bar: exact mode on all 60 weeks, more than 15,834 a week, no week under 90% on time, and the eight hardest
weeks (fresh-9, fresh-12, hold-10, hold-17, hold-2, hold-9, fresh-20, lab-11) at least 93.5% on time on average.

How a design is judged: fast mode (`lab_step=12`) screens, but flatters anything that wins more cars; then the
main session's fixed 30-week exact panel (`--only fresh-9,fresh-12,hold-10,hold-17,hold-2,hold-9,fresh-20,lab-11,
lab-19,fresh-2,lab-18,lab-10,hold-14,hold-13,hold-12,fresh-5,lab-1,lab-3,lab-5,lab-7,hold-1,hold-3,hold-5,hold-7,
fresh-1,fresh-3,fresh-7,fresh-11,lab-13,hold-15`; version 6 there: 15,606 a week, the eight hardest 93.5%, lowest
91.4%); then all 60 exact weeks.

## What version 6's weeks say before any design (offline, `alt/analysis/`)

| Fact | Number | Script |
|---|---|---|
| Plain cars booked within 1 h of the win | 63% (median 0.3 h); 80% within 12 h | `pairing_window.py` |
| Round-trip partner: hours from the first car's win to the second's | median 4.9; 44% within 4 h; 63% within 8 h | `pairing_window.py` |
| ... first car already booked when its partner is won | 86% | `pairing_window.py` |
| Booked fee, in noise-free typical fees | median 0.85 (the opening fee); p75 1.0 to 1.1 where few drivers live at the delivery | `fee_levels.py` |
| Booked cars given back at least once | 14% | `fee_levels.py` |
| Correlation of a week's on-time share with Monday-Tuesday booked fee / slow bookings | -0.33 / -0.44 | (inline, on the cached rows) |

By option: same day 169 cars a week at 39.5 euros a car, next day 181 at 45.6, three days 19 at 51.6.

## Design C, on paper only: the volume desk (the leaders' corner) — dropped before playing

**Bet.** Win many more cars at a lower margin, but only cars that are almost certain to be on time; refuse the
kinds that come late.
**Why it fails on arithmetic.** In version 6's 60 weeks the kinds that make the late cars are long drives (over
5 hours, which are the same cars as a last pickup before 15:00), an end with under 10 drivers within 30 km, and
a last pickup before 13:00. Together they are 46% of the cars and 68% of the late ones, and they earn 52.7 euros
a car against 35.0 for the rest (hard weeks: 60.8 against 39.2). Refusing them gives up about 9,000 euros a week;
the safe cars would have to double in number at version 6's margin to replace it, and the extra safe cars come
at a lower price. The money of this game is in the risky cars; the late cars are what that money costs.
Version 6's shape (take them, at a price that covers their risk) is right for this. The milder form of the
leaders' corner, a lower cost on every car (`cost=0.9`), was measured by the main session: +446 ± 138 in fast
mode with the lowest hold week at 90.8%.

## Design A: hold a car back for a round-trip partner (`alt/pairhold.py`)

**Bet.** A round trip is driven for about 0.73 of two single fees and uses one driver for two cars. Version 6
loses most round trips because the first car is booked (median 18 minutes) before its partner is won (median
4.9 hours later). So a plain car with at least 16 hours to its last pickup is not posted at once: it waits up to
`hours` (never past 18:00 of the day it was won) for a partner among the cars we hold or the open gigs, and goes
out alone when the wait is over. Everything else is version 6.

**Fast mode, lab + hold, 40 weeks** (`python3 -X utf8 -m alt.analysis.bar design=pairhold_h4 lab_step=12`):

| Design | Gain a week | Better | Cars | Lowest week | Weeks <93% | Pairs posted a week |
|---|---|---|---|---|---|---|
| version 6 | | | 368 | 91.1% | 2 | 43 |
| `pairhold_h4` (wait up to 4 h) | +233 ± 120 | 21/40 | 364 | 92.4% | 2 | 82 (74 from held cars) |

Where the money comes from: driver fees -673 a week, refunds -63, revenue -467 (4 fewer cars). Cars that rode
in a pair were late 1.1% of the time against 4.6% for the cars that went alone (`alt/analysis/pair_late.py`): the
round trips are short hops around the busy towns. Pairs are booked a median 6 minutes after posting at 0.73 of
the two typical fees. Late causes (`lab.late_causes`): drops 124 -> 106, arrived late 117 -> 90; the "never
booked" count rises 52 -> 91, but that is the lab's per-car table crediting a pair's booking to its first car
only (`alt/analysis/never_booked.py` shows those gigs booked and done).

**Exact mode, the 30-week panel** (`python3 -X utf8 -m alt.analysis.bar design=pairhold_h4`):

| Family | Weeks | Version 6 | `pairhold_h4` | Gain | Better | Cars | Lowest |
|---|---|---|---|---|---|---|---|
| lab | 9 | 15,122 | 15,171 | +49 ± 229 | 4/9 | 368 > 365 | 94.7% > 94.6% |
| hold | 12 | 14,993 | 15,500 | +507 ± 243 | 9/12 | 358 > 355 | 91.7% > 91.4% |
| fresh | 9 | 16,909 | 17,135 | +227 ± 384 | 5/9 | 373 > 371 | 91.4% > 90.5% |
| all | 30 | 15,606 | 15,892 | **+285 ± 164** | 18/30 | 366 > 363 | 91.4% > 90.5% |

The eight hardest weeks: 93.5% on time > **92.8%** (fresh-12 93.7 > 90.7, fresh-9 91.4 > 90.5, hold-9 94.4 > 93.5;
hold-2 93.7 > 94.3). No week under 90%. **Misses the bar on the hard weeks.** Why, from the panel's cars:

| Car (pairhold_h4, 30 exact weeks) | Cars a week | Late |
|---|---|---|
| not held, alone, drive up to 3 h | 61.1 | 1.3% |
| not held, alone, drive over 3 h | 20.9 | 9.9% |
| held, then alone, drive up to 3 h | 71.4 | 3.1% |
| held, then alone, drive over 3 h | 60.4 | 10.5% |
| held, then in a pair, drive up to 3 h | 40.2 | 2.2% |
| held, then in a pair, drive over 3 h | 3.4 | 10.9% |

A long drive is held as often as a short one and almost never finds a partner (3.4 of 64 a week), while it loses
its first look; in fresh-12 the late long drives go from 20 to 33 and "booked late" from 12 to 23. So the next
variants hold only drives of at most 3 hours (`pairhold_s4`, `pairhold_s2`).

Holding only drives of at most 3 hours (exact, the same 30 weeks, against version 6):

| Design | Gain | Better | Cars | Eight hardest | Lowest | <90% | Gain on the 8 hardest / the other 22 |
|---|---|---|---|---|---|---|---|
| `pairhold_h4` (any car, 4 h) | +285 ± 164 | 18/30 | 363 | 92.8% | 90.5% | 0 | |
| `pairhold_s4` (drive <= 3 h, 4 h) | +271 ± 137 | 21/30 | 363 | 93.0% | 89.8% (fresh-9) | 1 | +540 ± 375 / +173 ± 129 |
| `pairhold_s2` (drive <= 3 h, 2 h) | +249 ± 205 | 20/30 | 364 | **93.5%** | 91.0% | 0 | +362 ± 557 / +209 ± 203 |

`pairhold_s2` meets the panel's bar (eight hardest equal to version 6, none under 90%). One week moves the same
way in all three: fresh-12, 93.7% > about 91%. Its extra late cars are not held cars: they are long drives
posted at once and booked late (Wednesday's: 10 > 16). Either noise of one week, or the round trips draw the
drivers who would have taken the long single drives in a thin week.

Ceiling (`alt/analysis/pair_ceiling.py`, version 6's won cars, greedy disjoint matching, ignoring when cars are
won): 123 round trips a week at 60/90 minutes, 149 at 90/120, 163 at 120/180. Holding 4 hours reaches 82.

Dropped on reasoning: re-matching open single cars into pairs once an hour. A car is posted at its win, so two
cars are open together only if the first was open when the second was won, and version 6 already pairs them
then; the time test only gets tighter later.

## Design B: one fee per gig, no raise before the warning (`alt/flatfee.py`)

**Bet.** Drivers learn how far our fees rise and wait for it; a desk whose fees never rise teaches them to book
at first look. Every gig of the week must follow it.

| Design (fast, lab + hold, 40 weeks) | Gain a week | Better | Cars | Lowest week | Weeks <90% |
|---|---|---|---|---|---|
| `flat_90`: 0.90 to the warning | -988 ± 122 | 2/40 | 368 | 86.3% | 4 |
| `flat_90_120`: 0.90, one raise to 1.20 when drivers plan the day | +42 ± 135 | 20/40 | 371 | 90.6% | 0 |

**Verdict: no.** A car that does not pay a driver at 0.90 needs its raise before the deadline warning, and
without it the hard weeks fall under 90%. With one raise the result is version 6's within noise: the waiting
that raises teach is not where our money goes (version 6's median booking is already at its opening fee). The
per-kind variant (`flat_class`: 0.85, or 1.05 to towns with few drivers) was taken out of the queue to make
room for the bolder designs; on this evidence it is not worth its queue time.

## Bolder rules for which cars to win (`alt/bold.py`), asked for by Emil

Exact mode, the 30-week panel, against version 6 (`python3 -X utf8 -m alt.analysis.bar design=<name> [settings]`):

| Design | Bet | Gain a week | Better | Cars | Eight hardest | Lowest | <90% | Gain: 8 hardest / other 22 |
|---|---|---|---|---|---|---|---|---|
| `bold_front` | cost x 0.80, 0.85, 1.00, 1.15, 1.15 by the day a car is won: Monday's cars are rarely late | -393 ± 181 | 11/30 | 380 | 93.0% | 89.7% | 2 | -263 / -440 |
| `bold_volume`, `cost=0.85` | a volume desk: low cost, holding for pairs, a hard stop per day at 2.5 unbooked posted cars per 100 drivers | -1,239 ± 396 | 7/30 | 392 | 91.6% | 87.5% | 2 | -3,426 / -444 |
| `bold_vol_s4`, `cost=0.95 day_cap=0.12 easy_find_hours=6` | the main session's volume settings with holding (short drives) and the hard stop as brakes | -465 ± 271 | 13/30 | 375 | 93.4% | 89.2% | 1 | -1,226 / -188 |
| (reference) `cost=0.95 day_cap=0.12 easy_find_hours=6` alone | | +803 ± 174 | 26/30 | 409 | 92.5% | 89.4% | 2 | +695 / +843 |

**Verdicts.**
- *Front-loading the week: no.* Cheap Monday and Tuesday cars are cheap because the dealers' level is low then
  (EXPERIMENTS.md 3: the low Monday is a property of the week); 14 more cars a week at a worse price, and the hard
  weeks gain nothing, because the cars that make them hard are still won from Wednesday at the usual risk.
- *A hard stop per day as the brake: no.* It shuts whole days: against the same volume settings without it, it
  gives back 34 of the 43 extra cars and 1,268 euros a week, and still leaves fresh-9 at 89.2%. A brake on the
  count of unbooked cars reacts to the wrong thing: in a hard week the cars that come late are long drives that
  sit unbooked for hours by their nature, not a full day.
- *Cost 0.85: no*, even with holding and the stop: 26 more cars a week, -3,426 in the hard weeks.
- `bold_nosame` (never quote same day) and `bold_refuse` (decline drives over 3 h to towns with <10 drivers) were
  not played: queue room went to the holding variants, and the main session's finding that the gap to the field
  is the kinds of car we refused (EXPERIMENTS.md 43 to 44) argues against refusing more.

## Design A on version 7 (the base from Sat ~10:50: +984 over version 6, 406 cars, eight hardest 94.3%)

Version 7 takes private addresses, so the holding desk never holds a car with one (a booked slot does not wait).
Exact mode, the 30-week panel, against version 7 (`python3 -X utf8 -m alt.analysis.bar design=<name> [settings]`):

| Design | Gain a week | Better | Cars | Eight hardest | Lowest | <90% | Gain: 8 hardest / other 22 |
|---|---|---|---|---|---|---|---|
| version 7 | | | 401 | 94.3% | 91.6% | 0 | |
| `pairhold_s2` | -5 ± 226 | 16/30 | 395 | 93.4% | 90.2% | 0 | -380 ± 655 / +131 ± 202 |
| `pairhold_s4` | +221 ± 123 | 20/30 | 395 | 93.3% | 90.6% | 0 | -128 ± 234 / +349 ± 137 |
| `pairhold_s2`, `pair_bonus=0.15` | -3 ± 216 | 14/30 | 406 | 94.2% | 92.4% | 0 | +168 ± 507 / -66 ± 237 |
| `pairhold_s4c` (s4, holds only while v7's guard is calm) | +246 ± 134 | 20/30 | 395 | 93.5% | 89.8% (fresh-9) | 1 | +156 ± 310 / +279 ± 148 |

On version 7 holding keeps a gain only in ordinary weeks and costs about one point on time in the hard ones in
every variant. Pricing a request lower when it completes a round trip (`pair_bonus`, the handbook's advice) wins
5 more cars and nothing else.

Gating the hold on version 7's guard (`calm=1`) brings the margin on the eight hardest back to even (+156 ± 310),
but not their timeliness: 93.5% against 94.3%, and fresh-9 falls to 89.8%. The guard trips only after a week has
already gone wrong, and by then the held cars of the morning have lost their first-look drivers.

**Verdict on design A: tested and dropped.** On version 6 it met the panel bar (`pairhold_s2`); on version 7,
which already takes the ordinary weeks' volume, holding is a fee saving of about +300 a week in ordinary weeks
paid for with about one point on time in the hard ones, in every variant (wait 2 h or 4 h, long drives
excluded, guard-gated, with a round-trip discount). No variant clears the bar against version 7.

## Final verdict

No design that is not a variation of the base beats version 7 on the bar (exact mode, more margin, no week under
90%, eight hardest at least the base's):

- A, hold for a round-trip partner: beat version 6 (`pairhold_s2` +249 ± 205, hardest 93.5%, none under 90%), not
  version 7 (best `pairhold_s4c` +246 ± 134 with fresh-9 at 89.8% and hardest 93.5% < 94.3%). Dropped.
- B, flat fee: -988 (one fee 0.90) to +42 (0.90 then 1.20) in fast mode against version 6. Dropped.
- C, a volume desk refusing the risky kinds: dropped on arithmetic (the risky kinds carry 52.7 € a car).
- Bold rules for which cars to win (day-of-week cost, no same day, hard stop on unbooked cars): all lose against
  version 6 in exact mode (-393 to -1,239). Dropped.

To replay any line on the server (exact, 30-week panel, priority 0):

    python3 -X utf8 -m lab.sweep --only fresh-9,fresh-12,hold-10,hold-17,hold-2,hold-9,fresh-20,lab-11,lab-19,fresh-2,lab-18,lab-10,hold-14,hold-13,hold-12,fresh-5,lab-1,lab-3,lab-5,lab-7,hold-1,hold-3,hold-5,hold-7,fresh-1,fresh-3,fresh-7,fresh-11,lab-13,hold-15 --set design=pairhold_s4c --priority 0
    python3 -X utf8 -m alt.analysis.bar design=pairhold_s4c
