# ReelAgent Contribution Workflow

All project changes must go through a feature branch and pull request before they reach `main`.

## Mandatory Branch / PR Flow

1. Start from the latest `main`.
2. Create a focused branch for the change.
   - `feat/<short-description>` for product/application features.
   - `fix/<short-description>` for bug fixes.
   - `chore/<short-description>` for tooling, documentation, or maintenance.
3. Commit changes only to that branch. Do not commit directly to `main`.
4. Push the branch and open a pull request targeting `main`.
5. CI must pass before merge.
6. Perform the required human and/or independent LLM review described in `CODE_READINESS.md` and `LLM_REVIEW_POLICY.md`.
7. Resolve blocking review findings on the same branch and let CI run again.
8. Merge only after the change is approved and no blocking findings remain.

## Pull Request Scope

Prefer one coherent change per PR. Keep PRs small enough to review meaningfully and avoid mixing unrelated refactors with feature work.

## Main Branch Rule

`main` is treated as an integration branch containing reviewed work only. Direct commits to `main` are not part of the ReelAgent development process, including changes made by AI agents.

## AI Agent Rule

Any AI coding or documentation agent working on ReelAgent must create or use a non-`main` branch and open a PR for repository changes. The agent must not merge its own PR unless the project owner explicitly requests the merge after review.

## Review Evidence

The PR should make it easy to answer:

- What changed and why?
- What tests or checks ran?
- Did CI pass?
- Is independent LLM review required?
- Were any review findings accepted or fixed?
- Are documentation or decisions affected?
