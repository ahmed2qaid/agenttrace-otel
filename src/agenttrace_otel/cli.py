from __future__ import annotations

import argparse
import json

from .analysis import GatePolicy, evaluate_gate
from .replay import load_replay


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare AgentTrace runs and enforce regression policies")
    parser.add_argument("candidate", help="candidate replay JSON")
    parser.add_argument("--baseline", help="optional baseline replay JSON")
    parser.add_argument("--policy", required=True, help="gate policy JSON")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    candidate = load_replay(args.candidate)
    baseline = load_replay(args.baseline) if args.baseline else None
    policy = GatePolicy.from_dict(json.load(open(args.policy, encoding="utf-8")))
    result = evaluate_gate(candidate, policy, baseline)

    if args.json_output:
        print(
            json.dumps(
                {
                    "passed": result.passed,
                    "candidate": result.candidate.__dict__,
                    "baseline": None if result.baseline is None else result.baseline.__dict__,
                    "violations": [item.__dict__ for item in result.violations],
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print("PASS" if result.passed else "FAIL")
        print(
            f"candidate latency={result.candidate.latency_ms:.2f}ms "
            f"cost=${result.candidate.cost_usd:.6f} retry_rate={result.candidate.retry_rate:.3f}"
        )
        for violation in result.violations:
            print(f"[{violation.severity.upper()}] {violation.code}: {violation.message}")

    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
