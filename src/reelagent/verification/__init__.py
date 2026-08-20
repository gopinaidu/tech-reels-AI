"""Claim verification contracts and application workflow."""

from reelagent.verification.models import (
    ClaimVerificationRequest,
    ClaimVerificationResult,
    ClaimVerificationVerdict,
    VerificationOutcome,
    VerificationReport,
)
from reelagent.verification.pipeline import VerificationPipeline
from reelagent.verification.ports import ClaimVerifier, VerificationEvidenceCollector

__all__ = [
    "ClaimVerificationRequest",
    "ClaimVerificationResult",
    "ClaimVerificationVerdict",
    "ClaimVerifier",
    "VerificationEvidenceCollector",
    "VerificationOutcome",
    "VerificationPipeline",
    "VerificationReport",
]
