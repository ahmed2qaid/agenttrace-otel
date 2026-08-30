from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agenttrace_otel.collector import TrajectoryStore, render_diff, render_timeline, trajectory_from_payload
from agenttrace_otel.core import TraceEvent, Trajectory
from agenttrace_otel.replay import trajectory_to_replay


class CollectorTests(unittest.TestCase):
    def test_store_query_and_diff(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = TrajectoryStore(Path(tmp) / "trace.db")
            left = Trajectory(
                run_id="left",
                attributes={"model": "gpt-test"},
                events=[
                    TraceEvent("search", "tool", "ok", 10, {}),
                    TraceEvent("answer", "model", "ok", 20, {"model": "gpt-test"}),
                ],
            )
            right = Trajectory(
                run_id="right",
                attributes={"model": "gpt-test"},
                events=[
                    TraceEvent("search", "tool", "ok", 8, {}),
                    TraceEvent("db", "tool", "error", 5, {}),
                    TraceEvent("answer", "model", "ok", 15, {"model": "gpt-test"}),
                ],
            )
            store.put(left)
            store.put(right)
            self.assertEqual([run.run_id for run in store.query(tool="db")], ["right"])
            self.assertEqual({run.run_id for run in store.query(model="gpt-test")}, {"left", "right"})
            self.assertEqual([run.run_id for run in store.query(error=True)], ["right"])
            self.assertFalse(store.compare("left", "right").same_path)

    def test_accepts_replay_payload(self):
        trajectory = Trajectory(run_id="r1", events=[TraceEvent("lookup", "tool", "ok", 1, {})])
        parsed = trajectory_from_payload(trajectory_to_replay(trajectory))
        self.assertEqual(parsed.run_id, "r1")
        self.assertEqual(parsed.events[0].name, "lookup")

    def test_html_views_render_paths(self):
        left = Trajectory(run_id="a", events=[TraceEvent("search", "tool", "ok", 1, {})])
        right = Trajectory(run_id="b", events=[TraceEvent("lookup", "tool", "ok", 1, {})])
        self.assertIn("tool", render_timeline(left))
        page = render_diff(left, right)
        self.assertIn("first divergence", page)
        self.assertIn("tool:search", page)


if __name__ == "__main__":
    unittest.main()
