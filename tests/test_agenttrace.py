import unittest

from agenttrace_otel import AgentTraceSession, diff_trajectories


class AgentTraceTests(unittest.TestCase):
    def test_records_ordered_trajectory(self) -> None:
        with AgentTraceSession("run-1") as session:
            with session.step("search", kind="tool"):
                pass
            with session.step("compose", kind="model"):
                pass

        self.assertEqual([event.name for event in session.trajectory.events], ["search", "compose"])
        self.assertTrue(all(event.status == "ok" for event in session.trajectory.events))

    def test_diff_finds_divergence(self) -> None:
        with AgentTraceSession("left") as left:
            with left.step("search", kind="tool"):
                pass
            with left.step("database", kind="tool"):
                pass

        with AgentTraceSession("right") as right:
            with right.step("search", kind="tool"):
                pass
            with right.step("mcp_lookup", kind="tool"):
                pass

        diff = diff_trajectories(left.trajectory, right.trajectory)
        self.assertFalse(diff.same_path)
        self.assertEqual(diff.first_divergence, 1)
        self.assertIn("tool:database", diff.removed)
        self.assertIn("tool:mcp_lookup", diff.added)

    def test_error_is_recorded_and_reraised(self) -> None:
        session = AgentTraceSession("run-error")
        with self.assertRaises(RuntimeError):
            with session:
                with session.step("dangerous-tool", kind="tool"):
                    raise RuntimeError("boom")
        self.assertEqual(session.trajectory.events[0].status, "error")


if __name__ == "__main__":
    unittest.main()
