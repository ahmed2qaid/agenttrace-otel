from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatchcase

from .core import Trajectory, diff_trajectories


@dataclass(frozen=True)
class GateViolation:
    code: str
    message: str
    severity: str = "error"


@dataclass(frozen=True)
class GatePolicy:
    required_tools: tuple[str, ...] = ()
    forbidden_tools: tuple[str, ...] = ()
    required_path: tuple[str, ...] = ()
    require_same_path: bool = False
    max_latency_ms: float | None = None
    max_cost_usd: float | None = None
    max_latency_increase_pct: float | None = None
    max_cost_increase_pct: float | None = None
    max_retry_rate_increase_pct: float | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "GatePolicy":
        return cls(
            required_tools=tuple(str(x) for x in data.get("required_tools", [])),
            forbidden_tools=tuple(str(x) for x in data.get("forbidden_tools", [])),
            required_path=tuple(str(x) for x in data.get("required_path", [])),
            require_same_path=bool(data.get("require_same_path", False)),
            max_latency_ms=_optional_float(data.get("max_latency_ms")),
            max_cost_usd=_optional_float(data.get("max_cost_usd")),
            max_latency_increase_pct=_optional_float(data.get("max_latency_increase_pct")),
            max_cost_increase_pct=_optional_float(data.get("max_cost_increase_pct")),
            max_retry_rate_increase_pct=_optional_float(data.get("max_retry_rate_increase_pct")),
        )


@dataclass(frozen=True)
class RunMetrics:
    latency_ms: float
    cost_usd: float
    retry_rate: float
    tools: tuple[str, ...]
    errors: int


@dataclass(frozen=True)
class GateResult:
    passed: bool
    candidate: RunMetrics
    baseline: RunMetrics | None
    violations: tuple[GateViolation, ...] = field(default_factory=tuple)


def run_metrics(trajectory: Trajectory) -> RunMetrics:
    latency = sum(max(0.0, event.duration_ms) for event in trajectory.events)
    cost = 0.0
    tools: list[str] = []
    retries = 0
    errors = 0
    for event in trajectory.events:
        if event.kind == "tool" or event.kind.endswith(".tool") or "tool" in event.kind:
            tools.append(event.name)
        if event.status == "error":
            errors += 1
        retry_index = event.attributes.get("retry_index")
        if isinstance(retry_index, (int, float)) and retry_index > 0:
            retries += 1
        event_cost = event.attributes.get("usage.cost_usd")
        if isinstance(event_cost, (int, float)):
            cost += float(event_cost)
    retry_rate = retries / max(1, len(trajectory.events))
    return RunMetrics(latency, cost, retry_rate, tuple(tools), errors)


def evaluate_gate(candidate: Trajectory, policy: GatePolicy, baseline: Trajectory | None = None) -> GateResult:
    current = run_metrics(candidate)
    previous = run_metrics(baseline) if baseline is not None else None
    violations: list[GateViolation] = []

    for pattern in policy.required_tools:
        if not any(fnmatchcase(tool, pattern) for tool in current.tools):
            violations.append(GateViolation("tool.required_missing", f"required tool not used: {pattern}"))
    for pattern in policy.forbidden_tools:
        matched = next((tool for tool in current.tools if fnmatchcase(tool, pattern)), None)
        if matched:
            violations.append(GateViolation("tool.forbidden", f"forbidden tool used: {matched}"))

    if policy.required_path and not _ordered_path(current.tools, policy.required_path):
        violations.append(
            GateViolation("trajectory.required_path", "required ordered tool path was not observed")
        )

    if policy.max_latency_ms is not None and current.latency_ms > policy.max_latency_ms:
        violations.append(
            GateViolation(
                "latency.absolute",
                f"latency {current.latency_ms:.2f}ms exceeds {policy.max_latency_ms:.2f}ms",
            )
        )
    if policy.max_cost_usd is not None and current.cost_usd > policy.max_cost_usd:
        violations.append(
            GateViolation(
                "cost.absolute",
                f"cost ${current.cost_usd:.6f} exceeds ${policy.max_cost_usd:.6f}",
            )
        )

    if baseline is not None and previous is not None:
        if policy.require_same_path and not diff_trajectories(baseline, candidate).same_path:
            violations.append(GateViolation("trajectory.changed", "candidate trajectory differs from baseline"))
        _append_regression(
            violations,
            "latency.regression",
            "latency",
            previous.latency_ms,
            current.latency_ms,
            policy.max_latency_increase_pct,
        )
        _append_regression(
            violations,
            "cost.regression",
            "cost",
            previous.cost_usd,
            current.cost_usd,
            policy.max_cost_increase_pct,
        )
        _append_regression(
            violations,
            "retry.regression",
            "retry rate",
            previous.retry_rate,
            current.retry_rate,
            policy.max_retry_rate_increase_pct,
        )

    return GateResult(not violations, current, previous, tuple(violations))


def _ordered_path(tools: tuple[str, ...], required: tuple[str, ...]) -> bool:
    index = 0
    for tool in tools:
        if index < len(required) and fnmatchcase(tool, required[index]):
            index += 1
    return index == len(required)


def _append_regression(violations, code, label, baseline, candidate, limit):
    if limit is None:
        return
    if baseline <= 0:
        increase = 0.0 if candidate <= 0 else float("inf")
    else:
        increase = ((candidate - baseline) / baseline) * 100.0
    if increase > limit:
        text = "infinite" if increase == float("inf") else f"{increase:.2f}%"
        violations.append(GateViolation(code, f"{label} increased by {text}; limit is {limit:.2f}%"))


def _optional_float(value):
    return None if value is None else float(value)
