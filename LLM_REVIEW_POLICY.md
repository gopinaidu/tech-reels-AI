# LLM_REVIEW_POLICY.md

## Purpose

ReelAgent uses independent AI reviewers to reduce blind spots without manufacturing consensus. OpenAI Codex is the default code-PR reviewer; Claude, Gemini, and other capable models remain useful for fallback and additional architecture review.

## Roles

### Primary Architect / Implementer
Produces the initial design, assumptions, options, recommendation, implementation where applicable, and test approach.

### Independent Reviewer
Evaluates independently and tries to find problems rather than confirm the proposal. The reviewer should not be the same agent/session that performed the primary implementation pass.

### Project Owner
Makes the final call on material tradeoffs and accepts or rejects residual risk.

## Baseline Peer Review For Every Code PR

Every pull request containing application, infrastructure, workflow, or test code must receive an independent AI peer review before merge.

Default implementation:

- OpenAI Codex reviews the GitHub pull request.
- The Codex review must be independent of the primary implementation pass.
- Critical, High, or otherwise blocking findings must be fixed or explicitly accepted by the project owner.
- After material fixes, request another review of the updated diff when needed.
- CI and automated tests remain mandatory; AI review does not replace them.

Fallback when Codex review is unavailable:

- Run the Standard Code Review Prompt below through a separate Claude, Gemini, or other capable model session.
- Provide the PR diff and relevant ReelAgent governance context.
- Record the reviewer, findings, disposition, and any accepted risk on the pull request before merge.

Documentation-only typo/copy changes may skip the baseline peer review when they cannot change behavior, governance, security, architecture, or operational meaning.

## Mandatory Additional Independent Review

In addition to the baseline code-PR peer review, use another independent model review for:

- Major architectural decisions
- New infrastructure/platform dependencies
- Costly-to-change data models
- Workflow/orchestration framework selection
- Authentication/security model
- Secrets/credential isolation model when materially changed
- Publication artifact/approval integrity design
- Publishing safety/idempotency
- Significant concurrency design
- Database ownership/transaction changes
- Expensive provider commitments
- Conflicting technical sources
- Authoritative performance guidance
- Large refactors
- Ambiguity explicitly flagged by the primary architect

For these cases, provider/model diversity is preferred where practical. A Codex code review alone does not replace a deliberate architecture review when one is required.

## Optional Review

Additional review beyond the baseline peer-review gate is usually unnecessary for naming cleanup, simple CRUD, copy changes, straightforward tests, documentation typos, and behavior-preserving small refactors.

## Required Review Packet

Provide:

### Context
What are we building?

### Requirement
What must be achieved?

### Constraints
Time, cost, stack, security, scale, compatibility.

### Current Proposal
What is proposed?

### Alternatives
At least one credible alternative.

### Known Concerns
What is uncertain?

### Requested Review
Ask for incorrect assumptions, failure modes, security/reliability issues, overengineering, missing alternatives, operational/cost concerns, test gaps, and a recommendation.

## Standard Architecture Review Prompt

"You are an independent senior software architect reviewing ReelAgent.

Do not optimize for agreement with the existing proposal.

Evaluate the design against correctness, simplicity, failure recovery, data integrity, security, approval integrity, observability, maintainability, cost, reversibility, and MVP scope.

Identify hidden assumptions and concrete failure scenarios.

Separate findings into Critical, High, Medium, and Low severity.

If you disagree, propose a specific alternative and explain the tradeoff.

Do not recommend additional infrastructure unless it solves a stated problem."

## Standard Code Review Prompt

"You are an independent senior engineer reviewing ReelAgent code.

Review for functional correctness, edge cases, exception handling, security, concurrency, data integrity, idempotency, approval/artifact integrity, API misuse, LLM output validation, tests, observability, proprietary-information risk, unnecessary complexity, and cost impact.

For Python changes, explicitly check typing, async behavior, resource lifecycle, exception boundaries, mutable/default-state hazards, library/API misuse, and tests that may falsely pass despite broken behavior.

Do not praise the code generically.

Return prioritized findings with file/function references when available. For each blocking finding, provide a concrete fix or acceptance criterion."

## Review Independence

Do not bias the reviewer by saying another model already approved the design. Ask for counterexamples and what would make the reviewer reject the proposal.

The implementation agent may respond to findings and make fixes, but the updated diff should be reviewed independently again when the fix materially changes behavior.

## Reconciling Disagreement

Do not decide by model voting.

Use:

1. Project requirements
2. Empirical tests/benchmarks
3. Official documentation
4. Failure-mode analysis
5. Security/data-integrity constraints
6. Cost
7. Simplicity
8. Reversibility

If uncertainty remains and the choice is reversible, choose the simpler option and record uncertainty. If expensive to reverse, run a spike/prototype.

## Decision Record

After material review, update `DECISIONS.md` with context, options, primary recommendation, independent review summary, disagreements, evidence, final decision, and consequences.

## AI Review Is Not a Test Substitute

Agreement among models does not prove correctness. Use automated tests, prototypes, benchmarks, documentation, and runtime evidence.

## Provider Diversity

For routine code PRs, Codex is the default reviewer. For material architectural or high-risk decisions, use a different model family where practical so the second review is genuinely independent rather than another pass through the same model family.

## Sensitive Context

Do not send proprietary/sensitive information to an external model unless approved for that provider/use case.

Redact credentials, personal information, internal company names, confidential incident data, and unauthorized non-public source code.

ReelAgent's own source code and governance documents **are** authorized for the review providers named in this policy. Without that, the independent code review this document mandates could not be performed at all.

Employer, client, and any other third-party non-public code, internal system names, and incident data are never authorized, regardless of how much review value they would add. See `DECISIONS.md` D-027.

## Review Completion

A required review is complete when findings are recorded, Critical/High findings are resolved or explicitly accepted, material disagreement is documented, disputed correctness is addressed with evidence where possible, and the owner decision is recorded.
