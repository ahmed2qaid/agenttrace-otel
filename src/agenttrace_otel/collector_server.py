from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .collector import TrajectoryStore, render_diff, render_index, render_timeline, trajectory_from_payload
from .replay import trajectory_to_replay


class CollectorHandler(BaseHTTPRequestHandler):
    store: TrajectoryStore

    def _write(self, body: bytes, *, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, value: object, status: int = 200) -> None:
        self._write(
            json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8"),
            content_type="application/json; charset=utf-8",
            status=status,
        )

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/runs":
            self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("request body must be a JSON object")
            trajectory = trajectory_from_payload(payload)
            self.store.put(trajectory)
        except Exception as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        self._json({"stored": trajectory.run_id}, HTTPStatus.CREATED)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if parsed.path == "/":
            runs = self.store.query(
                tool=_first(params, "tool"),
                model=_first(params, "model"),
                error=_bool_param(params, "error"),
            )
            self._write(render_index(runs).encode("utf-8"), content_type="text/html; charset=utf-8")
            return

        if parsed.path == "/api/runs":
            runs = self.store.query(
                tool=_first(params, "tool"),
                model=_first(params, "model"),
                error=_bool_param(params, "error"),
                limit=int(_first(params, "limit") or 100),
            )
            self._json([trajectory_to_replay(run) for run in runs])
            return

        if parsed.path.startswith("/api/runs/"):
            run_id = parsed.path[len("/api/runs/") :]
            trajectory = self.store.get(run_id)
            if trajectory is None:
                self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            else:
                self._json(trajectory_to_replay(trajectory))
            return

        if parsed.path.startswith("/runs/"):
            run_id = parsed.path[len("/runs/") :]
            trajectory = self.store.get(run_id)
            if trajectory is None:
                self._write(b"not found", content_type="text/plain", status=HTTPStatus.NOT_FOUND)
            else:
                self._write(render_timeline(trajectory).encode("utf-8"), content_type="text/html; charset=utf-8")
            return

        if parsed.path == "/diff":
            left_id = _first(params, "left")
            right_id = _first(params, "right")
            if not left_id or not right_id:
                self._write(b"left and right are required", content_type="text/plain", status=HTTPStatus.BAD_REQUEST)
                return
            left = self.store.get(left_id)
            right = self.store.get(right_id)
            if left is None or right is None:
                self._write(b"run not found", content_type="text/plain", status=HTTPStatus.NOT_FOUND)
                return
            self._write(render_diff(left, right).encode("utf-8"), content_type="text/html; charset=utf-8")
            return

        self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args) -> None:
        return


def _first(params: dict[str, list[str]], key: str) -> str | None:
    values = params.get(key)
    return values[0] if values else None


def _bool_param(params: dict[str, list[str]], key: str) -> bool | None:
    value = _first(params, key)
    if value is None:
        return None
    normalized = value.lower()
    if normalized in {"1", "true", "yes"}:
        return True
    if normalized in {"0", "false", "no"}:
        return False
    raise ValueError(f"invalid boolean query parameter: {key}")


def serve(*, database: str = "agenttrace.db", host: str = "127.0.0.1", port: int = 4319) -> None:
    store = TrajectoryStore(database)
    handler = type("ConfiguredCollectorHandler", (CollectorHandler,), {"store": store})
    server = ThreadingHTTPServer((host, port), handler)
    print(f"AgentTrace collector listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the lightweight AgentTrace trajectory collector")
    parser.add_argument("--database", default="agenttrace.db")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4319)
    args = parser.parse_args()
    serve(database=args.database, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
