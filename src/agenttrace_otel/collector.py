from __future__ import annotations

import html
import json
import sqlite3
import time
from pathlib import Path
from typing import Iterable

from .core import TraceEvent, Trajectory, diff_trajectories
from .replay import FORMAT, trajectory_from_replay, trajectory_to_replay


class TrajectoryStore:
    """Small SQLite-backed store for local AgentTrace development and CI artifacts."""

    def __init__(self, path: str | Path = "agenttrace.db") -> None:
        self.path = str(path)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_schema(self) -> None:
        with self._connect() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS trajectories (
                    run_id TEXT PRIMARY KEY,
                    created_at REAL NOT NULL,
                    model TEXT NOT NULL DEFAULT '',
                    has_error INTEGER NOT NULL DEFAULT 0,
                    tools TEXT NOT NULL DEFAULT '',
                    payload TEXT NOT NULL
                )
                """
            )
            db.execute("CREATE INDEX IF NOT EXISTS trajectories_model_idx ON trajectories(model)")
            db.execute("CREATE INDEX IF NOT EXISTS trajectories_error_idx ON trajectories(has_error)")

    def put(self, trajectory: Trajectory) -> None:
        tools = sorted(
            {
                event.name
                for event in trajectory.events
                if event.kind in {"tool", "mcp", "function", "action"}
            }
        )
        model = str(trajectory.attributes.get("model", ""))
        if not model:
            for event in trajectory.events:
                value = event.attributes.get("model") or event.attributes.get("gen_ai.request.model")
                if value:
                    model = str(value)
                    break
        has_error = int(any(event.status == "error" for event in trajectory.events))
        payload = json.dumps(trajectory_to_replay(trajectory), separators=(",", ":"), ensure_ascii=False)
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO trajectories(run_id, created_at, model, has_error, tools, payload)
                VALUES(?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    created_at=excluded.created_at,
                    model=excluded.model,
                    has_error=excluded.has_error,
                    tools=excluded.tools,
                    payload=excluded.payload
                """,
                (trajectory.run_id, time.time(), model, has_error, "\n".join(tools), payload),
            )

    def get(self, run_id: str) -> Trajectory | None:
        with self._connect() as db:
            row = db.execute("SELECT payload FROM trajectories WHERE run_id = ?", (run_id,)).fetchone()
        if row is None:
            return None
        return trajectory_from_replay(json.loads(row["payload"]))

    def query(
        self,
        *,
        tool: str | None = None,
        model: str | None = None,
        error: bool | None = None,
        limit: int = 100,
    ) -> list[Trajectory]:
        clauses: list[str] = []
        params: list[object] = []
        if tool:
            clauses.append("tools LIKE ?")
            params.append(f"%{tool}%")
        if model:
            clauses.append("model LIKE ?")
            params.append(f"%{model}%")
        if error is not None:
            clauses.append("has_error = ?")
            params.append(int(error))
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        safe_limit = max(1, min(int(limit), 1000))
        with self._connect() as db:
            rows = db.execute(
                f"SELECT payload FROM trajectories{where} ORDER BY created_at DESC LIMIT ?",
                (*params, safe_limit),
            ).fetchall()
        return [trajectory_from_replay(json.loads(row["payload"])) for row in rows]

    def compare(self, left_run_id: str, right_run_id: str):
        left = self.get(left_run_id)
        right = self.get(right_run_id)
        if left is None or right is None:
            missing = left_run_id if left is None else right_run_id
            raise KeyError(f"trajectory not found: {missing}")
        return diff_trajectories(left, right)


def trajectory_from_payload(payload: dict) -> Trajectory:
    if payload.get("format") == FORMAT:
        return trajectory_from_replay(payload)
    run_id = str(payload.get("run_id", "")).strip()
    if not run_id:
        raise ValueError("trajectory run_id is required")
    raw_events = payload.get("events", [])
    if not isinstance(raw_events, list):
        raise ValueError("trajectory events must be a list")
    events: list[TraceEvent] = []
    for item in raw_events:
        if not isinstance(item, dict):
            raise ValueError("trajectory event must be an object")
        events.append(
            TraceEvent(
                name=str(item.get("name", "")),
                kind=str(item.get("kind", "step")),
                status=str(item.get("status", "ok")),
                duration_ms=float(item.get("duration_ms", 0.0)),
                attributes=dict(item.get("attributes", {})),
            )
        )
    return Trajectory(run_id=run_id, events=events, attributes=dict(payload.get("attributes", {})))


def render_timeline(trajectory: Trajectory) -> str:
    rows = []
    for index, event in enumerate(trajectory.events, 1):
        attrs = html.escape(json.dumps(event.attributes, ensure_ascii=False, sort_keys=True))
        rows.append(
            "<tr>"
            f"<td>{index}</td><td>{html.escape(event.kind)}</td><td>{html.escape(event.name)}</td>"
            f"<td>{html.escape(event.status)}</td><td>{event.duration_ms:.2f} ms</td><td><code>{attrs}</code></td>"
            "</tr>"
        )
    return f"""<!doctype html>
<html><head><meta charset='utf-8'><title>AgentTrace {html.escape(trajectory.run_id)}</title>
<style>body{{font-family:system-ui;margin:2rem;background:#0b1020;color:#e7edf7}}a{{color:#7dd3fc}}table{{width:100%;border-collapse:collapse}}td,th{{padding:.65rem;border-bottom:1px solid #27324a;text-align:left}}code{{white-space:pre-wrap;color:#c4b5fd}}</style></head>
<body><p><a href='/'>← runs</a></p><h1>{html.escape(trajectory.run_id)}</h1>
<p>{html.escape(json.dumps(trajectory.attributes, ensure_ascii=False, sort_keys=True))}</p>
<table><thead><tr><th>#</th><th>Kind</th><th>Step</th><th>Status</th><th>Duration</th><th>Attributes</th></tr></thead><tbody>{''.join(rows)}</tbody></table></body></html>"""


def render_index(trajectories: Iterable[Trajectory]) -> str:
    cards = []
    for trajectory in trajectories:
        errors = sum(event.status == "error" for event in trajectory.events)
        duration = sum(event.duration_ms for event in trajectory.events)
        path = " → ".join(html.escape(f"{event.kind}:{event.name}") for event in trajectory.events[:8])
        cards.append(
            f"<article><h3><a href='/runs/{html.escape(trajectory.run_id)}'>{html.escape(trajectory.run_id)}</a></h3>"
            f"<p>{len(trajectory.events)} events · {duration:.2f} ms · {errors} errors</p><code>{path}</code></article>"
        )
    return f"""<!doctype html><html><head><meta charset='utf-8'><title>AgentTrace Collector</title>
<style>body{{font-family:system-ui;margin:2rem;background:#0b1020;color:#e7edf7;max-width:1100px}}a{{color:#7dd3fc}}article{{padding:1rem;margin:.8rem 0;border:1px solid #27324a;border-radius:12px;background:#11182b}}code{{color:#c4b5fd}}</style></head>
<body><h1>AgentTrace Collector</h1><p>Local trajectory timeline, query and diff store. Filters: <code>?tool=...</code>, <code>?model=...</code>, <code>?error=true</code>.</p>{''.join(cards) or '<p>No runs yet.</p>'}</body></html>"""


def render_diff(left: Trajectory, right: Trajectory) -> str:
    diff = diff_trajectories(left, right)
    left_path = "<br>".join(html.escape(item) for item in diff.left_path)
    right_path = "<br>".join(html.escape(item) for item in diff.right_path)
    return f"""<!doctype html><html><head><meta charset='utf-8'><title>AgentTrace Diff</title>
<style>body{{font-family:system-ui;margin:2rem;background:#0b1020;color:#e7edf7}}a{{color:#7dd3fc}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:1rem}}section{{border:1px solid #27324a;border-radius:12px;padding:1rem}}code{{color:#c4b5fd}}</style></head>
<body><p><a href='/'>← runs</a></p><h1>Trajectory Diff</h1><p>same path: <strong>{str(diff.same_path).lower()}</strong> · first divergence: {diff.first_divergence}</p>
<div class='grid'><section><h2>{html.escape(left.run_id)}</h2><code>{left_path}</code></section><section><h2>{html.escape(right.run_id)}</h2><code>{right_path}</code></section></div></body></html>"""
