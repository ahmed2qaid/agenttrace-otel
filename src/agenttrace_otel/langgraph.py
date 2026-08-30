from __future__ import annotations

import time

from .core import AgentTraceSession
from .usage import usage_snapshot


class LangGraphEventAdapter:
    """Consume LangGraph v3 protocol events without requiring LangGraph as a dependency."""

    def __init__(self, session: AgentTraceSession) -> None:
        self.session = session
        self._tool_started: dict[str, float] = {}

    def process(self, event: dict) -> bool:
        method = event.get("method")
        params = event.get("params") or {}
        data = params.get("data") or {}
        namespace = params.get("namespace") or []
        if not isinstance(data, dict):
            return True

        if method == "tools":
            state = data.get("event")
            tool_name = str(data.get("tool_name") or data.get("name") or "tool")
            call_id = str(data.get("tool_call_id") or data.get("id") or tool_name)
            if state == "tool-started":
                self._tool_started[call_id] = time.perf_counter()
            elif state in {"tool-finished", "tool-error"}:
                started = self._tool_started.pop(call_id, None)
                duration = 0.0 if started is None else (time.perf_counter() - started) * 1000
                self.session.record(
                    tool_name,
                    kind="tool",
                    status="error" if state == "tool-error" else "ok",
                    duration_ms=duration,
                    attributes={"framework": "langgraph", "namespace": "/".join(namespace), "tool_call_id": call_id},
                )

        elif method == "messages" and data.get("event") == "message-finish":
            usage = data.get("usage") or data.get("usage_metadata") or {}
            snapshot = usage_snapshot(usage)
            self.session.record(
                str(data.get("model") or data.get("node") or "model"),
                kind="model",
                attributes={"framework": "langgraph", "namespace": "/".join(namespace), **snapshot.attributes()},
            )

        elif method == "lifecycle" and data.get("event") in {"completed", "failed", "interrupted"}:
            self.session.record(
                str(data.get("graph_name") or (namespace[-1] if namespace else "graph")),
                kind="graph.lifecycle",
                status="error" if data.get("event") == "failed" else str(data.get("event")),
                attributes={"framework": "langgraph", "namespace": "/".join(namespace)},
            )
        return True
