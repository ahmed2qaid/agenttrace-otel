# Execution Roadmap

## v0.1 — Trajectory-first tracing

- [x] run/session abstraction
- [x] step/tool/model event recording
- [x] OpenTelemetry span emission
- [x] ordered trajectory diff
- [x] JSON export
- [x] tests and CI

## v0.2 — Framework instrumentation

- [x] OpenAI Agents SDK RunHooks adapter
- [x] LangGraph v3 event-stream adapter
- [x] n8n execution importer
- [x] MCP tool-call wrapper
- [x] token/request usage attributes
- [x] optional model cost calculation
- [x] error annotations
- [x] retry annotations for imported n8n attempts
- [x] integration tests

Exit criteria: one AgentTrace trajectory can be populated from live framework lifecycle events or imported automation execution data without adopting a proprietary observability backend.

## v0.3 — Replay and analysis

- trace replay format
- run comparison CLI
- trajectory assertions
- forbidden/required tool paths
- latency and cost regression thresholds
- retry-rate regression thresholds

## v0.4 — Collector and UI

- OTLP receiver example
- lightweight local collector
- run timeline UI
- visual trajectory diff
- query by tool/model/error

## v1.0

- stable semantic conventions for agent spans
- multi-framework compatibility suite
- sampling guidance
- export to standard OTel backends
- benchmark and overhead report
