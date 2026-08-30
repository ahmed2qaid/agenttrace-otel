from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from typing import Iterator

from opentelemetry import trace


@dataclass(frozen=True)
class TraceEvent:
    name: str
    kind: str
    status: str
    duration_ms: float
    attributes: dict[str, object] = field(default_factory=dict)


@dataclass
class Trajectory:
    run_id: str
    events: list[TraceEvent] = field(default_factory=list)
    attributes: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "events": [asdict(event) for event in self.events],
            "attributes": dict(self.attributes),
        }


@dataclass(frozen=True)
class TrajectoryDiff:
    same_path: bool
    added: tuple[str, ...]
    removed: tuple[str, ...]
    first_divergence: int | None
    left_path: tuple[str, ...]
    right_path: tuple[str, ...]


class AgentTraceSession:
    def __init__(
        self,
        run_id: str,
        *,
        tracer_name: str = "agenttrace-otel",
        attributes: dict[str, object] | None = None,
    ) -> None:
        if not run_id:
            raise ValueError("run_id must not be empty")
        self.trajectory = Trajectory(run_id=run_id, attributes=attributes or {})
        self._tracer = trace.get_tracer(tracer_name)
        self._root_context = None

    def __enter__(self) -> "AgentTraceSession":
        self._root_context = self._tracer.start_as_current_span(
            "agent.run",
            attributes={
                "agenttrace.run_id": self.trajectory.run_id,
                **{f"agenttrace.{k}": v for k, v in self.trajectory.attributes.items()},
            },
        )
        self._root_context.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._root_context is not None:
            self._root_context.__exit__(exc_type, exc, tb)

    @contextmanager
    def step(
        self,
        name: str,
        *,
        kind: str,
        attributes: dict[str, object] | None = None,
    ) -> Iterator[None]:
        attrs = attributes or {}
        started = time.perf_counter()
        status = "ok"
        try:
            with self._tracer.start_as_current_span(
                f"agent.{kind}",
                attributes={
                    "agenttrace.step.name": name,
                    "agenttrace.step.kind": kind,
                    **{f"agenttrace.{k}": v for k, v in attrs.items()},
                },
            ):
                yield
        except Exception:
            status = "error"
            raise
        finally:
            duration_ms = (time.perf_counter() - started) * 1000
            self.trajectory.events.append(
                TraceEvent(
                    name=name,
                    kind=kind,
                    status=status,
                    duration_ms=duration_ms,
                    attributes=dict(attrs),
                )
            )


def diff_trajectories(left: Trajectory, right: Trajectory) -> TrajectoryDiff:
    left_path = tuple(f"{event.kind}:{event.name}" for event in left.events)
    right_path = tuple(f"{event.kind}:{event.name}" for event in right.events)

    divergence = None
    for index, pair in enumerate(zip(left_path, right_path)):
        if pair[0] != pair[1]:
            divergence = index
            break
    if divergence is None and len(left_path) != len(right_path):
        divergence = min(len(left_path), len(right_path))

    left_counts = {item: left_path.count(item) for item in set(left_path)}
    right_counts = {item: right_path.count(item) for item in set(right_path)}

    removed: list[str] = []
    added: list[str] = []
    for item, count in left_counts.items():
        removed.extend([item] * max(0, count - right_counts.get(item, 0)))
    for item, count in right_counts.items():
        added.extend([item] * max(0, count - left_counts.get(item, 0)))

    return TrajectoryDiff(
        same_path=left_path == right_path,
        added=tuple(sorted(added)),
        removed=tuple(sorted(removed)),
        first_divergence=divergence,
        left_path=left_path,
        right_path=right_path,
    )


__all__ = [
    "AgentTraceSession",
    "TraceEvent",
    "Trajectory",
    "TrajectoryDiff",
    "diff_trajectories",
]
