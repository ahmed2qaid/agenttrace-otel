# Execution Roadmap

## v0.1 — Trajectory-first tracing

- [x] run/session abstraction
- [x] step/tool/model event recording
- [x] OpenTelemetry span emission
- [x] ordered trajectory diff
- [x] JSON export
- [x] tests and CI

Exit criteria: developers can instrument an agent run and compare two trajectories without adopting a full observability backend.

## v0.2 — Framework instrumentation

- OpenAI Agents SDK hooks
- LangGraph callbacks
- n8n execution importer
- MCP tool-call instrumentation
- token/cost attributes
- error/retry annotations

## v0.3 — Replay and analysis

- trace replay format
- run comparison CLI
- trajectory assertions
- forbidden/required tool paths
- latency and cost regression thresholds

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
