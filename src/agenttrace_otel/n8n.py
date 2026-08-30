from __future__ import annotations

from .core import AgentTraceSession


def import_n8n_execution(session: AgentTraceSession, execution: dict) -> int:
    """Import the node timeline from an n8n execution API/export payload."""
    run_data = (((execution.get("data") or {}).get("resultData") or {}).get("runData") or {})
    if not isinstance(run_data, dict):
        return 0

    count = 0
    for node_name, attempts in run_data.items():
        if not isinstance(attempts, list):
            continue
        for index, attempt in enumerate(attempts):
            if not isinstance(attempt, dict):
                continue
            error = attempt.get("error")
            status = "error" if error else "ok"
            duration = float(attempt.get("executionTime") or 0.0)
            session.record(
                str(node_name),
                kind="n8n.node",
                status=status,
                duration_ms=duration,
                attributes={
                    "framework": "n8n",
                    "retry_index": index,
                    "start_time": attempt.get("startTime") or 0,
                    "error_type": str((error or {}).get("name", "")) if isinstance(error, dict) else "",
                },
            )
            count += 1
    return count
