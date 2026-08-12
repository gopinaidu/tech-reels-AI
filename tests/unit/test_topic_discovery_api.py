from fastapi.testclient import TestClient

from reelagent.app import app, get_topic_discovery_service
from reelagent.topics.service import DiscoveryCandidateSummary, DiscoveryRunResult


class FakeDiscoveryService:
    async def run(self) -> DiscoveryRunResult:
        return DiscoveryRunResult(
            discovered_count=1,
            persisted_count=1,
            candidates=[
                DiscoveryCandidateSummary(
                    title="Kafka performance change",
                    source_kind="hacker_news",
                    external_id="42",
                    points=81,
                    comment_count=23,
                    discovery_method="targeted_search",
                    matched_topic_group="streaming",
                    matched_query="Kafka",
                )
            ],
        )


def test_discover_topics_returns_operator_summary() -> None:
    app.dependency_overrides[get_topic_discovery_service] = lambda: FakeDiscoveryService()
    try:
        response = TestClient(app).post("/topics/discover")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "discovered_count": 1,
        "persisted_count": 1,
        "candidates": [
            {
                "title": "Kafka performance change",
                "source_kind": "hacker_news",
                "external_id": "42",
                "points": 81,
                "comment_count": 23,
                "discovery_method": "targeted_search",
                "matched_topic_group": "streaming",
                "matched_query": "Kafka",
            }
        ],
    }
