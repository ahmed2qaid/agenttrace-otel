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
- [x] error/retry annotations
- [x] integration tests

## v0.3 — Replay and regression gates

- [x] portable `agenttrace-trajectory/v1` replay format
- [x] save/load replay helpers
- [x] run comparison CLI (`agenttrace-gate`)
- [x] required and forbidden tool assertions
- [x] ordered required tool-path assertions
- [x] optional exact trajectory regression gate
- [x] absolute latency and cost limits
- [x] latency and cost regression thresholds against a baseline
- [x] retry-rate regression threshold
- [x] JSON output suitable for CI

Exit criteria: a committed baseline trace can block a PR or release when an agent takes a forbidden path or regresses beyond configured latency, cost, retry, or trajectory limits.

## v0.4 — Collector and UI

- [x] OpenTelemetry Collector OTLP receiver example
- [x] lightweight local HTTP collector command
- [x] SQLite-backed trajectory store
- [x] run timeline UI
- [x] visual trajectory diff view
- [x] query/filter by tool, model, and error state
- [x] JSON ingestion and query API for replay artifacts
- [x] tests for persistence, filtering, replay ingestion, and UI rendering

Exit criteria: developers can send portable AgentTrace trajectories to a local collector, inspect timelines and diffs in a browser, and query regressions without deploying a full observability platform.

## v1.0

- stable semantic conventions for agent spans
- multi-framework compatibility suite
- sampling guidance
- export to standard OTel backends
- benchmark and overhead report
