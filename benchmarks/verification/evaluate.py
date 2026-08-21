#!/usr/bin/env python3
"""Evaluate ReelAgent verification benchmark result files.

Expected result JSONL fields per row:

Required:
  id: benchmark claim id
  verdict: SUPPORTED | CONTRADICTED | INCONCLUSIVE

Optional:
  source_domains: list[str]
  evidence_found: bool
  relevant_passage_found: bool
  search_calls: int
  latency_ms: number
  input_tokens: int
  output_tokens: int

The evaluator deliberately stays implementation-agnostic so the same benchmark
can compare the existing pipeline with later retrieval experiments.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any, Iterable

VALID_VERDICTS = {"SUPPORTED", "CONTRADICTED", "INCONCLUSIVE"}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at {path}:{line_number}: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"Expected JSON object at {path}:{line_number}")
            rows.append(value)
    return rows


def normalize_domain(domain: str) -> str:
    domain = domain.lower().strip()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def domain_matches(actual: str, expected: str) -> bool:
    actual = normalize_domain(actual)
    expected = normalize_domain(expected)
    return actual == expected or actual.endswith(f".{expected}")


def optional_mean(values: Iterable[Any]) -> float | None:
    numeric = [float(value) for value in values if isinstance(value, (int, float))]
    return mean(numeric) if numeric else None


def percent(numerator: int, denominator: int) -> float:
    return round((numerator / denominator) * 100, 2) if denominator else 0.0


def evaluate(claims: list[dict[str, Any]], results: list[dict[str, Any]]) -> dict[str, Any]:
    claim_by_id = {row["id"]: row for row in claims}
    result_by_id = {row["id"]: row for row in results}

    unknown_ids = sorted(set(result_by_id) - set(claim_by_id))
    missing_ids = sorted(set(claim_by_id) - set(result_by_id))

    verdict_correct = 0
    supported_total = 0
    false_supports = 0
    evidence_found = 0
    passage_found = 0
    official_source_hits = 0
    official_source_eligible = 0
    confusion: dict[str, Counter[str]] = defaultdict(Counter)
    by_difficulty: dict[str, Counter[str]] = defaultdict(Counter)
    by_domain: dict[str, Counter[str]] = defaultdict(Counter)

    evaluated = 0
    for claim_id, claim in claim_by_id.items():
        result = result_by_id.get(claim_id)
        if result is None:
            continue

        expected = str(claim["expected_verdict"]).upper()
        actual = str(result.get("verdict", "")).upper()
        if expected not in VALID_VERDICTS:
            raise ValueError(f"Invalid expected verdict for {claim_id}: {expected}")
        if actual not in VALID_VERDICTS:
            raise ValueError(f"Invalid result verdict for {claim_id}: {actual}")

        evaluated += 1
        is_correct = actual == expected
        verdict_correct += int(is_correct)
        confusion[expected][actual] += 1

        difficulty = str(claim.get("difficulty", "unknown"))
        domain = str(claim.get("domain", "unknown"))
        by_difficulty[difficulty]["total"] += 1
        by_difficulty[difficulty]["correct"] += int(is_correct)
        by_domain[domain]["total"] += 1
        by_domain[domain]["correct"] += int(is_correct)

        if expected == "SUPPORTED":
            supported_total += 1
        elif actual == "SUPPORTED":
            false_supports += 1

        evidence_found += int(bool(result.get("evidence_found", False)))
        passage_found += int(bool(result.get("relevant_passage_found", False)))

        expected_domains = claim.get("expected_primary_domains", []) or []
        if expected_domains:
            official_source_eligible += 1
            actual_domains = result.get("source_domains", []) or []
            hit = any(
                domain_matches(actual_domain, expected_domain)
                for actual_domain in actual_domains
                for expected_domain in expected_domains
            )
            official_source_hits += int(hit)

    total_tokens = [
        int(row.get("input_tokens", 0) or 0) + int(row.get("output_tokens", 0) or 0)
        for row in results
        if "input_tokens" in row or "output_tokens" in row
    ]

    return {
        "claims_total": len(claims),
        "claims_evaluated": evaluated,
        "missing_result_count": len(missing_ids),
        "missing_result_ids": missing_ids,
        "unknown_result_ids": unknown_ids,
        "verdict_accuracy_pct": percent(verdict_correct, evaluated),
        "false_support_rate_pct": percent(false_supports, evaluated - supported_total),
        "evidence_found_rate_pct": percent(evidence_found, evaluated),
        "passage_recall_pct": percent(passage_found, evaluated),
        "official_source_recall_pct": percent(official_source_hits, official_source_eligible),
        "avg_search_calls": optional_mean(row.get("search_calls") for row in results),
        "avg_latency_ms": optional_mean(row.get("latency_ms") for row in results),
        "avg_total_tokens": optional_mean(total_tokens),
        "confusion_matrix": {expected: dict(counts) for expected, counts in confusion.items()},
        "accuracy_by_difficulty": {
            key: percent(counts["correct"], counts["total"])
            for key, counts in sorted(by_difficulty.items())
        },
        "accuracy_by_domain": {
            key: percent(counts["correct"], counts["total"])
            for key, counts in sorted(by_domain.items())
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claims", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, help="Optional path for JSON summary")
    args = parser.parse_args()

    summary = evaluate(read_jsonl(args.claims), read_jsonl(args.results))
    rendered = json.dumps(summary, indent=2, sort_keys=True)
    print(rendered)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
