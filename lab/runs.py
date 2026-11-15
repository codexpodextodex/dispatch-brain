"""One practice week, played and saved. A run is named by its level, its seed and its setting: the policy
values that differ from the defaults, and the version of the decisions. A practice world is deterministic, so a
run that is saved is never played again.

For every run we keep three files under data/:
    runs/<name>.json        the score, the account by kind, and counts for the tables
    reveals/<world>.json.gz the reveal: every request with our quote and the answer, the truth of each won
                            car, and every view of our gigs with the fee the driver saw
    events/<world>.json.gz  every event of the week except the views
    snapshots/<world>.json.gz  the orders and gigs as they stood at the end of the week
    rosters/<world>.json.gz    the driver list: home town, rating, licence
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import sys
import time
from dataclasses import asdict, fields, replace
from pathlib import Path

from dispatch.env import ROOT, load_env
from dispatch.play import new_desk, play_practice
from dispatch.policy import VERSION, Params
from spread import starter as kit
from spread.client import Client, SpreadError, Unreachable

DATA = ROOT / "data"
RUNS, REVEALS, EVENTS, SNAPSHOTS, ROSTERS = DATA / "runs", DATA / "reveals", DATA / "events", DATA / "snapshots", DATA / "rosters"
KINDS = {f.name: type(f.default) for f in fields(Params)}


def params_from(changed: dict) -> Params:
    return replace(Params(), **{k: KINDS[k](v) for k, v in changed.items()})


def setting_of(changed: dict | None) -> str:
    """`changed` None is the kit's starter."""
    if changed is None:
        return "starter"
    defaults = asdict(Params())
    return json.dumps({"version": VERSION, **{k: v for k, v in sorted(changed.items()) if KINDS[k](v) != defaults[k]}}, sort_keys=True)


def name_of(level: int, seed: str, changed: dict | None) -> str:
    return f"L{level}-{seed}-{hashlib.sha1(setting_of(changed).encode()).hexdigest()[:10]}"


def load(level: int, seed: str, changed: dict | None) -> dict | None:
    path = RUNS / f"{name_of(level, seed, changed)}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def write_gz(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as file:
        json.dump(value, file, separators=(",", ":"))


def read_gz(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as file:
        return json.load(file)


def own(world) -> Path:
    """Marks a practice world as ours by hand, so the worker does not free it as a leftover. Delete the file after."""
    marker = DATA / "queue" / "running" / f"byhand-{world.id}.json"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps({"worldId": world.id}), encoding="utf-8")
    return marker


def create(client: Client, level: int, seed: str):
    """A new practice world. When the team's eight slots are full, waits for one: another week is about to end."""
    for _ in range(60):
        try:
            return client.create(level=level, seed=seed)
        except SpreadError as error:
            if error.status != 409:
                raise
            time.sleep(10)
    return client.create(level=level, seed=seed)


def run(level: int, seed: str, changed: dict | None, note_world=None) -> dict:
    """Plays one week and saves it. When the server restarts, plays the week again from its start."""
    saved = load(level, seed, changed)
    if saved:
        return saved
    marker = None
    if note_world is None:  # played by hand, not by the worker: say so, or the worker takes the world for an orphan
        marker = DATA / "queue" / "running" / f"byhand-{os.getpid()}-{name_of(level, seed, changed)}.json"
        marker.parent.mkdir(parents=True, exist_ok=True)

        def note_world(world_id: str) -> None:
            marker.write_text(json.dumps({"level": level, "seed": seed, "params": changed, "worldId": world_id}), encoding="utf-8")
    for attempt in range(8):
        client, started, world = Client(), time.time(), None
        try:
            world = create(client, level, seed)
            if note_world:
                note_world(world.id)
            now = world.snapshot()["now"]
            desk = kit.Desk(world, level, now) if changed is None else new_desk(client, world, level, now, params_from(changed))
            events: list = []
            score = play_practice(world, desk, record=events)
            reveal = world.reveal()
            snapshot = world.snapshot()
            roster = world.roster()
            break
        except BaseException as error:
            if world is not None:
                try:
                    world.delete()  # a world left behind holds one of the eight practice slots
                except SpreadError:
                    pass
            if not isinstance(error, Unreachable) or attempt == 7:
                raise
            time.sleep(30)
    bucket = client._buckets.get("practice")
    result = {
        "level": level, "seed": seed, "worldId": world.id, "setting": setting_of(changed), "seconds": round(time.time() - started), "score": score,
        "stats": dict(getattr(desk, "stats", {})), "ledger": dict(getattr(desk, "ledger", {})), "refused": dict(getattr(desk, "refused", {})),
        "requests": len(reveal["requests"]), "rateLimit": bucket.per_second if bucket else None,
    }
    write_gz(REVEALS / f"{world.id}.json.gz", reveal)
    write_gz(EVENTS / f"{world.id}.json.gz", events)
    write_gz(SNAPSHOTS / f"{world.id}.json.gz", {"orders": snapshot["orders"], "gigs": snapshot["gigs"]})
    write_gz(ROSTERS / f"{world.id}.json.gz", roster)
    RUNS.mkdir(parents=True, exist_ok=True)
    (RUNS / f"{name_of(level, seed, changed)}.json").write_text(json.dumps(result), encoding="utf-8")
    if marker is not None:
        marker.unlink(missing_ok=True)
    return result


if __name__ == "__main__":  # python -m lab.runs <job file>: the worker starts one of these for each week
    load_env()
    job_path = Path(sys.argv[1])
    job = json.loads(job_path.read_text(encoding="utf-8"))

    def note_world(world_id: str) -> None:  # so the worker can free the slot if this process dies
        job_path.write_text(json.dumps({**job, "worldId": world_id}), encoding="utf-8")

    done = run(job["level"], job["seed"], job["params"], note_world)
    print(f"{job['seed']} L{job['level']} {done['setting']} margin {done['score']['marginCents'] / 100:,.0f} on time {done['score']['onTimeShare']:.1%} {done['seconds']}s rate {done.get('rateLimit')}")
