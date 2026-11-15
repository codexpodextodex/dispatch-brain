"""One compact record for every car of every saved week of the current version (exact mode, plus the fast-mode
weeks that carry kinds of car the exact weeks lack), for fitting how often a car comes late.

    python -m lab.cars_dump        # writes data/cars.json.gz

A record: what was known when we quoted (kind of car, drive, time to find a driver, the day and hour of the last
pickup, drivers near both ends), what happened (booked when, given back how often, on time or how late), and the
week's flu days (the days on which four or more of that day's bookings were given back in the first hour)."""
from __future__ import annotations

import glob
import gzip
import json
from collections import Counter
from multiprocessing import Pool

from dispatch.policy import VERSION
from lab.orders import rows, snapshot_of
from lab.runs import DATA, EVENTS, read_gz

KINDS = ("premium", "private_delivery", "private_pickup")


def wanted(setting: dict) -> bool:
    if setting.get("version") != VERSION or setting.get("design"):
        return False
    return not setting.get("lab_step") or any(setting.get(kind) for kind in KINDS)


def flu_days(events: list, booked_for: dict) -> list[int]:
    """Days on which four or more bookings for that same day were given back between 00:00 and 01:00."""
    drops = Counter()
    for e in events:
        if e["kind"] == "gig_dropped" and e["at"] % 1440 < 60 and booked_for.get(e["gigId"]) == e["at"] // 1440:
            drops[e["at"] // 1440] += 1
    return sorted(day for day, n in drops.items() if n >= 4)


def one(path: str):
    try:
        run = json.load(open(path, encoding="utf-8"))
        setting = json.loads(run["setting"]) if run.get("setting", "starter") != "starter" else {}
        if not wanted(setting):
            return None
        rr = rows(run)
        events = read_gz(EVENTS / f"{run['worldId']}.json.gz")
    except Exception as error:  # a week without its details
        return None
    won = {e["order"]["id"]: e for e in events if e["kind"] == "order_won"}
    last_day = {oid: e["order"]["lastPickupAt"] // 1440 for oid, e in won.items()}
    # the day a gig's first car must be collected
    gig_day = {gig["id"]: last_day.get(gig["stops"][0]["orderId"]) for gig in snapshot_of(run["worldId"])["gigs"]}
    out = []
    for r in rr:
        e = won[r["order"]]
        out.append([
            r["order"], int(r["premium"]), int(bool(e["order"]["legs"][0]["pickup"]["privateAddress"])), int(bool(e["order"]["legs"][0]["delivery"]["privateAddress"])),
            r["legs"], round(r["drive"] / 60, 2), round(r["find_hours"], 1), e["at"], e["order"]["lastPickupAt"], r["option"], r["near_pickup"], r["near_delivery"],
            int(r["paired"]), int(r["cancelled"]), int(r["on_time"]), r["late_hours"] if r["late_hours"] is None else round(r["late_hours"], 1), int(r["undelivered"]),
            None if r["book_wait"] is None else round(r["book_wait"], 1), r["bookings"], r["drops"], int(r["warned"]), len(r["failed"]),
            r["price"], r["fees"], r["refunds"], r["margin"], r["typical"],
        ])
    return {"seed": run["seed"], "setting": {k: v for k, v in setting.items() if k != "version"}, "score": run["score"], "flu": flu_days(events, gig_day), "cars": out}


FIELDS = ["order", "premium", "private_pickup", "private_delivery", "legs", "drive", "find_hours", "won_at", "last_pickup", "option", "near_pickup", "near_delivery",
          "paired", "cancelled", "on_time", "late_hours", "undelivered", "book_wait", "bookings", "drops", "warned", "failed", "price", "fees", "refunds", "margin", "typical"]

if __name__ == "__main__":
    paths = sorted(glob.glob(str(DATA / "runs" / "L8-*.json")))
    with Pool(2) as pool:
        weeks = [w for w in pool.imap_unordered(one, paths, chunksize=20) if w]
    with gzip.open(DATA / "cars.json.gz", "wt", encoding="utf-8") as file:
        json.dump({"fields": FIELDS, "weeks": weeks}, file)
    print(f"{len(weeks)} weeks, {sum(len(w['cars']) for w in weeks)} cars")
