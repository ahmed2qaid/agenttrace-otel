# Demo Integration Contract

This repository remains the observability product. The end-to-end demo sends normalized agent trajectories and runtime events into AgentTrace; the demo does not own tracing semantics.

## Role in `ai-automation-infra-demo`

```text
Agent / n8n / MCP / durable runtime
              ↓ traces
        AgentTrace collector
              ↓
     timeline + diff + filters
```

## Demo responsibilities

- record the user request and agent run as one correlated execution
- capture model, tool, MCP and workflow steps
- show approval wait/resume as part of the trajectory
- expose cost/token/latency metadata when available
- persist runs in the local SQLite collector for a zero-setup demo
- provide a visual trajectory page and run-to-run diff

## Stable integration surface

The demo may use the Python SDK directly from its orchestrator and may send collector-compatible payloads over HTTP. The demo must not maintain a second trace schema.

A shared correlation identifier should be propagated through n8n, agent orchestration, durable execution and MCP calls so the UI can reconstruct one end-to-end story.

## Reference scenario

For a refund workflow the timeline should make the control path visible:

```text
webhook → classify → agent plan → MCP refund request → approval required
        → approval granted → durable resume → MCP refund → notification
```

The same run should support comparison against a second run where the model, prompt or tool path changed.

## Boundary rule

New tracing semantics, trajectory diff logic and collector behavior belong in `agenttrace-otel`; the integration repository only wires them together.
