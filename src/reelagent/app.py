from fastapi import FastAPI, HTTPException

from reelagent.config import get_settings
from reelagent.persistence import create_database_engine, create_session_factory
from reelagent.topics.service import TopicDiscoveryService

app = FastAPI(title="ReelAgent", version="0.1.0")


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/topics/discover", tags=["topics"])
async def discover_topics() -> dict[str, object]:
    settings = get_settings()
    if settings.database_url is None:
        raise HTTPException(status_code=503, detail="DATABASE_URL is not configured")

    engine = create_database_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    service = TopicDiscoveryService(settings=settings, session_factory=session_factory)
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
