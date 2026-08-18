from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException

from reelagent.config import get_settings
from reelagent.persistence import create_database_engine, create_session_factory
from reelagent.topics.service import TopicDiscoveryService

app = FastAPI(title="ReelAgent", version="0.1.0")


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@lru_cache(maxsize=1)
def get_topic_discovery_service() -> TopicDiscoveryService:
    settings = get_settings()
    if settings.database_url is None:
        raise HTTPException(status_code=503, detail="DATABASE_URL is not configured")

    engine = create_database_engine(settings.database_url)
    return TopicDiscoveryService(
        settings=settings,
        session_factory=create_session_factory(engine),
    )


@app.post("/topics/discover", tags=["topics"])
async def discover_topics(
    service: Annotated[TopicDiscoveryService, Depends(get_topic_discovery_service)],
) -> dict[str, object]:
    result = await service.run()
    return {
        "discovered_count": result.discovered_count,
        "persisted_count": result.persisted_count,
        "candidates": [
            {
                "title": candidate.title,
                "source_kind": candidate.source_kind,
                "external_id": candidate.external_id,
                "points": candidate.points,
                "comment_count": candidate.comment_count,
                "discovery_method": candidate.discovery_method,
                "matched_topic_group": candidate.matched_topic_group,
                "matched_query": candidate.matched_query,
            }
            for candidate in result.candidates
        ],
    }
