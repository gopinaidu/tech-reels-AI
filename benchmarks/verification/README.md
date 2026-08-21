# Verification Benchmark

This benchmark measures ReelAgent's technical-claim verification pipeline before retrieval or crawling changes are introduced.

## Goals

- Establish a reproducible baseline for claim verification.
- Separate evidence-retrieval failures from verifier failures.
- Track official-source retrieval, verdict accuracy, false support, search calls, token usage, and latency when available.
- Support controlled experiments where one retrieval variable changes at a time.

## Dataset

`claims.jsonl` contains benchmark claims with:

- `id`: stable claim identifier.
- `domain`: technology/domain label.
- `claim`: self-contained technical claim.
- `expected_verdict`: `SUPPORTED`, `CONTRADICTED`, or `INCONCLUSIVE`.
- `difficulty`: `clear`, `false`, or `nuanced`.
- `expected_primary_domains`: preferred authoritative domains when known.
- `notes`: benchmark rationale, especially for nuanced cases.

## Baseline run

Experiment 0 uses ReelAgent's existing verification pipeline unchanged through `reelagent.verification.benchmark:verify_claim`.

The same local environment variables used by the application are required, including the configured LLM provider key and verification search provider key. The adapter intentionally does not add retries, alternate queries, or benchmark-specific retrieval behavior.

```bash
python benchmarks/verification/run_baseline.py \
  --claims benchmarks/verification/claims.jsonl \
  --adapter reelagent.verification.benchmark:verify_claim \
  --output benchmark_results/verification/baseline.jsonl
```

For a cheap configuration check before running all 30 paid claims, add `--limit 1`.

The adapter records returned source domains, selected evidence, verifier verdict, and rationale. Metrics that the current runtime does not expose reliably (for example token counts, the generated research query, or whether evidence text originated from the fetched page versus the search snippet) are deliberately left unreported rather than inferred.

Save baseline outputs as JSONL so later experiments can be compared claim-by-claim.

## Evaluation

`evaluate.py` computes deterministic metrics from a result JSONL file. The result format is documented in the script and intentionally does not depend on a specific search or LLM implementation.

Example:

```bash
python benchmarks/verification/evaluate.py \
  --claims benchmarks/verification/claims.jsonl \
  --results benchmark_results/verification/baseline.jsonl
```

## Experiments

Keep the baseline unchanged, then compare controlled experiments such as:

1. Claim text as the search query.
2. Existing LLM-generated query.
3. Multiple-query retrieval.
4. Authority-aware reranking.
5. Page fetching plus passage retrieval.
6. Deep-research fallback for inconclusive claims.

Do not combine several changes in the same first experiment; the benchmark is intended to identify which capability actually improves evidence retrieval.
