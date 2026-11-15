"""The always-on queue: keeps 7 practice weeks running for as long as data/queue/ holds jobs.

    python -m lab.worker          # runs until the file data/queue/STOP appears

Each job is one week, played by its own process (python -m lab.runs), so a job always runs the code as it is
on disk at that moment. lab/sweep.py writes the jobs. A team holds at most 8 practice worlds that have not
ended; the worker uses 7 and leaves one spare."""
from __future__ import annotations

import json
import subprocess
import sys
import time

from dispatch.env import ROOT, load_env
from spread.client import Client, SpreadError

QUEUE = ROOT / "data" / "queue"
RUNNING, FAILED, LOGS = QUEUE / "running", QUEUE / "failed", QUEUE / "logs"
SLOTS = 7
TIME_LIMIT = 20 * 60  # seconds for one week before the worker gives it up


def log(line: str) -> None:
    with open(ROOT / "data" / "worker.log", "a", encoding="utf-8") as file:
        file.write(f"{time.strftime('%a %H:%M:%S')} {line}\n")


def free(world_id: str | None) -> None:
    if world_id:
        try:
            Client().world(world_id).delete()
        except SpreadError:
            pass


def reclaim() -> None:
    """Deletes practice worlds that no running job owns: a job that died may have left one, and a world that
    has not ended holds one of the team's eight slots. Never a ranking run: a deleted ranking run still counts."""
    owned = {json.loads(path.read_text(encoding="utf-8")).get("worldId") for path in RUNNING.glob("*.json")}
    try:
        for world in Client().worlds():
            if world["kind"] == "practice" and not world["ended"] and world["boardRun"] is None and world["worldId"] not in owned:
                free(world["worldId"])
                log(f"reclaimed {world['worldId']}")
    except SpreadError as error:
        log(f"reclaim: {error}")


def main() -> None:
    load_env()
    for folder in (QUEUE, RUNNING, FAILED, LOGS):
        folder.mkdir(parents=True, exist_ok=True)
    for stale in RUNNING.glob("*.json"):  # jobs of a worker that was stopped: free their worlds and queue them again
        free(json.loads(stale.read_text(encoding="utf-8")).get("worldId"))
        stale.rename(QUEUE / stale.name)
    live: dict = {}  # job path -> (process, start time)
    reclaim()
    checked = time.time()
    log(f"worker started, {len(list(QUEUE.glob('*.json')))} jobs waiting")
    while True:
        if time.time() - checked > 120:  # also covers the seconds between a job's create and its note of the world
            if len(live) < SLOTS or (FAILED.exists() and any(FAILED.iterdir())):
                reclaim()
            checked = time.time()
        for path, (process, started) in list(live.items()):
            code = process.poll()
            if code is None and time.time() - started < TIME_LIMIT:
                continue
            if code is None:
                process.kill()
            process.wait()
            out = (LOGS / f"{path.stem}.log").read_text(encoding="utf-8", errors="replace").strip()
            if code == 0:
                log(out.splitlines()[-1] if out else f"done {path.name}")
                path.unlink(missing_ok=True)
                (LOGS / f"{path.stem}.log").unlink(missing_ok=True)
            else:
                log(f"FAILED {path.name}: {out[-600:]}")
                free(json.loads(path.read_text(encoding="utf-8")).get("worldId"))
                path.rename(FAILED / path.name)
            del live[path]
        stop = (QUEUE / "STOP").exists()
        if stop and not live:
            log("worker stopped")
            return
        waiting = sorted(QUEUE.glob("*.json")) if not stop else []
        slots_file = QUEUE / "SLOTS"  # a number in this file lowers the worker's share of the practice worlds for a while
        slots = int(slots_file.read_text().strip() or SLOTS) if slots_file.exists() else SLOTS
        while waiting and len(live) < slots:
            job = waiting.pop(0)
            path = RUNNING / job.name
            job.rename(path)
            with open(LOGS / f"{path.stem}.log", "w", encoding="utf-8") as out:  # a file, so a long error cannot block the job
                process = subprocess.Popen([sys.executable, "-X", "utf8", "-m", "lab.runs", str(path)], cwd=ROOT, stdout=out, stderr=subprocess.STDOUT)
            live[path] = (process, time.time())
        time.sleep(1)


if __name__ == "__main__":
    main()
