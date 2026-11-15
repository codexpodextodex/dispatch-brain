"""How likely a car is to come late, from what is known when we quote it.

A plain logistic model on a few yes/no facts, fitted on every saved car (lab/risk_fit.py writes risk.json next to
this file): the kind of car, the drive, the time to find a driver, the drivers near its ends, where in the week its
last pickup falls, and whether that day is a flu day."""
from __future__ import annotations

import json
import math
from pathlib import Path

DRIVE = (2, 4, 5, 7)  # hours: under 2, 2-4, 4-5, 5-7, 7 and more
FIND = (6, 14, 30, 54)  # hours from our answer to the last pickup
NEAR = (10, 50)  # drivers living within 30 km of the thinner end
PLAIN = 0.03  # a plain car comes late about this often: what a price already carries


def bucket(value: float, edges: tuple) -> int:
    return sum(value >= edge for edge in edges)


def kind_of(premium: bool, private_pickup: bool, private_delivery: bool) -> str:
    return "premium" if premium else "private pickup" if private_pickup else "private delivery" if private_delivery else "plain"


def facts(kind: str, drive: float, find: float, near: int, day: int, flu: bool) -> list[str]:
    """The yes/no facts of one car. `day` is the day of its last pickup, 0 the first Monday; hours for the rest."""
    part = "mon-wed" if day <= 2 else "thu-fri" if day <= 4 else "weekend" if day <= 6 else "last monday"
    out = [f"kind {kind}", f"drive {bucket(drive, DRIVE)}", f"find {bucket(find, FIND)}", f"near {bucket(near, NEAR)}", f"due {part}"]
    if flu:
        out += ["flu day", f"flu day drive {min(2, bucket(drive, DRIVE))}"]
    return out


def chance(model: dict, names: list[str]) -> float:
    return 1 / (1 + math.exp(-(model["base"] + sum(model["facts"].get(name, 0.0) for name in names))))


def load() -> dict:
    path = Path(__file__).with_name("risk.json")
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"base": math.log(PLAIN / (1 - PLAIN)), "facts": {}}
