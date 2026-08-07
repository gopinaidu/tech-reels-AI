# DECISIONS.md — Architecture and Product Decision Log

## How to Use This Log

`ARCHITECTURE_GUIDELINES.md` requires material decisions to state context, options, decision, rationale, consequences, independent review, and status. Entries below follow that shape. Short product decisions may omit fields that add nothing.

**Statuses:** `Accepted`, `Proposed`, `Open — decision required`, `Superseded by D-nnn`, `Rejected`.

**Dates** are the date the decision was *recorded* in this log. D-001 through D-017 were recorded on 2026-08-07 when the log was consolidated; if any was actually decided earlier, correct the date in place.

**Open entries are not deferrable indefinitely.** D-019, D-020, D-022, and D-025 each block work that depends on them, and each says what it blocks.

---

## D-001 — Initial Audience
**Status:** Accepted
**Date:** 2026-08-07
**Decision:** Target senior software engineers, tech leads, and architects.
**Rationale:** Differentiate through practical architecture depth rather than beginner tutorials.
**Options considered:** Not recorded at the time.

## D-002 — Content Mix
**Status:** Accepted
**Date:** 2026-08-07
**Decision:** Approximately 60% trending/current and 40% evergreen as a flexible guideline, not a hard quota.
**Rationale:** Stay current without becoming dependent on low-quality trend cycles.

## D-003 — Content Pillars
**Status:** Accepted
**Date:** 2026-08-07
**Decision:** AI & Emerging Tech; Architecture & Distributed Systems; Languages & Performance; Cloud & Platform; Data & Databases; OMS & Commerce Technology with special focus on IBM Sterling OMS.
**Consequences:** Pillar six carries the highest proprietary-information risk in the project. See D-013.

## D-004 — Initial Reel Formats
**Status:** Accepted
**Date:** 2026-08-07
**Decision:** What's New?, 60-Second Architecture, Production Reality.
**Consequences:** "Production Reality" is the format most likely to surface non-public employer experience. The D-013 gate applies with particular force to it.

## D-005 — Initial Reel Queue
**Status:** Accepted
**Date:** 2026-08-07
**Decision:** (1) IBM Sterling OMS + Agentic AI + MCP, (2) Redis TTL is a Business Decision, (3) Kafka Share Groups / Kafka Queues.

## D-006 — MVP Human Approval
**Status:** Superseded by D-010
**Date:** 2026-08-07
**Original decision:** Reels require human approval before publication.
**Why superseded:** Correct in principle but underspecified — it did not say what approval attaches to, which is where the real defect lives.

## D-007 — Development Approach
**Status:** Accepted
**Date:** 2026-08-07
**Decision:** Build in approximately one focused hour per day with small completion gates.
**Consequences:** This is the binding constraint on the project. Every process gate in these documents spends part of it, and gates that cannot be met in that budget will be skipped rather than followed. Prefer cutting a gate deliberately over letting it decay.

## D-008 — Multi-LLM Review
**Status:** Accepted
**Date:** 2026-08-07
**Decision:** Use independent LLM review for material architectural ambiguity and significant code/design reviews. LLM consensus is advisory.
**Rationale:** Different model families expose different blind spots.

## D-009 — Pre-Code Documentation Gate
**Status:** Accepted
**Date:** 2026-08-07
**Decision:** No application code begins until README, AGENTS, CODE_READINESS, ARCHITECTURE_GUIDELINES, LLM_REVIEW_POLICY, and DECISIONS are reviewed and accepted.
**Consequences:** The gate is now met for structure. The first vertical slice should be treated as the test of these documents; parts that prove unworkable at the D-007 cadence should be revised here rather than quietly ignored.

## D-010 — Artifact-Bound Approval
**Status:** Accepted
**Date:** 2026-08-07
**Decision:** Human approval binds to a specific immutable publication artifact/package identified by a stable content/artifact identity, preferably a cryptographic hash. Any content-changing regeneration or edit creates a new artifact and invalidates prior approval. Publishing must verify that the outgoing artifact is the approved artifact.
**Rationale:** A mutable reel-level `approved` boolean can authorize content that was never reviewed.
**Consequences:** The data model must support versioned publication artifacts, approval identity, and auditable approval/publication records.
**Independent review:** Raised in Claude documentation review, 2026-08-07.

## D-011 — Source Control Before Code
**Status:** Accepted
**Date:** 2026-08-07
**Decision:** After documentation approval and before application code or credentials: initialize Git, create and review `.gitignore`, commit governance docs, add `.env.example`, configure secret loading, then begin code.
**Rationale:** Prompts and decisions require history, and credentials and runtime artifacts must be protected before the first broad `git add`.
**Consequences:** Git is initialized and `.gitignore` is in place as of 2026-08-07. The governance docs are not yet committed.
**Independent review:** Raised in Claude documentation review, 2026-08-07.

## D-012 — Secrets and Configuration Strategy
**Status:** Accepted
**Date:** 2026-08-07
**Decision:** Local secrets use environment variables, optionally loaded from a Git-ignored `.env`; commit `.env.example` with placeholders only. Use centralized typed configuration. Hosted environments initially use platform-managed secrets/environment variables. Introduce a dedicated secret manager only when justified. Apply least privilege so publishing credentials are not broadly available to research/generation components.
**Incident rule:** Any credential committed or exposed is rotated or revoked; deletion alone is insufficient.
**Consequences:** Inside a modular monolith this is enforced by config injection and discipline, not by process boundaries. See the credential isolation note in `ARCHITECTURE_GUIDELINES.md`.
**Independent review:** Raised in Claude documentation review, 2026-08-07.

## D-013 — Pre-Publish Safety and Proprietary-Information Gate
**Status:** Accepted
**Date:** 2026-08-07
**Decision:** The exact final publication artifact must pass a persisted pre-publish review before human approval, covering technical claims, attribution, unsupported benchmarks, secrets and private data, employer/client identity, internal system names, proprietary implementation and architecture details, anonymization, sensitive metrics, and audience-visible publication metadata.
**Rationale:** Agent generation rules alone are not sufficient protection at the last boundary before publication.
**Independent review:** Raised in Claude documentation review, 2026-08-07.

## D-014 — Initial Publishing Platform
**Status:** Accepted
**Date:** 2026-08-07
**Decision:** YouTube Shorts is the first automated publishing platform. LinkedIn and Instagram Reels are later candidates, subject to API and policy review at implementation time.
**Consequences:** Blocked on D-020 before adapter design begins.

## D-015 — Discovery Access Preference
**Status:** Accepted
**Date:** 2026-08-07
**Decision:** Prefer official API → RSS/Atom/feed → supported public endpoint → scraping only when necessary and permitted. Discovery source and verification source are separate concepts.

## D-016 — Prompt Versioning
**Status:** Accepted
**Date:** 2026-08-07
**Decision:** Important prompts are source-controlled artifacts with stable identifiers/versions. Generated outputs retain prompt identifier, a content hash of the prompt actually sent, and model/provider metadata where practical.
**Rationale:** Prompt files are edited in place, so a hand-maintained version string drifts from the file. The hash is the part that cannot drift.

## D-017 — Resumability
**Status:** Accepted
**Date:** 2026-08-07
**Decision:** Successful expensive pipeline stages must be persisted and reusable so downstream failures do not automatically repeat upstream paid work.
**Consequences:** Implemented through the stage run records in D-018.

## D-018 — Workflow State Model and Bounded Revision Loop
**Status:** Accepted
**Date:** 2026-08-07
**Context:** The original lifecycle was strictly forward, so the most common non-happy path in the pipeline — verification rejecting a claim — had no representable state and no bound. A single status field also cannot express both "where the reel is" and "what has already been paid for."
**Decision:** Split state into a milestone status and per-attempt stage run records. Add `REVISION_REQUESTED`, `REJECTED`, `FAILED`, and `SUPERSEDED`. Define backward transitions for verification failure, pre-publish gate failure, and owner rejection. Bound revision cycles at a default of two per reel version, after which the reel becomes `FAILED` and continuing requires a recorded owner action.
**Options considered:** (a) single status enum with in-progress states — rejected, cannot support resumption or cost attribution; (b) infer progress from persisted artifacts — rejected, explicitly forbidden by the explicit-state rule; (c) status plus stage runs — chosen.
**Rationale:** An unbounded verify-and-rewrite loop is uncontrolled spend and a way to push a weak claim past verification by attrition. Bounding it protects both cost and credibility.
**Consequences:** Two tables rather than one column. The bound is a tunable default, not a technical limit.
**Independent review:** Raised in Claude documentation review, 2026-08-07.

## D-019 — Cost Guardrail Thresholds
**Status:** Open — decision required
**Date:** 2026-08-07
**Context:** Cost is described as a first-class metric and Level 3 requires active cost guardrails, but no threshold exists anywhere. A guardrail without a number cannot be implemented or tested, which makes Level 3 currently unsatisfiable as written.
**Required to resolve — owner must set:**
- Monthly production budget ceiling.
- Per-reel soft ceiling (warn) and hard ceiling (halt).
- Maximum spend per stage attempt, and per reel across all revision cycles.
- Behavior on breach: halt the pipeline, or warn and continue.
- Whether the ceiling covers research and discovery calls or only generation, TTS, and rendering.
**Blocks:** Release Ready for any paid-API feature. Does not block Development Ready.
**Independent review:** Raised in Claude documentation review, 2026-08-07.

## D-020 — Publishing Platform API Constraints
**Status:** Open — verification required
**Date:** 2026-08-07
**Context:** The MVP commits to automated YouTube Shorts publishing. Platform API terms for video upload have historically included restrictions that would materially change the design — in particular, uploads from an API client that has not passed review may be constrained in visibility regardless of the requested setting.
**Required to resolve — verify against current official documentation, not memory:**
- Requirements and review/audit process for the upload scope.
- Whether an unaudited client's uploads are forced to private or unlisted, and what lifting that requires.
- Quota cost per upload against the daily quota, at roughly three uploads per week plus retries.
- Any Shorts-specific upload or metadata requirements.
**Consequence if restrictions are confirmed:** The workflow must represent a published-but-not-public state, and "PUBLISHED" stops meaning "publicly visible." That is a state model change, which is why this is verified before adapter design rather than during it.
**Blocks:** Publish adapter design.
**Independent review:** Raised in Claude documentation review, 2026-08-07.

## D-021 — Initial Technology Direction
**Status:** Accepted
**Date:** 2026-08-07
**Decision:** Python, FastAPI, Pydantic, SQLAlchemy, PostgreSQL, Docker, explicit workflow/scheduling code, Remotion + FFmpeg for rendering, and a lightweight approval UI.
**Rationale:** Matches the modular-monolith and no-unnecessary-infrastructure defaults, and keeps one language for pipeline logic.
**Consequences:** Remotion introduces a Node toolchain alongside Python purely for rendering — the one deliberate polyglot boundary. Rendering is therefore the module most likely to need process isolation later.
**Reversibility:** High for most items; rendering choice is the most expensive to reverse once scene definitions are built against it.
**Independent review:** Recorded as a decision following Claude documentation review, 2026-08-07; the stack itself has not had independent architectural review.

## D-022 — Synthetic Content Disclosure
**Status:** Open — verification required
**Date:** 2026-08-07
**Context:** The narration strategy contemplates synthetic TTS and possibly an authorized clone of the owner's voice. Platforms have disclosure requirements for synthetic or AI-assisted content, and these interact with the publication metadata that D-010 binds into the approved artifact.
**Required to resolve:**
- Current platform disclosure requirements for synthetic narration and AI-assisted content.
- Where disclosure is applied: upload metadata, on-screen, spoken, or description.
- Whether disclosure text belongs inside the approved artifact identity — it is audience-visible, so under D-010 it likely does.
**Blocks:** First publish, and the narration provider decision.
**Independent review:** Raised in Claude documentation review, 2026-08-07.

## D-023 — Retrieved Content Is Untrusted Input
**Status:** Accepted
**Date:** 2026-08-07
**Context:** Research fetches third-party pages, feeds, and comment threads, and that text reaches a model whose output becomes a script published under the owner's name. The existing rules treated LLM *output* as untrusted but said nothing about adversarial *input*. The structural protection already in place — models cannot publish, execute, or write arbitrary state — prevents an injected instruction from taking action, but not from shaping content.
**Decision:** Treat retrieved content as adversarial data. Delimit and label it in prompts, never let it influence control flow or publication metadata, ignore and flag instruction-like content, bound input size and document count, verify each claim against a source independent of the one that introduced it, and retain documents with provenance for post-hoc tracing.
**Rationale:** Human approval is a real backstop but a weak primary control — at three reels per week, approval fatigue is predictable rather than hypothetical.
**Consequences:** Verification needs at least two independent sources per material claim, which raises research cost per reel. That is an accepted trade for credibility, and it interacts with D-019.
**Independent review:** Raised in Claude documentation review, 2026-08-07.

## D-024 — Publishing Test Policy
**Status:** Accepted
**Date:** 2026-08-07
**Context:** Integration tests are required for publishing workflows, and the publishing platform has no sandbox. Left unspecified, that requirement is satisfiable only by testing against a real channel — which is the uncontrolled publishing this project classifies as Critical.
**Decision:** All automated publishing tests run against a fake publisher implementing the same port. Automated tests must never authenticate to a real platform, and the suite fails closed if real publishing credentials are visible in the environment. Real-platform verification is a manually invoked, explicitly gated smoke test that uploads unlisted to a dedicated test channel, never in CI. Level 3 requires one recorded successful smoke test.
**Options considered:** (a) test against the production channel and delete afterwards — rejected, deletion is not a control and the upload already happened; (b) skip publishing integration tests — rejected, idempotency is exactly what needs testing; (c) fake plus gated manual smoke test — chosen.
**Consequences:** Requires a dedicated test channel and a publisher port clean enough to fake honestly. The fake becomes the primary specification of publisher behavior, so it must model ambiguous timeouts, not just success.
**Independent review:** Raised in Claude documentation review, 2026-08-07.

## D-025 — Discovery Source Access Feasibility
**Status:** Open — spike required
**Date:** 2026-08-07
**Context:** Six source families are named, and each adapter is required to document its access method and terms before implementation. That check has not been run against the families themselves, so the source list was chosen before feasibility was known. Access terms and rate limits for community platforms in particular have changed materially in recent years, and the preferred-access rule already forbids falling back to scraping where terms prohibit it.
**Required to resolve:** For each of the six families, confirm a compliant access path exists, along with authentication requirements, rate limits, and cost if any.
**Consequence if a family has no compliant path:** Drop it from the source list rather than route around the access rule.
**Blocks:** Discovery adapter implementation. Should be a short timeboxed spike, not open research.
**Independent review:** Raised in Claude documentation review, 2026-08-07.

## D-026 — Media Storage for MVP
**Status:** Accepted
**Date:** 2026-08-07
**Context:** The guidance said large media should "eventually" live in object storage, which left the relational database as the implied interim home for rendered video.
**Decision:** Media files are never stored in Postgres. For the MVP they live on the local filesystem or a mounted volume, with Postgres holding path, size, and content hash. Object storage replaces the filesystem when hosting or durability requires it, behind a small reference abstraction.
**Rationale:** Video in Postgres bloats backups and restore times for no benefit at this scale, and the content hash is needed anyway for the D-010 artifact identity.
**Independent review:** Raised in Claude documentation review, 2026-08-07.

## D-027 — Review Context Authorization
**Status:** Accepted
**Date:** 2026-08-07
**Context:** The review policy mandates independent LLM code review while also forbidding non-public source code from being sent to external models. As written, an agent could reasonably decline the review the policy requires.
**Decision:** ReelAgent's own source code and governance documents are authorized for the review providers named in the policy. Employer, client, and other third-party non-public code, internal system names, and incident data are never authorized, regardless of review value.
**Rationale:** Removes a contradiction that would otherwise block a mandatory process, without widening what may be disclosed.
**Independent review:** Raised in Claude documentation review, 2026-08-07.
