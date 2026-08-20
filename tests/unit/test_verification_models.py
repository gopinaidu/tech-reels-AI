import pytest
from pydantic import ValidationError

from reelagent.verification.models import (
    ClaimVerificationRequest,
    ClaimVerificationResult,
    ClaimVerificationVerdict,
    VerificationOutcome,
    VerificationReport,
)


def _request() -> ClaimVerificationRequest:
    return ClaimVerificationRequest(
        claim_index=0,
        claim_text="PostgreSQL supports a documented locking feature.",
        introducing_evidence_ids=("discovery:1",),
    )


def test_supported_result_requires_verification_evidence() -> None:
    with pytest.raises(ValidationError, match="supported claims require verification evidence"):
        ClaimVerificationResult(
            request=_request(),
            verdict=ClaimVerificationVerdict.SUPPORTED,
            rationale="Claim appears supported.",
        )


def test_report_rejects_outcome_that_disagrees_with_verdicts() -> None:
    result = ClaimVerificationResult(
        request=_request(),
        verdict=ClaimVerificationVerdict.INSUFFICIENT_EVIDENCE,
        rationale="More evidence is required.",
    )

    with pytest.raises(ValidationError, match="outcome does not match"):
        VerificationReport(
            outcome=VerificationOutcome.READY_FOR_SCRIPT,
            results=(result,),
        )
