from __future__ import annotations

import argparse
import asyncio
from collections.abc import Sequence

from reelagent.config import Settings
from reelagent.verification.models import (
    ClaimVerificationRequest,
    ClaimVerificationResult,
    ClaimVerificationVerdict,
)
from reelagent.verification.pipeline import VerificationPipeline
from reelagent.verification.runtime import build_verification_pipeline

_EXIT_OK = 0
_EXIT_ERROR = 1
_EXIT_NEEDS_RESEARCH = 2
_EXIT_UNSUPPORTED = 3


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "verify":
        return asyncio.run(_verify(args.claim))
    parser.print_help()
    return _EXIT_ERROR


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="reelagent", description="ReelAgent developer CLI")
    subparsers = parser.add_subparsers(dest="command")
    verify = subparsers.add_parser("verify", help="verify one factual claim")
    verify.add_argument("--claim", required=True, help="factual claim to verify")
    return parser


async def _verify(claim: str) -> int:
    try:
        pipeline = build_verification_pipeline(Settings())
        result = await verify_claim(claim, pipeline)
    except Exception as exc:  # CLI boundary: present configuration/network errors cleanly.
        print(f"Verification failed: {exc}")
        return _EXIT_ERROR

    _print_result(result)
    if result.verdict == ClaimVerificationVerdict.SUPPORTED:
        return _EXIT_OK
    if result.verdict == ClaimVerificationVerdict.UNSUPPORTED:
        return _EXIT_UNSUPPORTED
    return _EXIT_NEEDS_RESEARCH


async def verify_claim(claim: str, pipeline: VerificationPipeline) -> ClaimVerificationResult:
    request = ClaimVerificationRequest(
        claim_index=0,
        claim_text=claim,
        introducing_evidence_ids=("cli:manual-claim",),
    )
    return await pipeline.verify_claim(request)


def _print_result(result: ClaimVerificationResult) -> None:
    print(f"Verdict: {result.verdict.value.upper()}")
    print(f"Claim: {result.request.claim_text}")
    print(f"Reason: {result.rationale}")
    if result.verification_evidence:
        print("Evidence:")
        for item in result.verification_evidence:
            print(f"  - {item.source.source_name}: {item.source.url}")
