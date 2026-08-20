import asyncio
from datetime import UTC, datetime

from pydantic import HttpUrl

from reelagent.cli import _print_result, verify_claim
from reelagent.intelligence.models import Evidence, EvidenceRole
from reelagent.topics.models import SourceEvidence, SourceKind
from reelagent.verification.models import (
    ClaimVerificationRequest,
    ClaimVerificationResult,
    ClaimVerificationVerdict,
)


class _Pipeline:
    def __init__(self, result: ClaimVerificationResult) -> None:
        self.result = result
        self.request: ClaimVerificationRequest | None = None

    async def verify_claim(self, request: ClaimVerificationRequest) -> ClaimVerificationResult:
        self.request = request
        return self.result.model_copy(update={"request": request})


def _result() -> ClaimVerificationResult:
    now = datetime.now(UTC)
    evidence = Evidence(
        evidence_id="postgres-docs",
        source=SourceEvidence(
            source_name="postgresql.org",
            source_kind=SourceKind.OFFICIAL,
            url=HttpUrl("https://www.postgresql.org/docs/current/sql-select.html"),
            published_at=now,
        ),
        roles=frozenset({EvidenceRole.VERIFICATION}),
        summary="Official PostgreSQL SELECT documentation.",
        retrieved_at=now,
    )
    request = ClaimVerificationRequest(
        claim_index=0,
        claim_text="placeholder",
        introducing_evidence_ids=("cli:manual-claim",),
    )
    return ClaimVerificationResult(
        request=request,
        verdict=ClaimVerificationVerdict.SUPPORTED,
        verification_evidence=(evidence,),
        rationale="The official documentation supports the claim.",
    )


def test_verify_claim_builds_manual_request() -> None:
    pipeline = _Pipeline(_result())

    result = asyncio.run(verify_claim("PostgreSQL supports SKIP LOCKED.", pipeline))  # type: ignore[arg-type]

    assert pipeline.request is not None
    assert pipeline.request.claim_text == "PostgreSQL supports SKIP LOCKED."
    assert pipeline.request.introducing_evidence_ids == ("cli:manual-claim",)
    assert result.verdict == ClaimVerificationVerdict.SUPPORTED


def test_print_result_shows_verdict_reason_and_evidence(capsys: object) -> None:
    result = _result()

    _print_result(result)

    # pytest's capture fixture is intentionally kept out of the application type surface.
    output = capsys.readouterr().out  # type: ignore[attr-defined]
    assert "Verdict: SUPPORTED" in output
    assert "postgresql.org" in output
    assert "official documentation supports" in output
