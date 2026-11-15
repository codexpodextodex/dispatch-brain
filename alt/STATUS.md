# alt/ status (side session "designs not of version 6's shape")

Sat 14 Nov, Helsinki time. Newest first.

- 13:30 **Done.** `pairhold_s4c` exact against version 7: +246 ± 134, 20/30 better, but fresh-9 89.8% and
  eight hardest 93.5% < 94.3% (margin there +156 ± 310, other 22 +279 ± 148). The holding line is dropped; no
  design clears the bar against version 7. Verdicts and replay commands in NOTES.md ("Final verdict").
- 12:40 Exact panel against version 7: `pairhold_s2` -5 ± 226 (cars 401 > 395, eight hardest 94.3% > 93.4%);
  `pairhold_s4` +221 ± 123, 20/30 better, none under 90%, lowest 90.6%, but eight hardest 94.3% > 93.3% (gain
  -128 ± 234 there, +349 ± 137 on the other 22); `pairhold_s2 pair_bonus=0.15` -3 ± 216 (406 cars, hardest 94.2%).
  None clears the bar. Last try running: `pairhold_s4c` (s4, but it holds only while version 7's guard finds
  the week going well, so hard weeks should play as version 7).
- 12:00 Version 7 is the base now (main session: +984 over version 6, 406 cars). The holding desk never holds
  a car with a private address (version 7 takes them). Queued on the exact panel against version 7:
  `pairhold_s2`, `pairhold_s4`, `pairhold_s2 pair_bonus=0.15` (a request that completes a round trip with a held
  car or an open gig is priced 0.15 typical fees cheaper).
- 11:45 Bold designs, exact panel vs version 6, all lose: `bold_front` -393 ± 181 (380 cars, two weeks <90%),
  `bold_volume` (cost 0.85) -1,239 ± 396, `bold_vol_s4` (main's volume settings + holding + hard stop) -465 ± 271
  against +803 for the same settings without my brakes: the hard stop per day gives back 34 of 43 extra cars.
- 11:30 Exact panel vs version 6: `pairhold_s4` +271 ± 137, eight hardest 93.0%, fresh-9 89.8% (one week under
  90%); **`pairhold_s2` +249 ± 205, eight hardest 93.5%, lowest 91.0%, none under 90%: meets the panel bar.**
  fresh-12 falls to ~91% in every holding variant (long single drives booked late). Waiting for the main
  session's version 7 fold before queueing anything new; then holding and the hard stop go on the v7 base.
- 11:15 **`pairhold_h4` exact, 30-week panel: +285 ± 164 a week, 18/30 better, cars 366 > 363; eight hardest
  93.5% > 92.8% (fresh-12 93.7 > 90.7), lowest 90.5%, none under 90%.** Misses the bar on the hard weeks. Cause:
  long drives are held and almost never pair (3.4 of 64 a week), and lose their first-look drivers. Queued exact
  panel: `pairhold_s4` / `pairhold_s2` (hold only drives up to 3 h, 4 h / 2 h). Removed from the queue to stay
  near 120 weeks: `pairhold_eve` (holds long drives for days), `bold_nosame`.
- 10:20 Emil asked (via the main session) for much bolder designs, judged on everything incl. failures. Built
  `alt/bold.py` (rules for which cars to win) and queued on the exact 30-week panel: `bold_front` (cost x
  0.80/0.85/1.00/1.15/1.15 by the day a car is won), `bold_nosame` (never quote same day), `bold_volume`
  (cost=0.85, holding for pairs, hard stop on a day at 2.5 unbooked posted cars per 100 drivers). Written, not
  queued: `bold_refuse` (decline drives over 3 h to towns with <10 drivers, for cost=0.85), `bold_front_x`
  (0.70 ... 1.30), `bold_front_hold`. Removed from the queue: `flat_class`, `pairhold_h8` (room for the panel).
- 09:55 First screen (fast, lab + hold, 40 weeks, gain over version 6):
  `pairhold_h4` +233 ± 120, lowest week 91.1% -> 92.4%, 82 pairs a week instead of 43 (74 from held cars),
  fees -673 a week; cars in pairs are 1.1% late against 4.6% alone. `flat_90` -988 ± 122, four weeks under 90%
  (cars that need more than 0.90 get it only at the warning). `flat_90_120` +42 ± 135, lowest 90.6%: neutral.
  Queued at priority 0 (main session's OK, at most ~120 weeks at a time): `pairhold_h8`, `pairhold_eve`
  (cars due in 2+ days wait to 17:00 the working day before), `flat_class`. Next: holding + `pair_bonus`
  (price a request lower when it completes a round trip with a held car: the handbook's advice).
- 09:35 Waiting for the first screen (the main session gave my 120 weeks the second slot of the queue).
  Dropped on paper: design C, the volume desk (the risky kinds carry the margin, see NOTES.md); an hourly
  re-matching of open single cars into pairs (it finds nothing version 6 does not already pair at the win);
  limiting risky cars to experienced drivers (they drop half as often, but make only a quarter of our bookings).
  Written for the next round: `flat_class` (one fee by kind of car: 0.85, or 1.05 to towns with few drivers).
- 09:10 Two designs built and queued in fast mode (lab + hold, 20 seeds each, priority 1, behind ~850 jobs):
  `pairhold_h4` (hold a car up to 4 h for a round-trip partner), `flat_90` (one fee 0.90 to the warning),
  `flat_90_120` (0.90, one raise to 1.20 when drivers plan the day). Variants `pairhold_h2/_h8`, `flat_100`,
  `flat_100_130` written, not queued yet.
- 08:40 Offline facts from version 6's 60 exact weeks (`alt/analysis/`):
  - 63% of plain cars are booked within 1 h of the win (median 0.3 h); 80% within 12 h.
  - Round-trip partners: the second car is won a median 4.9 h after the first; 44% within 4 h, 63% within 8 h;
    86% of the time the first car is already booked by then.
  - Booked fee, in noise-free typical fees: median 0.85 (the opening fee) everywhere, p75 1.0 to 1.1 where few
    drivers live near the delivery. 14% of booked cars are given back at least once.
  - An early-week sign of a hard week in fees or booking speed is weak (correlation with the week's on-time
    share -0.33 and -0.44), so no week-adaptive design is planned.
