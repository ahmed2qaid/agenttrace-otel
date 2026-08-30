import asyncio
import unittest

from agenttrace_otel import AgentTraceSession, LangGraphEventAdapter, TracedMCPClient, import_n8n_execution, usage_snapshot


class FakeMCPResult:
    is_error = False


class FakeMCPClient:
    async def call_tool(self, name, arguments, *args, **kwargs):
        return FakeMCPResult()

    async def list_tools(self, *args, **kwargs):
        return ["demo"]


class IntegrationTests(unittest.TestCase):
    def test_n8n_importer_records_retries_and_errors(self):
        session = AgentTraceSession("n8n-run")
        count = import_n8n_execution(
            session,
            {
                "data": {
                    "resultData": {
                        "runData": {
                            "HTTP Request": [
                                {"startTime": 1, "executionTime": 10},
                                {"startTime": 2, "executionTime": 5, "error": {"name": "TimeoutError"}},
                            ]
                        }
                    }
                }
            },
        )
        self.assertEqual(count, 2)
        self.assertEqual(session.trajectory.events[1].status, "error")
        self.assertEqual(session.trajectory.events[1].attributes["retry_index"], 1)

    def test_langgraph_v3_tool_events(self):
        session = AgentTraceSession("lg-run")
        adapter = LangGraphEventAdapter(session)
        adapter.process({"method": "tools", "params": {"namespace": ["agent:1"], "data": {"event": "tool-started", "tool_name": "search", "tool_call_id": "c1"}}})
        adapter.process({"method": "tools", "params": {"namespace": ["agent:1"], "data": {"event": "tool-finished", "tool_name": "search", "tool_call_id": "c1"}}})
        self.assertEqual(session.trajectory.events[-1].name, "search")
        self.assertEqual(session.trajectory.events[-1].kind, "tool")

    def test_mcp_wrapper_records_call(self):
        async def scenario():
            session = AgentTraceSession("mcp-run")
            client = TracedMCPClient(FakeMCPClient(), session, server_name="billing")
            await client.call_tool("refund", {"id": 1})
            self.assertEqual(session.trajectory.events[-1].kind, "mcp.tool")
            self.assertEqual(session.trajectory.events[-1].attributes["server"], "billing")

        asyncio.run(scenario())

    def test_usage_and_cost_attributes(self):
        usage = usage_snapshot(
            {"input_tokens": 1000, "output_tokens": 500, "requests": 2},
            model="demo",
            pricing={"demo": {"input_per_million": 1.0, "output_per_million": 2.0}},
        )
        self.assertEqual(usage.total_tokens, 1500)
        self.assertAlmostEqual(usage.cost_usd, 0.002)


if __name__ == "__main__":
    unittest.main()
