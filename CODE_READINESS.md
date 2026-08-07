# CODE_READINESS.md — Definition of Code Ready

This document defines when ReelAgent code is ready to merge or move to the next project task.

## Readiness Levels

### Level 0 — Experiment

For spikes, API exploration, disposable prompt experiments, and rendering POCs.

Requirements:

- Clearly marked experimental.
- No production-quality assumption.
- No secrets committed.
- Results documented in the experiment's own file, or in `DECISIONS.md` when they informed a decision.

Experiment code must not silently become production code.

### Level 1 — Development Ready

- Purpose is clear.
- Public interfaces are typed.
- Configuration is externalized.
- Errors are handled intentionally.
- Basic tests exist.
- Lint/format checks pass.
- No secrets in repository.
- No obvious dead code.
- Logging exists where meaningful.

### Level 2 — Merge Ready

- Acceptance criteria satisfied.
- Relevant unit/integration tests pass.
- Negative/error paths tested.
- LLM outputs schema-validated.
- Documentation updated.
- Security review performed where applicable.
- Cost implications understood.
- Observability sufficient.
- No unresolved high-severity findings.
- Required independent review completed.

### Level 3 — Release Ready

- End-to-end path tested.
- External side effects are idempotent where applicable.
- Retry policy is bounded.
- Timeout behavior is defined.
- Secrets/configuration validated.
- Rollback/disable mechanism exists.
- Data migrations are reversible or explicitly accepted.
- Monitoring/logging is operational.
- Cost guardrails active for paid APIs, using the thresholds recorded in `DECISIONS.md` D-019. This item cannot be satisfied while those values are unset.
- Pre-publish safety gate enforced.
- Approval is bound to the exact publication artifact.
- Publish path verifies artifact/approval identity.
- One manual publishing smoke test recorded against a test channel.
- Revision loops are bounded and the bound is enforced.
- No known Critical/High defects.

## Mandatory Quality Gates

### Correctness

Check requirements, edge cases, timestamps/time zones, duplicates, stale inputs, malformed inputs, and partial failures.

### Reliability

Define behavior for unavailable external services, retries, partial failure, uncertain outcomes, and workflow resumption.

Verification and pre-publish rejections must have a defined backward path and a bounded revision count. An unbounded regenerate-until-it-passes loop is a **High** defect: it is both uncontrolled spend and a way to push a weak claim past verification by attrition.

### LLM Reliability

For LLM calls:

- Control input size.
- Identify prompt version.
- Define/validate output schema.
- Bound retries.
- Fail safely.
- Preserve provider/model metadata.
- Preserve factual source provenance where required.

### Data Integrity

Check state ownership, transaction boundaries, duplicate processing, idempotency, audit/history needs, and approval/version integrity.

### Artifact-Bound Approval Gate

Publishing must never rely only on a mutable reel-level approval boolean.

Release-ready publishing must demonstrate:

- A publication artifact/package has an immutable identity/content hash.
- Human approval references that exact identity.
- Any content-changing edit/regeneration produces a different artifact identity and requires new approval.
- Publish verifies the outgoing artifact identity equals the approved artifact identity.
- Title/description/captions/other approved publication metadata are included in the identity/package as appropriate.
- Approval and publication events are auditable.

A mismatch is a **Critical** defect.

### Pre-Publish Safety / Proprietary Information Gate

Before approval, verify:

- [ ] Material technical claims verified/characterized.
- [ ] Required attribution present.
- [ ] No unsupported benchmark claims.
- [ ] No credentials/tokens/secrets/private data.
- [ ] No unintended employer/client identification.
- [ ] No non-public internal system names.
- [ ] No proprietary architecture/implementation detail.
- [ ] Production incidents sufficiently anonymized.
- [ ] Sensitive business metrics removed or explicitly approved.
- [ ] Final title/description/captions/publication metadata reviewed.

Failure to enforce this gate is **High**; exposure of secrets or serious confidential data is **Critical**.

### External Publishing

Publishing code must:

- Require a valid approval for the exact artifact.
- Prevent duplicate publishing.
- Store platform response/publication ID.
- Handle uncertain timeout outcomes.
- Never blindly retry an ambiguous publish failure.
- Preserve an audit trail.

### Secrets and Configuration

Before adapters requiring credentials are Merge Ready:

- Secrets are injected, never hard-coded.
- `.env` and token/credential files are ignored.
- `.env.example` contains placeholders only.
- Central typed configuration is used.
- Components receive least-privilege configuration where practical.
- Logs/errors do not expose secrets.
- Hosted secrets use platform-managed secret/environment facilities initially.

If a credential enters Git history, rotate/revoke it; deletion alone is insufficient.

### Source Control Precondition

Application code is not considered Development Ready until:

- Git repository exists.
- `.gitignore` is reviewed.
- Governance docs are committed.
- Secret-bearing/runtime artifacts are excluded.

### Tests

Prefer many focused unit tests, targeted integration tests, and few E2E tests.

Tests should cover behavior rather than implementation details.

### Publishing Tests Must Not Publish

There is no sandbox for the publishing platform, so the publishing integration tests required elsewhere in this document must not reach it.

- All automated publishing tests run against a fake publisher implementing the same port: artifact/approval matching, duplicate prevention, idempotency keys, ambiguous-timeout handling, and error classification.
- Automated tests must never authenticate to a real platform. If real publishing credentials are visible in the environment, the suite fails closed rather than proceeding.
- Real-platform verification is a manually invoked, explicitly gated smoke test. It uploads unlisted or private to a dedicated test channel, never the production channel, and is never part of CI or the default test command.
- Level 3 requires one recorded successful manual smoke test, including the resulting platform publication ID.

An automated test that performs a real publish is a **Critical** defect, not a convenience. See `DECISIONS.md` D-024.

### Maintainability

Reject code when responsibilities are unclear, workflow stages are mixed, prompt/persistence/business logic is tangled, provider-specific behavior leaks through the domain, or abstractions exist only for hypothetical needs.

### Performance

Do not optimize prematurely. Performance changes require an observed bottleneck, measurement method, before/after evidence, and documented tradeoffs.

### Cost

Paid-API features should document triggers, expected calls, approximate cost category, retry impact, and relevant budget guardrails.

## Pull Request / Change Review Checklist

- [ ] Requirement is clear.
- [ ] Design matches project architecture.
- [ ] No unnecessary dependency/complexity.
- [ ] Correctness/error paths reviewed.
- [ ] Tests meaningful and passing.
- [ ] Security checked.
- [ ] LLM outputs validated where relevant.
- [ ] Side effects idempotent where relevant.
- [ ] Approval integrity preserved where relevant.
- [ ] Proprietary-information risks checked where relevant.
- [ ] Logging/diagnostics adequate.
- [ ] Cost impact understood.
- [ ] Documentation updated.
- [ ] No unresolved High/Critical findings.

## Severity

### Critical
Security compromise, credential exposure, destructive data loss, publication of an unapproved artifact, serious confidential-data exposure, or uncontrolled publishing.

### High
Incorrect publication, significant data inconsistency, repeated side effects, missing mandatory pre-publish gate, or major workflow failure.

### Medium
Maintainability, missing edge case, weak tests, or recoverable reliability issue.

### Low
Style/minor refactoring/non-blocking improvement.

## Code Ready Rule

**Code is not ready because multiple LLMs agree.**

Evidence, tests, constraints, review findings, and project-owner acceptance determine readiness.
