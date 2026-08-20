from __future__ import annotations

from reelagent.config import Settings
from reelagent.intelligence.llm_runtime import _has_secret, build_structured_llm_client
from reelagent.verification.adapters import (
    AuthoritativeSearchEvidenceCollector,
    BraveVerificationSearchClient,
    LlmClaimVerifier,
    SerperVerificationSearchClient,
    VerificationSearchClient,
)
from reelagent.verification.pipeline import VerificationPipeline


class VerificationRuntimeConfigurationError(RuntimeError):
    """Raised when verification runtime dependencies are not configured."""


def build_verification_pipeline(settings: Settings) -> VerificationPipeline:
    """Build the concrete verification pipeline used by the application runtime."""

    structured_client = build_structured_llm_client(
        settings,
        model=settings.verification_model,
    )

    search_client: VerificationSearchClient
    if settings.verification_search_provider == "brave":
        if not _has_secret(settings.brave_search_api_key):
            raise VerificationRuntimeConfigurationError(
                "BRAVE_SEARCH_API_KEY is required when "
                "VERIFICATION_SEARCH_PROVIDER=brave"
            )
        search_client = BraveVerificationSearchClient(api_key=settings.brave_search_api_key)
    else:
        if not _has_secret(settings.serper_api_key):
            raise VerificationRuntimeConfigurationError(
                "SERPER_API_KEY is required when "
                "VERIFICATION_SEARCH_PROVIDER=serper"
            )
        search_client = SerperVerificationSearchClient(
            api_key=settings.serper_api_key,
            llm_client=structured_client,
        )

    evidence_collector = AuthoritativeSearchEvidenceCollector(
        search_client=search_client,
        max_results=settings.verification_search_limit,
    )
    verifier = LlmClaimVerifier(client=structured_client)
    return VerificationPipeline(
        evidence_collector=evidence_collector,
        verifier=verifier,
    )
