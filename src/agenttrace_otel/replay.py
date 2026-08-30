from __future__ import annotations

import json
from pathlib import Path

from .core import TraceEvent, Trajectory


FORMAT = "agenttrace-trajectory/v1"


def trajectory_to_replay(trajectory: Trajectory) -> dict:
    return {
        "format": FORMAT,
        "run": trajectory.to_dict(),
    }


def trajectory_from_replay(payload: dict) -> Trajectory:
    if payload.get("format") != FORMAT:
        raise ValueError("unsupported AgentTrace replay format")
    run = payload.get("run")
    if not isinstance(run, dict) or not run.get("run_id"):
        raise ValueError("replay payload requires run.run_id")
    events = []
    for item in run.get("events", []):
        if not isinstance(item, dict):
            raise ValueError("replay event must be an object")
        events.append(
            TraceEvent(
                name=str(item.get("name", "")),
                kind=str(item.get("kind", "")),
                status=str(item.get("status", "ok")),
                duration_ms=float(item.get("duration_ms", 0.0) or 0.0),
                attributes=dict(item.get("attributes") or {}),
            )
        )
    return Trajectory(
        run_id=str(run["run_id"]),
        events=events,
        attributes=dict(run.get("attributes") or {}),
    )


def save_replay(path: str | Path, trajectory: Trajectory) -> None:
    Path(path).write_text(
        json.dumps(trajectory_to_replay(trajectory), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_replay(path: str | Path) -> Trajectory:
    return trajectory_from_replay(json.loads(Path(path).read_text(encoding="utf-8")))
