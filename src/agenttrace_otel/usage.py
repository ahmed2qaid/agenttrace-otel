from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UsageSnapshot:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    requests: int = 0
    cost_usd: float | None = None

    def attributes(self) -> dict[str, object]:
        data: dict[str, object] = {
            "usage.input_tokens": self.input_tokens,
            "usage.output_tokens": self.output_tokens,
            "usage.total_tokens": self.total_tokens,
            "usage.requests": self.requests,
        }
        if self.cost_usd is not None:
            data["usage.cost_usd"] = self.cost_usd
        return data


def _read(source, *names, default=0):
    for name in names:
        if isinstance(source, dict) and name in source:
            return source[name]
        if hasattr(source, name):
            return getattr(source, name)
    return default


def usage_snapshot(source, *, model: str | None = None, pricing: dict[str, dict[str, float]] | None = None) -> UsageSnapshot:
    if source is None:
        return UsageSnapshot()
    source = getattr(source, "usage", source)
    input_tokens = int(_read(source, "input_tokens", "prompt_tokens", default=0) or 0)
    output_tokens = int(_read(source, "output_tokens", "completion_tokens", default=0) or 0)
    total_tokens = int(_read(source, "total_tokens", default=input_tokens + output_tokens) or (input_tokens + output_tokens))
    requests = int(_read(source, "requests", "request_count", default=0) or 0)

    cost = None
    if model and pricing and model in pricing:
        price = pricing[model]
        input_per_million = float(price.get("input_per_million", 0.0))
        output_per_million = float(price.get("output_per_million", 0.0))
        cost = (input_tokens / 1_000_000) * input_per_million + (output_tokens / 1_000_000) * output_per_million

    return UsageSnapshot(input_tokens, output_tokens, total_tokens, requests, cost)
