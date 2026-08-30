# AgentTrace OTel

OpenTelemetry-native observability focused on **AI agent trajectories**: tool paths, step timing, failures, cost metadata, replay-friendly events, and run-to-run diffs.

## Why another observability project?

General LLM observability already exists. AgentTrace focuses on a narrower question:

> How did the agent behave, and how did that behavior change between runs?

## v0.1

- agent run/session abstraction
- OpenTelemetry spans for agent steps
- trajectory event recorder
- deterministic run diff
- JSON-serializable trace model
- unit tests and CI

## Example

```python
from agenttrace_otel import AgentTraceSession, diff_trajectories

with AgentTraceSession("run-a") as session:
    with session.step("search", kind="tool"):
        pass
    with session.step("compose", kind="model"):
        pass

run_a = session.trajectory
```

The diff engine compares ordered behavior, not only aggregate metrics.

## Planned integrations

LangGraph, OpenAI Agents SDK, Google ADK, Microsoft Agent Framework, CrewAI, n8n and MCP.

See [ROADMAP.md](ROADMAP.md).

## Status

v0.1 foundation.

## License

MIT.