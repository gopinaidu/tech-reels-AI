from reelagent.verification.benchmark import _benchmark_result, _benchmark_verdict
from reelagent.verification.models import (
    ClaimVerificationRequest,
    ClaimVerificationResult,
    ClaimVerificationVerdict,
)


def _request() -> ClaimVerificationRequest:
    return ClaimVerificationRequest(
        claim_index=0,
        claim_text="A benchmark claim",
        introducing_evidence_ids=("benchmark-input",),
    )


def test_benchmark_verdict_maps_existing_verdicts() -> None:
    assert _benchmark_verdict(ClaimVerificationVerdict.SUPPORTED) == "SUPPORTED"
    assert _benchmark_verdict(ClaimVerificationVerdict.UNSUPPORTED) == "CONTRADICTED"
    assert _benchmark_verdict(ClaimVerificationVerdict.INSUFFICIENT_EVIDENCE) == "INCONCLUSIVE"


def test_benchmark_result_preserves_insufficient_evidence_without_inventing_telemetry() -> None:
    result = ClaimVerificationResult(
        request=_request(),
        verdict=ClaimVerificationVerdict.INSUFFICIENT_EVIDENCE,
        rationale="No independent authoritative evidence was collected.",
    )

    benchmark = _benchmark_result(result)

    assert benchmark["verdict"] == "INCONCLUSIVE"
    assert benchmark["source_domains"] == []
    assert benchmark["selected_evidence"] == []
    assert benchmark["evidence_found"] is False
    assert benchmark["relevant_passage_found"] is False
