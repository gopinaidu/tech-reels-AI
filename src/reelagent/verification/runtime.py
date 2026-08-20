from __future__ import annotations

from reelagent.config import Settings
from reelagent.intelligence.llm_runtime import build_structured_llm_client
from reelagent.verification.adapters import (
    AuthoritativeDomainSearchClient,
    AuthoritativeSearchEvidenceCollector,
    BraveVerificationSearchClient,
    LlmClaimVerifier,
    VerificationSearchClient,
)
from reelagent.verification.pipeline import VerificationPipeline


class VerificationRuntimeConfigurationError(RuntimeError):
    """Raised when verification runtime dependencies are not configured."""


def build_verification_pipeline(settings: Settings) -> VerificationPipeline:
    """Build the concrete verification pipeline used by the application runtime."""

    search_client: VerificationSearchClient
    if settings.verification_use_brave:
        if settings.brave_search_api_key is None:
            raise VerificationRuntimeConfigurationError(
                "BRAVE_SEARCH_API_KEY is required when VERIFICATION_USE_BRAVE=true"
            )
        search_client = BraveVerificationSearchClient(api_key=settings.brave_search_api_key)
    else:
        search_client = AuthoritativeDomainSearchClient()

    evidence_collector = AuthoritativeSearchEvidenceCollector(
        search_client=search_client,
        max_results=settings.verification_search_limit,
    )
    structured_client = build_structured_llm_client(
        settings,
        model=settings.verification_model,
    )
    verifier = LlmClaimVerifier(client=structured_client)
    return VerificationPipeline(
        evidence_collector=evidence_collector,
        verifier=verifier,
    )
