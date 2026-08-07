# ReelAgent Project Structure

This document defines the initial repository layout for the ReelAgent MVP. It follows the modular-monolith direction in `ARCHITECTURE_GUIDELINES.md` and D-021 in `DECISIONS.md`.

The goal is to create clear module boundaries without prematurely creating deployable microservices.

## Initial Layout

```text
tech-reels-AI/
├── README.md
├── AGENTS.md
├── CLAUDE.md
├── CODE_READINESS.md
├── ARCHITECTURE_GUIDELINES.md
├── LLM_REVIEW_POLICY.md
├── DECISIONS.md
├── PROJECT_STATUS.md
├── .gitignore
├── .env.example
├── pyproject.toml                 # Python project/dependency/tool configuration
├── src/
│   └── reelagent/
│       ├── __init__.py
│       ├── app.py                 # FastAPI application factory/entrypoint
│       ├── config.py              # Central typed configuration
│       ├── topics/                # Topic discovery, scoring, dedupe domain
│       ├── research/              # Research and provenance workflows
│       ├── scripting/             # Reel script generation
│       ├── verification/          # Claim verification
│       ├── scenes/                # Structured scene planning
│       ├── rendering/             # Render orchestration and media references
│       ├── approvals/             # Pre-publish review and artifact-bound approval
│       ├── publishing/            # Platform-neutral publishing port/adapters
│       ├── analytics/             # Metrics ingestion and analysis
│       ├── workflows/             # Explicit orchestration between stages
│       ├── persistence/           # DB session/repository implementations
│       └── shared/                # Small genuinely cross-cutting primitives only
├── prompts/
│   ├── research/
│   ├── topic_scoring/
│   ├── scripting/
│   ├── verification/
│   ├── scenes/
│   └── review/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── docs/
│   └── PROJECT_STRUCTURE.md
└── renderer/                      # Remotion/Node boundary; create only when rendering work starts
```

## Structure Rules

### 1. Feature modules first

Prefer feature/domain modules such as `topics`, `research`, and `publishing` over generic top-level folders such as `services`, `utils`, or `managers`.

### 2. Do not create empty architecture theater

Directories above describe intended ownership boundaries. Do not create every package immediately just to match this tree. Create a package when work for that module begins.

### 3. Keep the first vertical slice small

The initial implementation should require only:

```text
src/reelagent/
├── __init__.py
├── app.py
├── config.py
└── topics/
```

plus tests and project tooling.

Research, rendering, publishing, and other modules are added when their milestones begin.

### 4. `shared` has a high bar

`shared/` is not a dumping ground. Code belongs there only when it is genuinely cross-domain and has no natural owning module.

Avoid a generic `utils.py`.

### 5. Infrastructure stays behind module boundaries

External APIs, LLM providers, databases, TTS systems, storage, and publishing platforms must not define core domain objects.

Provider-specific code should remain behind small interfaces/ports where provider replacement is a realistic requirement.

### 6. Prompt files are source-controlled artifacts

Prompts live under `prompts/`, not as large inline application strings. Prompt content hashes and provider/model metadata should be retained with generated outputs where required by D-016.

### 7. Rendering is a deliberate polyglot boundary

The Python application owns workflow state and orchestration. Remotion/Node is introduced under `renderer/` only when scene rendering begins.

Do not introduce Node dependencies into the Python application modules.

### 8. Tests mirror behavior, not implementation details

- `tests/unit/` — pure domain/application behavior
- `tests/integration/` — database/provider adapter boundaries
- `tests/fixtures/` — safe, non-secret reusable test data

Publishing automation tests must follow D-024 and never use real publishing credentials in automated tests.

### 9. Runtime/generated files are not repository structure

Rendered media, temporary files, local databases, logs, caches, OAuth tokens, and `.env` files remain outside source control according to `.gitignore` and D-011/D-012.

## First Engineering Increment

The next implementation increment should create only the files needed to prove:

1. Python project installation works.
2. Typed configuration loads safely.
3. FastAPI starts.
4. `/health` returns successfully.
5. Tests and lint/format tooling run.

No database, LLM, discovery adapter, or rendering integration is required for that increment.

## Change Policy

This structure is a working baseline, not a permanent framework.

If implementation shows that a boundary is awkward or unnecessary, change it deliberately and update this document. Material architectural changes should follow `LLM_REVIEW_POLICY.md` and be recorded in `DECISIONS.md` when required.
