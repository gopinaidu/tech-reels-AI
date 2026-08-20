import asyncio

from pydantic import HttpUrl

from reelagent.topics.models import SourceKind
from reelagent.verification.adapters.search import (
    AuthoritativeSearchEvidenceCollector,
    VerificationSearchHit,
)
from reelagent.verification.models import ClaimVerificationRequest


class _SearchClient:
    async def search(self, query: str, *, limit: int) -> tuple[VerificationSearchHit, ...]:
        return (
            VerificationSearchHit(
                title="PostgreSQL documentation",
                url=HttpUrl("https://www.postgresql.org/docs/current/sql-select.html"),
                snippet="x" * 2_000,
                source_kind=SourceKind.OFFICIAL,
            ),
        )


def test_collector_accepts_maximum_evidence_summary() -> None:
    collector = AuthoritativeSearchEvidenceCollector(search_client=_SearchClient())
    request = ClaimVerificationRequest(
        claim_index=0,
        claim_text="PostgreSQL supports SKIP LOCKED.",
        introducing_evidence_ids=("cli:manual-claim",),
    )

    evidence = asyncio.run(collector.collect(request))

    assert len(evidence) == 1
    assert len(evidence[0].summary) == 2_000
