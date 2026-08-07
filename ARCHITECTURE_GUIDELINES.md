# ARCHITECTURE_GUIDELINES.md

## Architectural Style

Default to a modular monolith for the MVP.

Conceptual modules may include topics, research, scripting, verification, scenes, rendering, approvals, publishing, and analytics. These are logical modules first, not independent deployable services.

## Dependency Direction

Prefer domain/application logic isolated from infrastructure/provider adapters.

External providers should not define the core domain model.

## Provider Abstraction

Use provider abstractions where vendor change is realistic:

- LLM
- TTS/narration
- publishing platform
- object storage
- external trend/research source

Do not create abstractions only because multiple implementations are imaginable.

## Discovery Adapters

Each discovery source should document:

- Access method
- API/feed endpoint type
- Authentication if any
- Rate/usage constraints
- Relevant ToS/robots considerations
- Freshness metadata
- Source authority classification

Prefer official API, then RSS/Atom/feed, then supported public endpoint, then permitted scraping only when necessary.

Access feasibility is confirmed before a source family is treated as committed, not at adapter-implementation time. Terms, authentication requirements, and rate limits for community platforms change, and a source whose only compliant access path is unavailable is not a source. See `DECISIONS.md` D-025.

## Database and Durable State

PostgreSQL is the default system of record for MVP metadata.

Durable state may include topics, trend evidence, research sources, scripts, claims, reel versions, scene plans, render jobs, publication artifacts, approvals, publication records, and metrics.

Media files must not be stored in the relational database. For the MVP, rendered video, audio, and caption files live on the local filesystem or a mounted volume, and Postgres stores the reference: path, size, and content hash.

Object storage replaces the filesystem when hosting or durability requires it. Keep the reference behind a small abstraction so that migration does not reach into domain code. See `DECISIONS.md` D-026.

## Workflow and Resumability

Start with explicit application workflow code.

Each expensive/material stage should persist enough output/state to resume without repeating successful upstream work.

A workflow engine should only be introduced when actual needs justify it.

Do not adopt Kafka, Temporal, Celery, or similar infrastructure merely because they are familiar.

## Explicit Workflow State

Important workflow state must be explicit rather than inferred from file existence.

State lives in two places, not one.

### 1. Milestone status

One status field records the furthest milestone a reel version has reached:

DISCOVERED
→ RESEARCHED
→ SCRIPTED
→ VERIFIED
→ SCENE_PLANNED
→ RENDERED
→ PRE_PUBLISH_REVIEWED
→ AWAITING_APPROVAL
→ APPROVED
→ PUBLISHED

These additional states must also be representable:

- `REVISION_REQUESTED` — non-terminal. A later stage rejected the work and an earlier stage must run again.
- `REJECTED` — terminal. The owner declined this topic or reel permanently.
- `FAILED` — terminal. An attempt or revision limit was exhausted; owner action is required to continue.
- `SUPERSEDED` — terminal. A newer reel version replaced this one.

Milestone status must not encode in-progress work. "Currently rendering" is not a milestone.

### 2. Stage run records

Every attempt at every stage persists its own record, carrying at least: reel version, stage, attempt number, state (`RUNNING`, `SUCCEEDED`, `FAILED`), start and finish timestamps, output/artifact reference, provider/model and prompt version where applicable, error classification, and cost.

This split is what makes resumption and cost attribution possible. The milestone says where the reel is; the stage runs say what has already been paid for and may be reused.

### Backward transitions

The pipeline is not linear. At minimum these rejections need a defined path:

| Rejecting stage | Resulting status | Stage that runs again |
|---|---|---|
| Verification finds an unsupported claim | `REVISION_REQUESTED` | Scripting |
| Pre-publish gate fails | `REVISION_REQUESTED` | Scripting, or scenes/render depending on the finding |
| Owner rejects at approval | `REVISION_REQUESTED` or `REJECTED` | Owner's choice |

A backward transition creates a new attempt. It must never silently overwrite the previous one, because the rejected version is the audit evidence.

### Bounded revision loop

Revision cycles are bounded. Each cycle costs a full paid generation pass, and an unbounded verify-and-rewrite loop is two problems at once: uncontrolled cost, and a way to launder a weak claim past verification by regenerating until something passes.

- Default maximum: **two revision cycles per reel version**, then `FAILED`.
- Continuing past the limit requires an explicit, recorded owner action.
- A claim that fails verification twice should be cut from the script rather than rephrased a third time.

This bound is a project default rather than a technical constraint, and may be tuned once real rejection rates are known. See `DECISIONS.md` D-018.

## Topic Deduplication

Maintain coverage memory across discovered, rejected, approved, and published topics.

Use canonical identifiers/fingerprints and later semantic similarity where justified.

Deduplication must allow legitimate repeat coverage when materially new information exists.

## Publication Artifact and Approval Model

Approval is bound to an immutable **PublicationArtifact** (name conceptual; exact schema may evolve).

A publication artifact/package should identify the exact content intended for publication, including as appropriate:

- Final video
- Script/version lineage
- Scene plan/version lineage
- Narration/audio
- Captions/subtitles
- Visual assets that affect output
- Platform title
- Description/caption
- Other audience-visible publication metadata

The package must have a stable immutable identity, preferably a cryptographic content hash over a canonical manifest plus referenced immutable assets.

Conceptual model:

```text
Topic
  ↓
Reel
  ↓
ReelVersion
  ↓
PublicationArtifact(hash)
  ↓
PrePublishReview
  ↓
Approval(artifact_hash)
  ↓
Publication(artifact_hash, platform_publication_id)
```

Rules:

1. Approval references a specific artifact identity/hash.
2. Publish verifies the outgoing artifact identity equals the approved identity.
3. Content-changing regeneration/edit creates a new artifact identity.
4. New artifact identity requires new approval.
5. A reel-level boolean must not authorize publication.
6. Approval/publication events are auditable.
7. Artifact manifests should be immutable after approval.
8. If deterministic reproduction cannot prove identity, treat the output as a new artifact requiring approval.

## Pre-Publish Review

The pre-publish gate occurs against the final publication package before human approval.

It checks technical credibility, attribution, unsupported claims, secrets/private data, employer/client identifiers, internal system names, proprietary implementation/architecture details, anonymization, sensitive metrics, and audience-visible publication metadata.

The gate result should be persisted and tied to the same artifact identity being approved.

## Idempotency

Required for publishing, costly render job creation where duplicates matter, metric ingestion, repeat trend ingestion, and retried external mutations.

Publishing idempotency must account for ambiguous timeout outcomes and must not blindly create duplicate posts.

## LLM Boundary

LLMs should not directly write arbitrary database state, publish content, execute uncontrolled production shell commands, decide human approval, or mutate external services.

LLMs propose structured outputs; deterministic application code validates and performs controlled actions.

## Retrieved Content Is Untrusted Input

Research fetches third-party pages, feeds, comment threads, and papers, and that text reaches a model whose output becomes a published script. Retrieved content must be treated as adversarial input rather than neutral reference material. The risk is not only that a source is wrong; it is text written to steer generation.

Required controls:

1. Retrieved documents are passed to models as clearly delimited, explicitly labelled data. They are never concatenated into instruction text.
2. Retrieved content must never influence control flow, stage selection, tool invocation, or publication metadata. Application code decides those.
3. Instruction-like content found inside a retrieved document is ignored, and its presence is logged and flagged on the topic for human attention.
4. Input size and document count per call are bounded.
5. Verifying a claim requires a source independent of the one that introduced it. A source cannot confirm itself.
6. Retrieved documents are retained with their provenance, so an injected or incorrect claim can be traced after publication.

The pre-publish gate and human approval are the last line of defence, not the primary control. At roughly three reels per week, approval fatigue is a predictable failure mode, so the upstream controls have to carry the weight.

See `DECISIONS.md` D-023.

## Source Provenance

Material technical claims should retain source reference/URL, retrieval timestamp, source type, relevant evidence/summary, claim association, and whether attribution is required.

Preserve discovery source separately from verification source and inspiration source.

## Prompt Artifacts

Store important prompts as version-controlled files.

Generated outputs should retain prompt identifier/version and provider/model/config metadata where practical.

Because prompt files are edited in place, a hand-maintained version string drifts from the file it describes. Record a content hash of the prompt actually sent alongside its stable identifier — the hash is the part that cannot lie.

Prompt loading/versioning should be centralized rather than scattered through business logic.

## Secrets and Configuration

### Local Development

- Use environment variables, optionally loaded from a local `.env`.
- `.env` is Git-ignored.
- Commit `.env.example` with names/placeholders only.
- Use one centralized typed settings/configuration layer.

### Hosted Environment

Initially use platform-managed environment variables/secrets.

Introduce a dedicated cloud secret manager only when deployment/security needs justify it.

### Credential Isolation

Least privilege is the design goal.

Research components should not receive publishing credentials. Publishing components should receive only the credentials needed for the selected platform.

This may initially be enforced through dependency/config injection inside a modular monolith; stronger process/service isolation may be introduced later only when justified.

### Secret Incident Rule

If a credential is committed to Git or otherwise exposed, revoke/rotate it. Removing the file is not sufficient.

## Source Control Foundation

Before application implementation:

1. `git init`
2. Create/review `.gitignore`
3. Commit approved project/governance docs
4. Add `.env.example`
5. Configure local secret loading
6. Begin application code

Ignore at minimum:

- `.env*` except intentionally allowed `.env.example`
- OAuth token/credential files
- Python virtual environments/caches
- IDE/OS artifacts
- local databases
- logs
- generated media
- render/temp outputs
- build artifacts

## Architecture Decision Records

Use `DECISIONS.md` initially. Split into ADR files later if necessary.

Material decisions should state context, options, decision, rationale, consequences, independent review, and status.

## Security

Prefer least privilege.

Publishing credentials must be isolated from research/generation capabilities.

A component capable of discovering a webpage must not thereby gain permission to publish a reel.

## Observability

Every reel workflow should eventually have a correlation ID.

Logs should answer which stage failed, which provider was used, duration, retry state, approximate cost, and whether external state changed.

## Cost Architecture

Use higher-cost models only where reasoning quality materially matters.

Possible tiers:

- Cheap: classification and extraction
- Mid-tier: summarization/script generation
- Strong reasoning: architecture analysis/disputed claims/final review

Deduplication is deliberately absent from these tiers. Canonical fingerprints, and embedding similarity if it later proves necessary, are deterministic, cheaper, and reproducible across runs. An LLM deduplication call is none of those.

Track or estimate per-stage cost. Cost belongs in the stage run record, not only in logs — logs rotate away, and cost per reel is a product metric.

## Scalability

Design for approximately three reels/week initially, not millions of users.

Preserve clean module boundaries so extraction is possible later if actual scale requires it.

## Failure Strategy

Every external adapter should define timeout, retryability, max attempts, error classification, and behavior after uncertain outcomes.

Avoid infinite retries.

## Architectural Ambiguity Gate

Before a major architecture change, answer:

1. What current problem requires this?
2. What is the simplest option?
3. What are at least two viable choices?
4. What is the cost to reverse?
5. What failure mode does each introduce?
6. What does an independent reviewer say?
7. What evidence decides?

If uncertainty remains and the choice is reversible, prefer the simpler option. If expensive to reverse, prototype/spike first.
