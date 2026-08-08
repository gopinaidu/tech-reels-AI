from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, HttpUrl, field_validator


class SourceKind(StrEnum):
    OFFICIAL = "official"
    GITHUB = "github"
    HACKER_NEWS = "hacker_news"
    COMMUNITY = "community"
    RESEARCH = "research"
    ENGINEERING_BLOG = "engineering_blog"


class SourceEvidence(BaseModel, frozen=True):
    source_name: str = Field(min_length=1)
    source_kind: SourceKind
    url: HttpUrl
    external_id: str | None = None
    published_at: datetime | None = None

    @field_validator("published_at")
    @classmethod
    def published_at_must_be_timezone_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("published_at must be timezone-aware")
        return value


class TopicCandidate(BaseModel, frozen=True):
    title: str = Field(min_length=1, max_length=300)
    summary: str = Field(min_length=1, max_length=2_000)
    discovered_at: datetime
    source: SourceEvidence

    @field_validator("discovered_at")
    @classmethod
    def discovered_at_must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("discovered_at must be timezone-aware")
        return value


class DiscoveryQuery(BaseModel, frozen=True):
    limit: int = Field(default=20, ge=1, le=100)
    since: datetime | None = None

    @field_validator("since")
    @classmethod
    def since_must_be_timezone_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("since must be timezone-aware")
        return value
