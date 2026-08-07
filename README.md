# ReelAgent

ReelAgent is an AI-assisted content production system for creating short-form software engineering content for senior developers, tech leads, and architects.

The system will discover relevant software-engineering trends, research them against authoritative sources, generate structured scripts, verify the material claims those scripts make, convert them into video scenes, render reels, present immutable publication artifacts for human approval, publish approved content, and analyze performance.

## Current Project Status

**Phase:** Pre-code project foundation  
**Coding status:** NOT STARTED  
**Current gate:** Core engineering standards and agent instructions must be reviewed and approved before implementation begins.

## Product Objective

Build a dependable personal content-production system capable of producing approximately three high-quality technical reels per week with limited manual effort.

The MVP is not intended to be a multi-tenant SaaS platform.

## Target Audience

- Senior software engineers
- Tech leads
- Solution/software architects
- Engineering leaders who remain close to implementation and architecture

Content should avoid unnecessary beginner-level explanations. Foundational concepts should quickly lead to senior-level architecture, performance, operational, or design insight.

## Content Strategy

Working guideline:

- Approximately 60% trending/current software developments
- Approximately 40% evergreen architecture and production lessons

This is not a hard quota. Content quality, freshness, technical significance, and audience relevance take priority.

## Content Pillars

1. AI & Emerging Software Technology
2. Architecture & Distributed Systems
3. Languages & Performance
4. Cloud & Platform Engineering
5. Data & Databases
6. OMS & Commerce Technology
   - IBM Sterling OMS
   - Distributed order management
   - Inventory and availability
   - Sourcing and fulfillment
   - Payments and fraud
   - Returns
   - Order orchestration trends

## Initial Reel Formats

### What's New?
What changed, why it matters, and what a senior engineer or architect should do with the information.

### 60-Second Architecture
Problem, architecture, tradeoff, recommendation.

### Production Reality
What looks correct on paper, what fails in production, why, and the better design or operational approach.

## Initial Reel Queue

1. IBM Sterling OMS + Agentic AI + MCP
2. Redis TTL is a Business Decision
3. Kafka Share Groups / Kafka Queues

## MVP Publishing Platform

The first automated publishing integration will target **YouTube Shorts**.

Rendering and publishing should avoid unnecessary coupling to YouTube so additional destinations can be added later. Expected future distribution targets include LinkedIn and Instagram Reels, subject to API access and platform policies at implementation time.

Two platform realities must be confirmed before the publish adapter is designed, rather than discovered during implementation:

1. The current requirements and restrictions for API-based uploads — including whether an unaudited API client's uploads are constrained in visibility, which would change what "published" means for the MVP and require the workflow to represent a published-but-private state.
2. The platform's disclosure requirements for synthetic or AI-assisted content, including synthetic or cloned narration, and where that disclosure has to be applied.

See `DECISIONS.md` D-020 and D-022.

For publishing side-effect safety, provider isolation, approval binding, and idempotency requirements, see `ARCHITECTURE_GUIDELINES.md` and `CODE_READINESS.md`.

## Discovery Strategy

Trend discovery is a first-class capability. ReelAgent must not rely on a generic "scrape the web" strategy.

Initial source families:

1. **Official project/vendor documentation and release notes** — Python, OpenJDK/Java, Apache Kafka, PostgreSQL, Redis, Kubernetes, IBM Sterling, and relevant AI/software tooling.
2. **GitHub** — releases, repository activity, and selected trending/open-source projects.
3. **Hacker News** — primarily a discovery and popularity signal.
4. **Reddit and similar engineering communities** — discovery, practitioner discussion, and trend signals; not sole technical authority.
5. **Research sources** — arXiv and other appropriate primary research sources for emerging software/AI topics.
6. **Selected engineering blogs** — high-quality vendor, platform, and technology-company engineering publications.

Preferred ingestion order:

**Official API → RSS/Atom/feed → supported public endpoint → scraping only when necessary and permitted.**

Each source adapter must document its access method and relevant usage/ToS constraints before implementation.

Community popularity does not establish technical truth. Material technical claims should be verified through authoritative sources.

For source hierarchy, adapter design, provenance, and research boundaries, see `ARCHITECTURE_GUIDELINES.md` and `AGENTS.md`.

## Freshness and Trend Quality

Trending content must be technically relevant and genuinely current.

Topic candidates should retain enough metadata to reason about:

- Original publication/release date
- Discovery date
- Last verification date
- Trend window
- Source authority
- Trend velocity
- Technical significance
- Audience relevance
- Creator/domain expertise
- Novelty relative to previously covered topics

A technically correct but stale development should not be presented as breaking or new.

For detailed provenance and scoring design, see `ARCHITECTURE_GUIDELINES.md`.

## Topic Deduplication and Coverage Memory

ReelAgent must remember what has already been discovered, rejected, approved, and published.

Discovery should prevent accidental repeated coverage through canonical topic identification/fingerprinting, duplicate detection, similarity checks, publication history, and recency windows.

The same technology may legitimately be covered again when materially new information appears.

For persistence and deduplication design, see `ARCHITECTURE_GUIDELINES.md`.

## Technical Credibility, Provenance, and Attribution

Technical credibility is a core product requirement.

Every material technical claim should be traceable to a reliable source or clearly identified as interpretation, recommendation, experience, or opinion.

ReelAgent should distinguish:

- Discovery source
- Verification source
- Inspiration source
- Required attribution

Finding an official source that confirms a claim must not erase the provenance of the source that originally introduced the idea.

ReelAgent should give appropriate credit when a reel is materially inspired by another creator, researcher, engineering blog, paper, or original analysis.

The system must not present another author's novel analysis as original work or reproduce substantial copyrighted expression unnecessarily.

For provenance models and research rules, see `ARCHITECTURE_GUIDELINES.md` and `AGENTS.md`.

## Narration Strategy

Narration quality affects credibility and channel identity.

The architecture should support replaceable narration/TTS providers rather than tightly coupling ReelAgent to one vendor.

During early proof-of-concept work, a high-quality synthetic voice is acceptable. Before regular publishing, compare:

- The project owner's natural recorded voice
- An authorized clone of the project owner's voice, if desired and supported
- A premium synthetic voice

The final choice should prioritize credibility, consistency, quality, cost, and production effort.

Provider selection will be recorded in `DECISIONS.md`.

For provider abstraction guidance, see `ARCHITECTURE_GUIDELINES.md`.

## Artifact-Bound Human Approval

Human approval applies to a **specific immutable publication artifact/package**, not to a mutable reel record.

The approved package should represent the exact publishable content, including the final video and the publication metadata that materially affects what the audience will see.

Approval must be associated with a stable artifact/content hash or equivalent immutable identity.

Any content-changing regeneration or edit after approval invalidates the prior approval. This includes changes to script, scenes, narration, captions, visual assets, final video, title, description, or other approved publication metadata.

The publish operation must verify that the artifact being published is exactly the artifact that was approved.

A newly produced artifact must not inherit approval merely because it belongs to the same reel.

For detailed artifact/versioning and publication design, see `ARCHITECTURE_GUIDELINES.md`. For mandatory release enforcement, see `CODE_READINESS.md`.

## Pre-Publish Safety and Proprietary-Information Gate

Before human approval, the final publication package must pass a pre-publish review.

At minimum, review must confirm:

- Material technical claims are verified or correctly characterized.
- Required attribution is present.
- Unsupported benchmarks are not presented as fact.
- No credentials, tokens, secrets, or private data are exposed.
- No employer/client identity is exposed unintentionally.
- No non-public internal system names are exposed.
- No proprietary architecture, implementation detail, or confidential data is exposed.
- Production stories are sufficiently anonymized.
- Sensitive business metrics are removed or explicitly approved for publication.
- Title, description, captions, and other publication metadata are included in the review.

Public knowledge about IBM Sterling OMS or another vendor is not the same as permission to disclose a non-public employer/client implementation of that product.

For detailed agent behavior, see `AGENTS.md`. For the mandatory publishing gate, see `CODE_READINESS.md`.

## Resumability and Idempotency

Research, LLM generation, narration, and rendering can incur time and monetary cost. Successful expensive work must not be repeated simply because a later stage fails.

Pipeline stages must:

- Persist meaningful outputs
- Resume from appropriate checkpoints
- Retry only when safe
- Avoid duplicate external side effects
- Make workflow state explicit

A failed render should not automatically repeat successful research, scripting, and verification.

For workflow persistence, retry behavior, idempotency, and failure-recovery design, see `ARCHITECTURE_GUIDELINES.md`. For release-readiness requirements, see `CODE_READINESS.md`.

## Prompts as Versioned Product Artifacts

Prompts are part of ReelAgent's product behavior and must be treated as source-controlled artifacts.

Important prompts should:

- Live in dedicated version-controlled files
- Have stable names/identifiers
- Be reviewable through source-control history
- Avoid being scattered as large inline strings throughout application logic
- Have their version, and a content hash of the prompt actually sent, associated with generated outputs

For prompt-management rules, see `AGENTS.md` and `ARCHITECTURE_GUIDELINES.md`.

## Source Control Before Application Code

The Git repository and ignore rules must exist **before application code, local credentials, OAuth tokens, generated media, or other sensitive/runtime artifacts are introduced**.

After the documentation gate is approved, the first engineering setup steps are:

1. Initialize Git.
2. Add and review `.gitignore`.
3. Commit the approved governance/project documents.
4. Add `.env.example` containing names/placeholders only.
5. Configure the local secrets mechanism.
6. Only then begin application implementation.

Sensitive local files, OAuth tokens, generated media, local databases, virtual environments, logs, and IDE/runtime artifacts must not be committed.

For coding-agent source-control rules, see `AGENTS.md`. The accepted secrets strategy is recorded in `DECISIONS.md`.

## Secrets and Configuration Strategy

For the MVP:

- Local development secrets are supplied through environment variables, optionally loaded from a local `.env` file.
- `.env` and credential/token files are ignored by Git.
- `.env.example` may be committed but must contain placeholders/names only.
- Application configuration is loaded through one centralized typed configuration mechanism.
- Components should receive only the configuration/credentials they require.
- Hosted environments should initially use platform-managed environment variables/secrets.
- A dedicated cloud secret manager should be introduced only when justified by deployment/security needs.

Publishing credentials should be isolated from research/generation components according to least-privilege principles.

For credential isolation and provider-boundary design, see `ARCHITECTURE_GUIDELINES.md`. For secret-related readiness checks, see `CODE_READINESS.md`.

## Cost Model and Guardrails

Cost is a first-class engineering metric.

ReelAgent should estimate or record costs attributable to research/search calls, LLM classification/reasoning, script generation, fact checking, TTS, rendering, storage/bandwidth, and paid publishing-related services if any.

Useful measures should eventually include cost per generated reel, cost per published reel, monthly production cost, and expensive retry cost.

Paid API usage must have budget guardrails with concrete thresholds. The values are not yet set — see `DECISIONS.md` D-019, which blocks Release Ready until it is resolved.

For cost-aware architecture, see `ARCHITECTURE_GUIDELINES.md`. For readiness requirements related to paid APIs, see `CODE_READINESS.md`.

## MVP Capabilities

The MVP should:

1. Discover reel-topic candidates from approved sources.
2. Store source provenance and freshness metadata.
3. Detect duplicate/recently-covered topics.
4. Rank and classify candidates.
5. Research technical claims using reliable sources.
6. Generate structured scripts.
7. Verify material technical claims.
8. Generate structured video scene definitions.
9. Generate narration and captions. Whether captions are burned into the video, supplied as a sidecar file, or both is a rendering decision that must be recorded before scene work begins.
10. Render a vertical short-form video.
11. Assemble an immutable publication artifact/package.
12. Run the pre-publish safety/proprietary-information gate.
13. Present the exact publication artifact for human approval.
14. Publish only the exact approved artifact to YouTube Shorts.
15. Store publication identifiers and basic performance metrics.
16. Preserve resumable workflow state.
17. Track meaningful per-stage/per-reel cost information.

## Non-Goals for MVP

Do not build these unless explicitly approved:

- Multi-tenant SaaS
- Billing
- Mobile application
- Fully autonomous publishing
- Automatic comment responses
- Custom model training
- Complex agent frameworks without demonstrated need
- Kafka-based internal messaging without demonstrated need
- Multiple social-platform publishing integrations at launch
- Advanced autonomous analytics
- Microservice decomposition without demonstrated need

## Recommended Initial Technology Direction

Expected starting direction:

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- PostgreSQL
- Docker
- Simple explicit workflow/scheduling mechanisms
- Remotion + FFmpeg for video rendering
- Lightweight approval UI

These are architectural directions, not irreversible commitments.

This direction is recorded as `DECISIONS.md` D-021. Material changes to it should follow `LLM_REVIEW_POLICY.md` and update that record.

## Core Engineering Principles

### Build the Smallest Reliable System
Do not optimize for theoretical scale before the content workflow is proven. See `ARCHITECTURE_GUIDELINES.md`.

### Human Approval Is Artifact-Specific
Approval belongs to the exact immutable publication artifact. Changed content requires new approval. See `ARCHITECTURE_GUIDELINES.md` and `CODE_READINESS.md`.

### LLM Output Is Not Automatically Trusted
LLM-generated output must be validated before it controls workflow state, external side effects, or technical claims. See `AGENTS.md` and `ARCHITECTURE_GUIDELINES.md`.

### Preserve Evidence
Research, important claims, prompt versions, generation metadata, and material workflow decisions should remain traceable. See `ARCHITECTURE_GUIDELINES.md`.

### Resume Rather Than Restart
Expensive completed stages should be reusable after downstream failure. See `ARCHITECTURE_GUIDELINES.md`.

### Measure Cost
Paid model/API/rendering usage should be visible enough to understand the economics of each reel. See `ARCHITECTURE_GUIDELINES.md` and `CODE_READINESS.md`.

### Protect Proprietary Information
Production experience must be generalized/anonymized unless disclosure is explicitly safe and approved. See `AGENTS.md` and `CODE_READINESS.md`.

## Multi-LLM Architecture and Code Review

ReelAgent intentionally uses independent LLM review for material decisions. Potential reviewers include ChatGPT, Claude, Gemini, and other capable coding/reasoning models.

LLM consensus is advisory. Tests, evidence, official documentation, project constraints, and project-owner approval determine readiness.

For the complete process and reviewer prompts, see `LLM_REVIEW_POLICY.md`.

## Development and Code Readiness

A task is not complete merely because code was generated or appears to work once.

For the complete definition of ready, see `CODE_READINESS.md`.

## Instructions for AI Agents

Any AI coding or architecture agent working on ReelAgent must read the project documentation before making material changes.

Mandatory agent rules are defined in `AGENTS.md`.

## Architecture Decisions

Material product and architecture decisions must be recorded so future humans and agents do not have to reconstruct them from chat history.

The current decision log is `DECISIONS.md`.

## Working Cadence

The project is intentionally developed in small daily sessions:

1. Review previous work.
2. Select one small deliverable.
3. Implement and test.
4. Update decisions/documentation.
5. Identify the next smallest task.

Avoid accumulating multiple partially completed workstreams.

## Documentation Map

| Document | Purpose |
|---|---|
| `README.md` | Product mission, scope, MVP, and top-level principles |
| `AGENTS.md` | Mandatory behavior for AI coding/review agents |
| `CLAUDE.md` | Pointer that loads `AGENTS.md` in Claude Code sessions |
| `CODE_READINESS.md` | Quality gates and definition of ready |
| `ARCHITECTURE_GUIDELINES.md` | Detailed architecture, workflow, reliability, provenance, secrets, approval, and provider guidance |
| `LLM_REVIEW_POLICY.md` | Multi-LLM review and disagreement-resolution process |
| `DECISIONS.md` | Accepted product and architecture decisions |

## Definition of Done

A project task is complete only when:

1. Its acceptance criteria are satisfied.
2. Applicable code-readiness requirements are satisfied.
3. Required reviews are complete.
4. Material decisions/documentation are updated.
5. No unresolved blocking findings remain.

For detailed criteria, see `CODE_READINESS.md`.
