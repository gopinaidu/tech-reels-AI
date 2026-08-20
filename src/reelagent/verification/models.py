from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from reelagent.intelligence.models import Evidence


class ClaimVerificationVerdict(StrEnum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class VerificationOutcome(StrEnum):
    READY_FOR_SCRIPT = "ready_for_script"
    NEEDS_RESEARCH = "needs_research"
    REVISION_REQUIRED = "revision_required"


class ClaimVerificationRequest(BaseModel, frozen=True):
    claim_index: int = Field(ge=0)
    claim_text: str = Field(min_length=1, max_length=1_000)
    introducing_evidence_ids: tuple[str, ...] = Field(min_length=1)


class ClaimVerificationResult(BaseModel, frozen=True):
    request: ClaimVerificationRequest
    verdict: ClaimVerificationVerdict
    verification_evidence: tuple[Evidence, ...] = ()
    rationale: str = Field(min_length=1, max_length=2_000)

    @model_validator(mode="after")
    def supported_claim_requires_evidence(self) -> ClaimVerificationResult:
        if self.verdict == ClaimVerificationVerdict.SUPPORTED and not self.verification_evidence:
            raise ValueError("supported claims require verification evidence")
        return self


class VerificationReport(BaseModel, frozen=True):
    outcome: VerificationOutcome
    results: tuple[ClaimVerificationResult, ...]

    @model_validator(mode="after")
    def outcome_matches_results(self) -> VerificationReport:
        verdicts = {result.verdict for result in self.results}
        expected = VerificationOutcome.READY_FOR_SCRIPT
        if ClaimVerificationVerdict.UNSUPPORTED in verdicts:
            expected = VerificationOutcome.REVISION_REQUIRED
        elif ClaimVerificationVerdict.INSUFFICIENT_EVIDENCE in verdicts:
            expected = VerificationOutcome.NEEDS_RESEARCH
        if self.outcome != expected:
            raise ValueError("verification outcome does not match claim verdicts")
        return self
