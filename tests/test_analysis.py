import tempfile
import unittest
from pathlib import Path

from agenttrace_otel import (
    GatePolicy,
    TraceEvent,
    Trajectory,
    evaluate_gate,
    load_replay,
    save_replay,
)


def event(name, kind="tool", duration=10, *, cost=0.0, retry=0, status="ok"):
    attrs = {"retry_index": retry}
    if cost:
        attrs["usage.cost_usd"] = cost
    return TraceEvent(name, kind, status, duration, attrs)


class AnalysisTests(unittest.TestCase):
    def test_replay_round_trip(self):
        trajectory = Trajectory("run-1", [event("search"), event("answer", "model", cost=0.02)], {"model": "x"})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trace.json"
            save_replay(path, trajectory)
            loaded = load_replay(path)
        self.assertEqual(loaded.run_id, "run-1")
        self.assertEqual([e.name for e in loaded.events], ["search", "answer"])
        self.assertEqual(loaded.attributes["model"], "x")

    def test_forbidden_tool_fails_gate(self):
        candidate = Trajectory("candidate", [event("delete_customer")])
        result = evaluate_gate(candidate, GatePolicy(forbidden_tools=("delete_*",)))
        self.assertFalse(result.passed)
        self.assertEqual(result.violations[0].code, "tool.forbidden")

    def test_required_order_is_enforced(self):
        good = Trajectory("good", [event("lookup"), event("approve"), event("refund")])
        bad = Trajectory("bad", [event("lookup"), event("refund")])
        policy = GatePolicy(required_path=("lookup", "approve", "refund"))
        self.assertTrue(evaluate_gate(good, policy).passed)
        self.assertFalse(evaluate_gate(bad, policy).passed)

    def test_latency_cost_and_retry_regressions(self):
        baseline = Trajectory(
            "base",
            [event("search", duration=100, cost=0.01), event("answer", "model", duration=100, cost=0.01)],
        )
        candidate = Trajectory(
            "candidate",
            [
                event("search", duration=150, cost=0.02),
                event("search", duration=150, cost=0.02, retry=1),
                event("answer", "model", duration=100, cost=0.02),
            ],
        )
        policy = GatePolicy(
            max_latency_increase_pct=20,
            max_cost_increase_pct=20,
            max_retry_rate_increase_pct=10,
        )
        result = evaluate_gate(candidate, policy, baseline)
        self.assertFalse(result.passed)
        codes = {item.code for item in result.violations}
        self.assertEqual(codes, {"latency.regression", "cost.regression", "retry.regression"})

    def test_same_path_gate(self):
        baseline = Trajectory("base", [event("search"), event("answer", "model")])
        candidate = Trajectory("candidate", [event("search"), event("database"), event("answer", "model")])
        result = evaluate_gate(candidate, GatePolicy(require_same_path=True), baseline)
        self.assertFalse(result.passed)
        self.assertEqual(result.violations[0].code, "trajectory.changed")


if __name__ == "__main__":
    unittest.main()
