"""SQLAlchemy persistence models and repository for topic discovery."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, select
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from reelagent.persistence import Base
from reelagent.topics.models import SourceEvidence, SourceKind, TopicCandidate


class TopicCandidateRow(Base):
    __tablename__ = "topic_candidate"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(300))
    summary: Mapped[str] = mapped_column(Text)
    normalized_title: Mapped[str] = mapped_column(String(300), index=True)
    dedupe_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    sources: Mapped[list[TopicSourceRow]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )


class TopicSourceRow(Base):
    __tablename__ = "topic_source"
    __table_args__ = (
        UniqueConstraint("source_kind", "external_id", name="uq_topic_source_external"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    topic_candidate_id: Mapped[UUID] = mapped_column(
        ForeignKey("topic_candidate.id", ondelete="CASCADE"), index=True
    )
    source_name: Mapped[str] = mapped_column(String(200))
    source_kind: Mapped[str] = mapped_column(String(50))
    url: Mapped[str] = mapped_column(Text)
    external_id: Mapped[str | None] = mapped_column(String(300), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    candidate: Mapped[TopicCandidateRow] = relationship(back_populates="sources")


def normalize_title(title: str) -> str:
    """Normalize a title for deterministic first-pass deduplication."""

    lowered = title.casefold().strip()
    return re.sub(r"\s+", " ", lowered)


def build_dedupe_key(candidate: TopicCandidate) -> str:
    """Build a stable MVP dedupe key without requiring embeddings."""

    if candidate.source.external_id:
        identity = f"{candidate.source.source_kind}:{candidate.source.external_id}"
    else:
        identity = normalize_title(candidate.title)
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


class SqlAlchemyTopicCandidateRepository:
    """Store and retrieve topic candidates while preserving source provenance."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, candidate: TopicCandidate) -> TopicCandidateRow:
        dedupe_key = build_dedupe_key(candidate)
        existing = self._session.scalar(
            select(TopicCandidateRow).where(TopicCandidateRow.dedupe_key == dedupe_key)
        )
        if existing is not None:
            self._attach_source_if_missing(existing, candidate)
            return existing

        row = TopicCandidateRow(
            title=candidate.title,
            summary=candidate.summary,
            normalized_title=normalize_title(candidate.title),
            dedupe_key=dedupe_key,
            discovered_at=candidate.discovered_at,
        )
        row.sources.append(self._to_source_row(candidate))
        self._session.add(row)
        self._session.flush()
        return row

    def get_by_dedupe_key(self, dedupe_key: str) -> TopicCandidateRow | None:
        return self._session.scalar(
            select(TopicCandidateRow).where(TopicCandidateRow.dedupe_key == dedupe_key)
        )

    def _attach_source_if_missing(
        self, row: TopicCandidateRow, candidate: TopicCandidate
    ) -> None:
        source = candidate.source
        identity = (source.source_kind.value, source.external_id, str(source.url))
        for existing in row.sources:
            if (existing.source_kind, existing.external_id, existing.url) == identity:
                return
        row.sources.append(self._to_source_row(candidate))

    @staticmethod
    def _to_source_row(candidate: TopicCandidate) -> TopicSourceRow:
        source: SourceEvidence = candidate.source
        return TopicSourceRow(
            source_name=source.source_name,
            source_kind=source.source_kind.value,
            url=str(source.url),
            external_id=source.external_id,
            published_at=source.published_at,
            discovered_at=candidate.discovered_at,
        )


__all__ = [
    "SqlAlchemyTopicCandidateRepository",
    "TopicCandidateRow",
    "TopicSourceRow",
    "build_dedupe_key",
    "normalize_title",
]
