from __future__ import annotations

import time

from .core import AgentTraceSession


class TracedMCPClient:
    """Thin wrapper around any MCP client exposing call_tool/list_tools."""

    def __init__(self, client, session: AgentTraceSession, *, server_name: str = "mcp") -> None:
        self.client = client
        self.session = session
        self.server_name = server_name

    async def list_tools(self, *args, **kwargs):
        return await self.client.list_tools(*args, **kwargs)

    async def call_tool(self, name: str, arguments: dict, *args, **kwargs):
        started = time.perf_counter()
        status = "ok"
        try:
            result = await self.client.call_tool(name, arguments, *args, **kwargs)
            if getattr(result, "is_error", False):
                status = "error"
            return result
        except Exception:
            status = "error"
            raise
        finally:
            self.session.record(
                name,
                kind="mcp.tool",
                status=status,
                duration_ms=(time.perf_counter() - started) * 1000,
                attributes={"framework": "mcp", "server": self.server_name},
            )
