"""How often does a car come late, from what is known when we quote it? Fits one small table from every saved car.

    python -m lab.risk_fit            # reads data/cars.json.gz (python -m lab.cars_dump), writes dispatch/risk.json
    python -m lab.risk_fit local      # the same from the 60 version-6 weeks on this machine, to try the fit

The model is a plain logistic regression on a few yes/no facts, so every number in it can be read:
the kind of car, the drive, the time to find a driver, how many drivers live near the ends, where in the week the
last pickup falls, and whether that day turned out to be a flu day (drivers gave back four or more of that day's
bookings just after midnight). Fitted on two seed families and checked on the third."""
from __future__ import annotations

import gzip
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

from dispatch.risk import DRIVE, FIND, NEAR, chance, facts, kind_of


def cells_of(weeks: list, fields: list) -> dict:
    f = {name: i for i, name in enumerate(fields)}
    cells = defaultdict(lambda: [0, 0])  # (family, facts) -> cars, late
    for week in weeks:
        if week["setting"].get("lab_step") and not any(week["setting"].get(k) for k in ("premium", "private_delivery", "private_pickup")):
            continue
        flu = set(day for day in week["flu"] if day <= 4)
        for c in week["cars"]:
            if c[f["cancelled"]] or c[f["legs"]] != 1:
                continue
            kind = kind_of(c[f["premium"]], c[f["private_pickup"]], c[f["private_delivery"]])
            if week["setting"].get("lab_step") and kind == "plain":
                continue  # of a fast-mode week only the kinds of car the exact weeks do not have
            day = c[f["last_pickup"]] // 1440
            key = (week["seed"].split("-")[0], tuple(facts(kind, c[f["drive"]], c[f["find_hours"]], min(c[f["near_pickup"]], c[f["near_delivery"]]), day, day in flu)))
            cells[key][0] += 1
            cells[key][1] += 1 - c[f["on_time"]]
    return cells


def fit(cells: dict, families: tuple, rounds: int = 3000, ridge: float = 2.0) -> dict:
    """Logistic regression by gradient descent on the cells of the given seed families."""
    rows = [(key[1], n, late) for key, (n, late) in cells.items() if key[0] in families]
    names = sorted({name for row in rows for name in row[0]})
    w = {name: 0.0 for name in names}
    total, late_all = sum(r[1] for r in rows), sum(r[2] for r in rows)
    w0 = math.log(late_all / (total - late_all))
    rate = 2.0
    for _ in range(rounds):
        g0, g = 0.0, defaultdict(float)
        for names_of, n, late in rows:
            p = 1 / (1 + math.exp(-(w0 + sum(w[name] for name in names_of))))
            d = n * p - late
            g0 += d
            for name in names_of:
                g[name] += d
        w0 -= rate * g0 / total
        for name in names:
            w[name] -= rate * (g[name] + ridge * w[name]) / total
    return {"base": w0, "facts": w}


def check(model: dict, cells: dict, families: tuple, label: str) -> None:
    rows = [(key[1], n, late) for key, (n, late) in cells.items() if key[0] in families]
    total, late = sum(r[1] for r in rows), sum(r[2] for r in rows)
    predicted = sum(n * chance(model, list(names)) for names, n, _ in rows)
    # how well it ranks: the late share in fifths of the cars sorted by predicted chance
    ordered = sorted(((chance(model, list(names)), n, l) for names, n, l in rows))
    fifths, acc, k = [], [0, 0, 0.0], 0
    for p, n, l in ordered:
        acc[0] += n
        acc[1] += l
        acc[2] += p * n
        if acc[0] >= total / 5 and k < 4:
            fifths.append(acc)
            acc, k = [0, 0, 0.0], k + 1
    fifths.append(acc)
    print(f"{label}: {total} cars, late {late / total:.2%}, predicted {predicted / total:.2%}; fifths by predicted chance, real (predicted): "
          + "  ".join(f"{a[1] / max(1, a[0]):.1%} ({a[2] / max(1, a[0]):.1%})" for a in fifths))


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "local":
        from lab.cars_dump import FIELDS, one
        from lab.runs import name_of
        weeks = [one(f"data/runs/{name_of(8, f'{fam}-{i}', {})}.json") for fam in ("lab", "hold", "fresh") for i in range(1, 21)]
        data = {"fields": FIELDS, "weeks": [w for w in weeks if w]}
    else:
        data = json.load(gzip.open("data/cars.json.gz", "rt", encoding="utf-8"))
    cells = cells_of(data["weeks"], data["fields"])
    print(f"{len(data['weeks'])} weeks, {sum(n for n, _ in cells.values())} cars in {len(cells)} cells")
    for held in ("lab", "hold", "fresh"):
        others = tuple(f for f in ("lab", "hold", "fresh") if f != held)
        check(fit(cells, others), cells, (held,), f"fitted without {held}, checked on {held}")
    model = fit(cells, ("lab", "hold", "fresh"))
    check(model, cells, ("lab", "hold", "fresh"), "all three")
    print("\nlog-odds: base", round(model["base"], 2))
    for name, value in sorted(model["facts"].items()):
        print(f"  {name:28} {value:+.2f}   x{math.exp(value):.2f}")
    Path("dispatch/risk.json").write_text(json.dumps({"drive": DRIVE, "find": FIND, "near": NEAR, **model}, indent=1), encoding="utf-8")
    flu_weeks = defaultdict(int)
    for week in data["weeks"]:
        if not week["setting"]:
            for day in week["flu"]:
                flu_weeks[day] += 1
    print("\nflu days by day of the week, version 6 weeks:", dict(sorted(flu_weeks.items())), "of", sum(1 for w in data["weeks"] if not w["setting"]), "weeks")


if __name__ == "__main__":
    main()
