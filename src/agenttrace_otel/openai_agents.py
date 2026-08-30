from __future__ import annotations

import time

from .core import AgentTraceSession
from .usage import usage_snapshot

try:
    from agents import RunHooks as _RunHooks
except ImportError:  # optional integration
    class _RunHooks:  # type: ignore[no-redef]
        pass


class OpenAIAgentsTraceHooks(_RunHooks):
    """OpenAI Agents SDK RunHooks that mirror lifecycle events into AgentTrace."""

    def __init__(self, session: AgentTraceSession, *, pricing=None) -> None:
        self.session = session
        self.pricing = pricing or {}
        self._started: dict[tuple[str, str], float] = {}

    @staticmethod
    def _name(obj, fallback: str) -> str:
        return str(getattr(obj, "name", fallback))

    def _start(self, kind: str, name: str) -> None:
        self._started[(kind, name)] = time.perf_counter()

    def _finish(self, kind: str, name: str) -> float:
        started = self._started.pop((kind, name), None)
        return 0.0 if started is None else (time.perf_counter() - started) * 1000

    async def on_agent_start(self, context, agent) -> None:
        name = self._name(agent, "agent")
        self._start("agent", name)
        self.session.record(name, kind="agent.start", attributes={"framework": "openai-agents"})

    async def on_agent_end(self, context, agent, output) -> None:
        name = self._name(agent, "agent")
        usage = usage_snapshot(context)
        self.session.record(
            name,
            kind="agent",
            duration_ms=self._finish("agent", name),
            attributes={"framework": "openai-agents", **usage.attributes()},
        )

    async def on_llm_start(self, context, agent, system_prompt, input_items) -> None:
        name = self._name(agent, "agent")
        self._start("model", name)

    async def on_llm_end(self, context, agent, response) -> None:
        name = self._name(agent, "agent")
        model = str(getattr(response, "model", getattr(agent, "model", "unknown")))
        usage = usage_snapshot(context, model=model, pricing=self.pricing)
        self.session.record(
            model,
            kind="model",
            duration_ms=self._finish("model", name),
            attributes={"framework": "openai-agents", "agent": name, **usage.attributes()},
        )

    async def on_tool_start(self, context, agent, tool) -> None:
        name = self._name(tool, "tool")
        self._start("tool", name)

    async def on_tool_end(self, context, agent, tool, result) -> None:
        name = self._name(tool, "tool")
        call_id = getattr(context, "tool_call_id", None)
        attrs = {"framework": "openai-agents", "agent": self._name(agent, "agent")}
        if call_id:
            attrs["tool_call_id"] = str(call_id)
        self.session.record(name, kind="tool", duration_ms=self._finish("tool", name), attributes=attrs)

    async def on_handoff(self, context, from_agent, to_agent) -> None:
        self.session.record(
            f"{self._name(from_agent, 'agent')}->{self._name(to_agent, 'agent')}",
            kind="handoff",
            attributes={"framework": "openai-agents"},
        )
