"""The map and the clock: road minutes, opening hours, and the last minute to collect a car and still be on time."""
from __future__ import annotations

import math
from typing import Optional

HOUR, DAY = 60, 24 * 60
CHARGING_MINUTES, PLATES_MINUTES = 40, 30


class Geo:
    """Road km and minutes between every pair of places, from `client.map()`."""

    def __init__(self, world_map: dict):
        self.name = {p["id"]: p["name"] for p in world_map["places"]}
        self.at = {p["id"]: (p["lat"], p["lon"]) for p in world_map["places"]}
        self.minutes = {(r["from"], r["to"]): r["minutes"] for r in world_map["roads"]}
        self.km = {(r["from"], r["to"]): r["km"] for r in world_map["roads"]}

    def drive(self, leg: dict) -> int:
        """Planned minutes from a leg's pickup to its delivery, with the charging stop the rules require."""
        lane = (leg["pickup"]["placeId"], leg["delivery"]["placeId"])
        return self.minutes[lane] + (CHARGING_MINUTES if needs_charging(leg, self.km[lane]) else 0)


NOTIFY_KM = 30  # a driver's app notifies them of a new gig when its first pickup is within 30 km of their home


def straight_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    """The straight-line distance between two (lat, lon) points."""
    x = math.radians(b[1] - a[1]) * math.cos(math.radians((a[0] + b[0]) / 2))
    return 6371 * math.hypot(x, math.radians(b[0] - a[0]))


def neighbours(geo: "Geo", place: str, km: float = NOTIFY_KM) -> list[str]:
    """The places within `km` of a place in a straight line, itself included."""
    return [other for other in geo.at if straight_km(geo.at[place], geo.at[other]) <= km]


def needs_charging(leg: dict, km: float) -> bool:
    """Rule 3: an electric car below 30% charge on a route over 200 km needs a charging stop."""
    car = leg["car"]
    return bool(car["electric"]) and car["chargePercent"] is not None and car["chargePercent"] < 30 and km > 200


def open_span(stop: dict, day: int) -> Optional[tuple[int, int]]:
    """The first and last minute that a stop's site is open on a world day. A site that closes at 18:00 takes
    its last car at 17:59. A private address has no hours: its window says when someone is there."""
    hours = stop["hours"]
    if hours is None:
        return day * DAY, (day + 1) * DAY - 1
    weekday = day % 7
    if weekday in hours["weekdays"]:
        return day * DAY + hours["opens"], day * DAY + hours["closes"] - 1
    if weekday == 5 and hours.get("saturday"):
        return day * DAY + hours["saturday"]["opens"], day * DAY + hours["saturday"]["closes"] - 1
    return None


def last_pickup(leg: dict, deadline: int, drive: int) -> Optional[int]:
    """The last minute to collect a car so that it arrives by `deadline` while the delivery site is open.
    None when no pickup can be on time. The world reports the same number as `lastPickupAt` once we win."""
    pickup, delivery = leg["pickup"], leg["delivery"]
    first = pickup["window"]["from"]
    latest = min(pickup["window"]["to"], deadline - drive)
    for day in range(latest // DAY, first // DAY - 1, -1):
        span = open_span(pickup, day)
        if span is None:
            continue
        low, high = max(span[0], first), min(span[1], latest)
        if low > high:
            continue
        for arrival_day in range((high + drive) // DAY, (low + drive) // DAY - 1, -1):
            arrival = open_span(delivery, arrival_day)
            if arrival is None:
                continue
            fits_low, fits_high = max(low, arrival[0] - drive), min(high, arrival[1] - drive)
            if fits_low <= fits_high:
                return fits_high
    return None


def counted_at(delivery: dict, arrival: int) -> int:
    """When a delivery counts: on arrival at an open site, else when the site next opens (rule 4)."""
    for day in range(arrival // DAY, arrival // DAY + 8):
        span = open_span(delivery, day)
        if span is not None and arrival <= span[1]:
            return max(arrival, span[0])
    return arrival


def last_private_pickup(leg: dict, deadline: int, drive: int) -> Optional[int]:
    """The last minute of a private seller's slot at which the car can be collected and still count as delivered
    by the deadline. A car collected in an evening slot may reach a closed site: it counts when the site opens."""
    slot = leg["pickup"]["window"]
    for at in range(slot["to"], slot["from"] - 1, -15):
        if counted_at(leg["delivery"], at + drive) <= deadline:
            return at
    return None
