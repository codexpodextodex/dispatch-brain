"""Does the daily cap decide how many cars we carry? Version 7's 60 weeks: listed drivers, cars won, on-time share.

    python -m lab.cap_bound      (on the machine that holds the rosters)"""
import statistics as st

from lab.runs import ROSTERS, load, read_gz

rows = []
for fam in ("lab", "hold", "fresh"):
    for i in range(1, 21):
        run = load(8, f"{fam}-{i}", {})
        if not run:
            continue
        drivers = len(read_gz(ROSTERS / f"{run['worldId']}.json.gz"))
        s = run["score"]
        rows.append((drivers, s["wonOrders"], s["onTimeShare"], s["marginCents"] / 100, run["seed"], run["stats"].get("price_request", 0)))
rows.sort()
print(f"{len(rows)} weeks; listed drivers {rows[0][0]} to {rows[-1][0]}; correlation of cars won with listed drivers {st.correlation([r[0] for r in rows], [r[1] for r in rows]):.2f}, "
      f"of margin with drivers {st.correlation([r[0] for r in rows], [r[3] for r in rows]):.2f}, of on-time share with drivers {st.correlation([r[0] for r in rows], [r[2] for r in rows]):.2f}")
print(f"{'drivers':>8} {'weeks':>5} {'cars':>5} {'cars per driver':>15} {'cap of a week (0.11 x 5)':>24} {'on time':>8} {'lowest':>7} {'margin':>8} {'margin a car':>12}")
for lo, hi in ((0, 600), (600, 680), (680, 760), (760, 840), (840, 2000)):
    g = [r for r in rows if lo <= r[0] < hi]
    if g:
        print(f"{f'{lo}-{hi}':>8} {len(g):5} {st.mean(r[1] for r in g):5.0f} {st.mean(r[1] / r[0] for r in g):15.3f} {st.mean(0.55 * r[0] for r in g):24.0f} {st.mean(r[2] for r in g):8.1%} {min(r[2] for r in g):7.1%} "
              f"{st.mean(r[3] for r in g):8,.0f} {st.mean(r[3] / r[1] for r in g):12.1f}")
print("\nweeks at 97.5% on time or better with the fewest cars per driver (room that the cap leaves?), and the hardest weeks:")
for r in sorted((r for r in rows if r[2] >= 0.975), key=lambda r: r[1] / r[0])[:8]:
    print(f"  {r[4]:9} drivers {r[0]:4} cars {r[1]:4} ({r[1] / r[0]:.3f} a driver) on time {r[2]:.1%} margin {r[3]:8,.0f}")
for r in sorted(rows, key=lambda r: r[2])[:6]:
    print(f"  hard: {r[4]:9} drivers {r[0]:4} cars {r[1]:4} ({r[1] / r[0]:.3f} a driver) on time {r[2]:.1%} margin {r[3]:8,.0f}")
