#!/usr/bin/env python3
"""Baseline runner contract for the verification benchmark.

This runner is intentionally thin: it loads benchmark claims and delegates each
claim to a callable specified as ``module:function``. The adapter function keeps
benchmark code decoupled from ReelAgent internals while letting Experiment 0 use
the current verification pipeline unchanged.

Adapter signature::

    def verify_claim(claim: str) -> dict:
        ...

The returned mapping should contain at least ``verdict`` and may include:
``query``, ``source_domains``, ``selected_evidence``, ``evidence_found``,
``relevant_passage_found``, ``search_calls``, ``input_tokens``, and
``output_tokens``.

Example::

    python benchmarks/verification/run_baseline.py \
      --claims benchmarks/verification/claims.jsonl \
      --adapter mypackage.benchmark_adapter:verify_claim \
      --output benchmark_results/verification/baseline.jsonl
"""

from __future__ import annotations

import argparse
import importlib
import json
import time
from pathlib import Path
from typing import Any, Callable


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at {path}:{line_number}: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"Expected JSON object at {path}:{line_number}")
            rows.append(row)
    return rows


def load_adapter(spec: str) -> Callable[[str], dict[str, Any]]:
    if ":" not in spec:
        raise ValueError("Adapter must be in module:function format")
    module_name, function_name = spec.split(":", 1)
    module = importlib.import_module(module_name)
    adapter = getattr(module, function_name)
    if not callable(adapter):
        raise TypeError(f"Adapter is not callable: {spec}")
    return adapter


def run_claim(adapter: Callable[[str], dict[str, Any]], claim: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    response = adapter(str(claim["claim"]))
    latency_ms = round((time.perf_counter() - started) * 1000, 2)

    if not isinstance(response, dict):
        raise TypeError("Benchmark adapter must return a mapping")
    if "verdict" not in response:
        raise ValueError("Benchmark adapter result must include 'verdict'")

    result = {
        "id": claim["id"],
        "claim": claim["claim"],
        "latency_ms": response.get("latency_ms", latency_ms),
        **response,
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claims", type=Path, required=True)
    parser.add_argument("--adapter", required=True, help="module:function callable")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, help="Run only the first N claims")
    args = parser.parse_args()

    claims = read_jsonl(args.claims)
    if args.limit is not None:
        claims = claims[: args.limit]

    adapter = load_adapter(args.adapter)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    with args.output.open("w", encoding="utf-8") as handle:
        for index, claim in enumerate(claims, start=1):
            result = run_claim(adapter, claim)
            handle.write(json.dumps(result, sort_keys=True) + "\n")
            handle.flush()
            print(f"[{index}/{len(claims)}] {claim['id']}: {result['verdict']}")


if __name__ == "__main__":
    main()
