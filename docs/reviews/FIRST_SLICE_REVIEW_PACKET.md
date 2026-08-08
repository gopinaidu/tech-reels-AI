# ReelAgent First Slice — Independent Review Packet

## Context

ReelAgent is a personal AI-assisted system for producing technically accurate short-form software-engineering content. The MVP is intentionally a modular monolith and must remain small enough to evolve in focused development sessions.

This review covers only the first engineering slice. It does **not** cover external discovery adapters, databases, LLM integration, rendering, approvals, or publishing.

## Requirement

Establish a Development-Ready foundation that proves:

1. The Python project installs successfully.
2. Centralized typed configuration loads safely.
3. FastAPI starts and exposes a health endpoint.
4. A provider-neutral topic-discovery domain boundary exists.
5. Automated tests, linting, and strict type checks pass in CI.

## Constraints

- Python 3.12+
- FastAPI
- Pydantic / Pydantic Settings
- pytest
- Ruff
- mypy strict
- Modular monolith
- No database yet
- No external discovery adapters yet
- No LLM calls yet
- No publishing/rendering code yet
- No secrets committed

## Current Implementation

Review these files:

- `pyproject.toml`
- `.env.example`
- `.github/workflows/ci.yml`
- `src/reelagent/config.py`
- `src/reelagent/app.py`
- `src/reelagent/topics/models.py`
- `src/reelagent/topics/ports.py`
- `tests/test_config.py`
- `tests/test_health.py`
- `tests/unit/test_topic_models.py`
- `docs/PROJECT_STRUCTURE.md`
- `PROJECT_STATUS.md`

Relevant governance:

- `AGENTS.md`
- `CODE_READINESS.md`
- `ARCHITECTURE_GUIDELINES.md`
- `LLM_REVIEW_POLICY.md`
- `DECISIONS.md`

## Design Choices

- Global FastAPI app instance for the initial health-only skeleton.
- Centralized Pydantic Settings boundary for environment configuration.
- Secret-bearing settings use `SecretStr`.
- Topic discovery domain models are immutable Pydantic models.
- Timestamps used for discovery freshness must be timezone-aware.
- Source provenance is part of each discovered topic candidate.
- `TopicDiscoverySource` is an async provider-neutral `Protocol`.
- No source-specific adapter is implemented until D-025 is resolved.
- CI runs Ruff, mypy strict, and pytest on pushes and pull requests.

## Known Open Questions

1. Is a global FastAPI app instance sufficient for this stage, or should an application factory be introduced now?
2. Are the initial discovery models appropriately small, or is any field prematurely committed?
3. Is returning `list[TopicCandidate]` from the discovery port sufficiently provider-neutral, or should a more general collection/result type be used?
4. Are timezone-awareness validators strong enough for production input boundaries?
5. Are the current dependency/version ranges reasonable for an MVP foundation?

## Requested Review

Act as an independent senior software architect/engineer. Do not optimize for agreement.

Review for:

- Functional correctness
- Simplicity and overengineering
- Module/dependency boundaries
- Type-safety
- Configuration/secrets handling
- Test quality and missing negative paths
- CI quality-gate gaps
- Domain-model coupling
- Future adapter compatibility
- Failure modes
- Maintainability
- Any violation of the approved ReelAgent governance documents

Return findings as **Critical, High, Medium, Low**.

For each blocking finding, provide a concrete fix or acceptance criterion.

If no Critical/High issues exist, explicitly state whether this slice is reasonable to accept as the Development-Ready baseline.
