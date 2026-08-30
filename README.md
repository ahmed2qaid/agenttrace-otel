# AgentTrace OTel

OpenTelemetry-native trajectory tracing for AI agents, focused on **what path the agent took**, not only prompts, tokens, and latency.

## v0.2

AgentTrace now includes framework-facing instrumentation for:

- OpenAI Agents SDK lifecycle hooks
- LangGraph v3 event streams
- n8n execution payload imports
- MCP tool calls
- token/request usage attributes
- optional model cost calculation
- error and retry annotations
- trajectory diff from v0.1

```text
OpenAI Agents ─┐
LangGraph      ├─> AgentTrace trajectory ─> OpenTelemetry spans
n8n executions ┤                         └─> Run/trajectory diff
MCP clients   ─┘
```

## Core

```python
from agenttrace_otel import AgentTraceSession

with AgentTraceSession("run-123") as trace:
    with trace.step("search_web", kind="tool"):
        ...

    trace.record(
        "gpt-5",
        kind="model",
        attributes={"usage.total_tokens": 1200},
    )
```

## OpenAI Agents SDK

Install the optional integration:

```bash
pip install -e '.[openai]'
```

Then pass the hooks object to `Runner.run(..., hooks=...)`:

```python
from agenttrace_otel import AgentTraceSession, OpenAIAgentsTraceHooks

with AgentTraceSession("support-42") as trace:
    hooks = OpenAIAgentsTraceHooks(trace)
    result = await Runner.run(agent, user_input, hooks=hooks)
```

The adapter records agent, LLM, tool, handoff, usage, and timing events while remaining independent of OpenAI's own trace exporter.

## LangGraph

The adapter targets LangGraph's current v3 protocol-event stream:

```python
adapter = LangGraphEventAdapter(trace)
run = graph.stream_events(input, version="v3")
for event in run:
    adapter.process(event)
```

Tool lifecycle, model-finish usage, and graph lifecycle events become AgentTrace events.

## n8n

```python
count = import_n8n_execution(trace, execution_payload)
```

It reads `data.resultData.runData`, preserves repeated node attempts as retries, and marks failed attempts.

## MCP

```python
client = TracedMCPClient(mcp_client, trace, server_name="billing")
result = await client.call_tool("refund", {"invoice": "A-10"})
```

This works with a current MCP SDK client or any compatible object exposing `call_tool`.

## Why this project exists

Many observability platforms answer “what did the model cost?” AgentTrace additionally answers:

> Which tools and agents were used, in what order, where did the path diverge, and did a new version add risky or unnecessary steps?

That trajectory becomes the input for v0.3 replay, assertions, and regression gates.

See [ROADMAP.md](ROADMAP.md).

## License

MIT.
