"""In-memory beat job store (one active job per world)."""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any, Literal

JobStatus = Literal["queued", "running", "done", "error"]

_RETENTION_SEC = 30 * 60
_DEFAULT_WORLD = "__legacy__"


def world_job_slot(world_id: str | None) -> str:
    return world_id or _DEFAULT_WORLD


# Legacy alias
player_job_slot = world_job_slot


@dataclass
class BeatJob:
    job_id: str
    status: JobStatus
    created_at: float
    updated_at: float
    world_id: str = _DEFAULT_WORLD
    phase: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None

    @property
    def player_id(self) -> str:
        return self.world_id

    @player_id.setter
    def player_id(self, value: str) -> None:
        self.world_id = value


class BeatJobStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, BeatJob] = {}

    @staticmethod
    def _slot(world_id: str | None) -> str:
        return world_job_slot(world_id)

    def _prune_old(self) -> None:
        now = time.time()
        stale = [
            jid
            for jid, job in self._jobs.items()
            if job.status in ("done", "error") and now - job.updated_at > _RETENTION_SEC
        ]
        for jid in stale:
            del self._jobs[jid]

    def has_active(self, world_id: str | None = None) -> bool:
        slot = self._slot(world_id)
        with self._lock:
            return any(
                j.world_id == slot and j.status in ("queued", "running")
                for j in self._jobs.values()
            )

    def get(self, job_id: str) -> BeatJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def create(self, world_id: str | None = None) -> BeatJob | None:
        slot = self._slot(world_id)
        with self._lock:
            self._prune_old()
            if any(
                j.world_id == slot and j.status in ("queued", "running")
                for j in self._jobs.values()
            ):
                return None
            now = time.time()
            job = BeatJob(
                job_id=str(uuid.uuid4()),
                status="queued",
                created_at=now,
                updated_at=now,
                world_id=slot,
            )
            self._jobs[job.job_id] = job
            return job

    def set_running(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = "running"
                job.updated_at = time.time()

    def set_phase(self, job_id: str, phase: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.phase = phase
                job.updated_at = time.time()

    def finish(self, job_id: str, result: dict[str, Any] | None, error: str | None = None) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.updated_at = time.time()
            if error:
                job.status = "error"
                job.error = error
                job.result = result
            elif result and int(result.get("exit_code", 0)) != 0:
                job.status = "error"
                job.error = str(result.get("error") or "beat failed")
                job.result = result
            else:
                job.status = "done"
                job.result = result
                job.error = None
