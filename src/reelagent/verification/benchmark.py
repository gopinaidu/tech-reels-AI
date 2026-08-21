from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import Any
from urllib.parse import urlparse

from reelagent.config import get_settings
from reelagent.verification.models import (
    ClaimVerificationRequest,
    ClaimVerificationResult,
    ClaimVerificationVerdict,
)
from reelagent.verification.pipeline import VerificationPipeline
from reelagent.verification.runtime import build_verification_pipeline

_BENCHMARK_EVIDENCE_ID = "benchmark-input"


def verify_claim(claim: str) -> dict[str, Any]:
    """Run one benchmark claim through the current production verification pipeline."""

    return asyncio.run(_verify_claim(claim))


async def _verify_claim(claim: str) -> dict[str, Any]:
    request = ClaimVerificationRequest(
        claim_index=0,
        claim_text=claim,
        introducing_evidence_ids=(_BENCHMARK_EVIDENCE_ID,),
    )
    result = await _pipeline().verify_claim(request)
    return _benchmark_result(result)


@lru_cache(maxsize=1)
def _pipeline() -> VerificationPipeline:
    return build_verification_pipeline(get_settings())


def _benchmark_result(result: ClaimVerificationResult) -> dict[str, Any]:
    evidence = result.verification_evidence
    domains = sorted(
        {
            hostname
            for item in evidence
            if (hostname := urlparse(str(item.source.url)).hostname) is not None
        }
    )
    selected_evidence = [
        {
            "url": str(item.source.url),
            "source_kind": item.source.source_kind.value,
            "summary": item.summary,
        }
        for item in evidence
    ]

    return {
        "verdict": _benchmark_verdict(result.verdict),
        "source_domains": domains,
        "selected_evidence": selected_evidence,
        "evidence_found": bool(evidence),
        # The current verifier works with search snippets/page excerpts but does not
        # expose whether the final summary came from a fetched page or search snippet.
        # Leave passage recall false rather than infer telemetry that does not exist.
        "relevant_passage_found": False,
        "rationale": result.rationale,
    }


def _benchmark_verdict(verdict: ClaimVerificationVerdict) -> str:
    if verdict == ClaimVerificationVerdict.SUPPORTED:
        return "SUPPORTED"
    if verdict == ClaimVerificationVerdict.UNSUPPORTED:
        return "CONTRADICTED"
    return "INCONCLUSIVE"
