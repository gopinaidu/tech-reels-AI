from typing import Protocol

from reelagent.intelligence.models import Evidence
from reelagent.verification.models import (
    ClaimVerificationRequest,
    ClaimVerificationResult,
)


class VerificationEvidenceCollector(Protocol):
    """Collect independent evidence for one material factual claim."""

    async def collect(self, request: ClaimVerificationRequest) -> tuple[Evidence, ...]:
        """Return bounded verification evidence without deciding the verdict."""
        ...


class ClaimVerifier(Protocol):
    """Evaluate one claim against already collected independent evidence."""

    async def verify(
        self,
        request: ClaimVerificationRequest,
        evidence: tuple[Evidence, ...],
    ) -> ClaimVerificationResult:
        """Return a structured verdict without unrelated workflow side effects."""
        ...
