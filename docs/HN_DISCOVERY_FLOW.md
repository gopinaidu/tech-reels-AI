# Hacker News Discovery Flow

## Goal

Keep Hacker News discovery broad enough to detect unexpected technical trends while narrowing the candidate pool before scoring so ReelAgent does not spend downstream work on obviously irrelevant topics.

## Dual-lane flow

```text
                         Hacker News
                              |
              +---------------+---------------+
              |                               |
       Trending / wildcard              Targeted search
       Firebase topstories              HN Algolia Search
              |                               |
       top recent stories          configured topic groups
              |                    freshness + low signal gate
              +---------------+---------------+
                              |
                      TopicCandidate pool
                              |
                         deduplicate
                              |
                 bounded targeted candidate pool
                              |
                         persistence
                              |
                     scoring / selection
```

### Trending lane

The trending lane deliberately avoids technical keyword filtering. Its purpose is to preserve serendipity and allow new technologies or unexpected engineering topics to enter the system even when they are not present in configured search terms.

The lane captures source-native Hacker News metadata including author, points, comment count, article URL, current HN rank, and `discovery_method=trending`.

### Targeted lane

The targeted lane uses the Hacker News Algolia Search API with configurable technical topic groups. The default groups cover AI, backend/distributed systems, data stores, streaming, programming languages, cloud, and architecture/reliability.

Each targeted candidate records the matched topic group and exact query so downstream scoring and analytics can explain why it entered the pool.

Targeted search applies a freshness window and a deliberately low engagement gate. A story is admitted when it meets either the minimum points threshold or the minimum comment threshold. Engagement is not a final quality judgment; it only prevents very low-signal matches from flooding the pool.

### Bounds

The targeted search path is bounded in four ways:

1. result count per configured query;
2. maximum targeted candidates retained for the run;
3. maximum concurrent targeted requests;
4. freshness window.

These controls prevent configuration growth from causing uncontrolled fan-out or an excessively large scoring pool.

## Configuration

Current settings are defined in `reelagent.config.Settings` and may be overridden by environment configuration:

- `discovery_topic_groups`
- `hn_trending_limit`
- `hn_targeted_limit_per_query`
- `hn_targeted_total_limit`
- `hn_targeted_max_concurrency`
- `hn_targeted_min_points`
- `hn_targeted_min_comments`
- `hn_targeted_freshness_days`

Topic groups are configuration rather than hard-coded eligibility rules. They can evolve as the channel evolves without changing the scoring architecture.

## Source metadata

`SourceEvidence.metadata` holds provider-specific discovery signals. For Hacker News, fields may include:

```text
author
points
comment_count
article_url
hn_rank
discovery_method
matched_topic_group
matched_query
```

The metadata is persisted as JSON on `topic_source`. Core domain fields remain provider-neutral.

## Deduplication

Trending and targeted results are merged using the existing deterministic normalized-title dedupe key. If the same title appears in both lanes, the trending candidate is retained and the duplicate targeted observation is not added to the in-memory pool. Cross-source provenance persistence remains handled by the repository layer.

Semantic clustering of differently worded stories is intentionally deferred.

## Downstream boundary

Discovery only answers whether a topic is worth considering. It does not decide that a topic belongs in the final content plan and it does not treat Hacker News claims as verified facts.

The next scoring stage will evaluate audience fit, freshness, technical depth, practical value, novelty, source quality, and engagement before selecting topics for research.
