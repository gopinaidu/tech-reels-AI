from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Protocol
from urllib.parse import urlparse

from pydantic import BaseModel, Field, HttpUrl

from reelagent.intelligence.models import Evidence, EvidenceRole
from reelagent.topics.models import SourceEvidence, SourceKind
from reelagent.verification.models import ClaimVerificationRequest


class VerificationSearchHit(BaseModel, frozen=True):
    title: str = Field(min_length=1, max_length=300)
    url: HttpUrl
    snippet: str = Field(min_length=1, max_length=4_000)
    source_kind: SourceKind
    published_at: datetime | None = None


class VerificationSearchClient(Protocol):
    async def search(self, query: str, *, limit: int) -> tuple[VerificationSearchHit, ...]: ...


class AuthoritativeSearchEvidenceCollector:
    """Collect a bounded set of non-community sources for one factual claim."""

    def __init__(self, *, search_client: VerificationSearchClient, max_results: int = 5) -> None:
        if max_results < 1 or max_results > 10:
            raise ValueError("max_results must be between 1 and 10")
        self._search_client = search_client
        self._max_results = max_results

    async def collect(self, request: ClaimVerificationRequest) -> tuple[Evidence, ...]:
        hits = await self._search_client.search(request.claim_text, limit=self._max_results)
        evidence: list[Evidence] = []
        seen_urls: set[str] = set()
        for hit in hits[: self._max_results]:
            if hit.source_kind in {SourceKind.HACKER_NEWS, SourceKind.COMMUNITY}:
                continue
            url = str(hit.url)
            if url in seen_urls:
                continue
            seen_urls.add(url)
            evidence.append(_hit_to_evidence(hit, len(evidence)))
        return tuple(evidence)


def _hit_to_evidence(hit: VerificationSearchHit, index: int) -> Evidence:
    host = urlparse(str(hit.url)).hostname or "unknown-source"
    source = SourceEvidence(
        source_name=host,
        source_kind=hit.source_kind,
        url=hit.url,
        published_at=hit.published_at,
        metadata={"search_result_title": hit.title},
    )
    return Evidence(
        evidence_id=f"verification-search:{index}:{host}",
        source=source,
        roles=frozenset({EvidenceRole.VERIFICATION}),
        summary=hit.snippet,
        retrieved_at=datetime.now(UTC),
        instruction_like_content_detected=_looks_instruction_like(hit.snippet),
    )


def _looks_instruction_like(text: str) -> bool:
    lowered = text.lower()
    markers = (
        "ignore previous instructions",
        "ignore all instructions",
        "system prompt",
        "developer message",
        "follow these instructions",
    )
    return any(marker in lowered for marker in markers)
