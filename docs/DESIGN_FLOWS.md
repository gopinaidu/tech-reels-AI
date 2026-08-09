# ReelAgent Design Flows

## Purpose

This document is the living map of ReelAgent's major product and engineering flows.

It exists so important workflow design does not live only in chat, pull request discussions, or code. Each material stage should be documented here at the level of responsibilities, boundaries, inputs/outputs, persistence, failure behavior, and downstream handoff.

Detailed architecture rules remain authoritative in `ARCHITECTURE_GUIDELINES.md`, and material choices remain authoritative in `DECISIONS.md`. This document explains how those decisions fit together in actual runtime flows.

## How to Maintain This Document

When a feature introduces or materially changes a workflow stage:

1. Update the relevant flow here in the same pull request.
2. Keep the flow provider-neutral unless provider behavior is itself material.
3. Link to deeper decision records rather than duplicating long decision rationale.
4. Record important boundaries, failure behavior, and persistence points.
5. Prefer simple deterministic processing before introducing additional LLM or infrastructure dependencies.

The goal is not exhaustive implementation documentation. The goal is a durable architecture map that makes the system understandable without reading every source file.

---

# 1. End-to-End Content Production Flow

```text
Discovery Sources
      ↓
Source Adapters
      ↓
Normalized Topic Candidates
      ↓
Deduplication / Topic Clustering
      ↓
Persistence
      ↓
Scoring / Selection
      ↓
Research / Claim Verification
      ↓
Script Generation
      ↓
Media / Rendering
      ↓
Pre-Publish Safety Review
      ↓
Immutable Publication Package
      ↓
Artifact-Bound Human Approval
      ↓
Publishing
```

Each stage has a different responsibility:

- **Discovery:** What is happening?
- **Scoring / selection:** Is this worth making a reel about?
- **Research / verification:** What is actually true?
- **Script generation:** How should we explain it?
- **Rendering:** What exact audience-visible artifact will be produced?
- **Safety review:** Is the exact publication package safe and supportable?
- **Approval:** Has the owner approved this exact immutable artifact?
- **Publishing:** Is the outgoing artifact exactly the approved artifact, and can it be published idempotently?

A stage must not silently absorb the responsibilities of a later stage. In particular, discovery content is not trusted as fact and cannot directly become publishable content.

---

# 2. Topic Discovery Flow

## Goal

Collect potentially useful software-engineering topics from multiple compliant sources while keeping source-specific behavior outside the core domain.

## Flow

```text
Hacker News / GitHub / arXiv / Official Feeds / Engineering Blogs
                            ↓
                     Source Adapters
                            ↓
                     TopicCandidate
                            ↓
                       Normalize
                            ↓
                     Deduplicate
                            ↓
                        Persist
                            ↓
                Score / Rank / Select
```

## 2.1 Source Adapter Boundary

Every discovery source has its own payload shape, API semantics, identifiers, timestamps, and reliability characteristics.

Adapters translate source-specific data into a provider-neutral `TopicCandidate` representation before the rest of ReelAgent sees it.

Conceptually, a candidate contains fields such as:

```text
TopicCandidate
- title
- summary
- canonical_url
- source_type
- source_name
- external_id
- published_at
- discovered_at
- tags
- source/provenance metadata
```

The exact schema may evolve, but downstream scoring and research code should not need to understand Hacker News JSON, GitHub release payloads, RSS XML, or arXiv Atom directly.

## 2.2 Normalization

Normalization creates consistent internal values across providers.

Examples:

- normalize canonical URLs where safe
- normalize timestamps to one timezone/representation
- trim or bound source text
- normalize source names and identifiers
- preserve the original source/provenance reference
- reject malformed records that cannot satisfy the domain contract

Normalization must not invent missing factual content.

## 2.3 Deduplication and Topic Clustering

The same underlying topic may appear across several sources.

Example:

```text
Hacker News:  "Kafka introduces new queue semantics"
GitHub:       "Apache Kafka 4.x released"
Vendor blog:  "What's new in Kafka 4.x"
Official:     "Kafka 4.x release notes"

                    ↓

       One logical topic candidate / cluster
```

For the MVP, prefer deterministic and explainable deduplication before adding embeddings or a vector database.

Initial signals can include:

- exact source + external ID
- canonical URL equality
- normalized URL equality
- normalized title equality
- bounded deterministic title similarity
- stable dedupe/hash keys where appropriate

When multiple sources refer to the same topic, do not simply discard the extra observations. Preserve source provenance so later scoring and research can see that the topic has multiple signals.

LLM-based semantic clustering may be considered later if deterministic methods produce unacceptable duplicate rates.

## 2.4 Persistence

Discovery results must survive process restarts and repeated discovery runs.

Persistence allows ReelAgent to know that a topic was already:

- discovered
- scored
- rejected
- selected
- researched
- converted into a reel

This prevents repeated API work and repeated paid LLM work.

A likely conceptual model is:

```text
topic_candidate
---------------
id
title
canonical_url
published_at
discovered_at
status
dedupe_key
signal_score

candidate_source
----------------
candidate_id
source_name
source_url
external_id
source_metadata
```

This is conceptual design, not a committed physical schema. The actual schema should be recorded in `DECISIONS.md` when chosen.

## 2.5 Prepare for Scoring / Selection

Discovery should produce a candidate pool, not automatically generate reels.

Scoring is a separate stage that may evaluate dimensions such as:

- audience fit
- freshness
- technical depth
- practical usefulness
- source credibility
- novelty
- fit for one of ReelAgent's content formats
- strength of multi-source interest signals
- proprietary-information risk
- expected research/generation cost

Example:

```text
Candidate: Kafka new queue semantics
Freshness:        high
Audience fit:     high
Technical depth:  high
Source quality:   high
Novelty:          high

                 ↓
             SELECT
```

The first scoring implementation should remain simple and explainable. Use deterministic rules where sufficient and reserve LLM judgment for dimensions that genuinely require semantic evaluation.

## 2.6 Discovery Is Not Verification

A high-ranking discovery item means only that the topic may be worth investigating.

Community posts, headlines, blog posts, and source descriptions must not become factual claims merely because they ranked highly.

The downstream research stage must independently verify material claims using the evidence hierarchy in `AGENTS.md` and the retrieved-content protections in D-023.

## 2.7 Failure Behavior

Discovery failures should be isolated by source when possible.

Examples:

- Hacker News unavailable should not prevent approved official feeds from running.
- Malformed individual items should be skipped or rejected without corrupting other candidates.
- External requests must be bounded.
- Retries must be bounded and must respect provider limits.
- Successfully normalized/persisted candidates should not be lost because another source fails later in the run.

## 2.8 Current MVP Increment

The first vertical slice is intentionally narrow:

```text
Hacker News
    ↓
HackerNewsDiscoverySource
    ↓
TopicCandidate
    ↓
Normalization boundary
    ↓
Deterministic dedupe
    ↓
Persistence boundary
    ↓
Tests
```

Explicitly deferred from this increment:

- embeddings / vector database
- LLM semantic clustering
- broad multi-source orchestration
- complex ranking models
- automated research
- publishing concerns

The purpose is to prove a small, reliable discovery path before scaling the number of sources or adding model-driven decisions.

---

# 3. Scoring / Topic Selection Flow

Status: **Design outline — implementation not started**

```text
Persisted Topic Candidates
          ↓
Eligibility Filters
          ↓
Deterministic Signals
          ↓
Optional Semantic Judgment
          ↓
Composite Score + Reasons
          ↓
Select / Hold / Reject
```

The scoring stage must retain enough explanation to answer why a topic was selected or rejected. Exact dimensions, weights, thresholds, and LLM involvement will be finalized when this stage is implemented.

---

# 4. Research / Verification Flow

Status: **Design outline — implementation not started**

```text
Selected Topic
      ↓
Research Plan
      ↓
Authoritative Sources
      ↓
Claim Extraction
      ↓
Independent Verification
      ↓
Verified Claim Set + Provenance
      ↓
Script Generation
```

Key rule: discovery sources can identify an interesting topic, but material technical claims must be verified independently before they become script inputs.

See D-023 and the evidence hierarchy in `AGENTS.md`.

---

# 5. Script-to-Publish Flow

Status: **High-level architecture already governed; implementation not started**

```text
Verified Claims
      ↓
Script Generation
      ↓
Scene / Media Generation
      ↓
Render
      ↓
Pre-Publish Safety Review
      ↓
Immutable Publication Package + Hash
      ↓
Owner Approval Bound to Hash
      ↓
Publish-time Hash Verification
      ↓
Idempotent Publisher Adapter
```

The human approval is bound to the exact publication artifact/package, not to a mutable reel-level boolean. Any audience-visible content change after approval invalidates that approval.

See D-010, D-013, and D-024.

---

# 6. Future Flow Sections

Add sections here as implementation reaches them, including:

- source scheduling and discovery-run orchestration
- topic lifecycle/status transitions
- scoring and selection
- research and claim verification
- prompt/version management
- script revision loops
- narration and media generation
- rendering
- publication package construction
- pre-publish safety review
- artifact-bound approval
- publishing and retry/idempotency
- observability and cost accounting

Each new section should answer:

1. What is this stage responsible for?
2. What is explicitly outside its responsibility?
3. What typed input does it consume?
4. What typed output does it produce?
5. What gets persisted?
6. What can fail?
7. How is retry/resumption handled?
8. What downstream stage receives the output?
9. Which decisions/policies govern it?
