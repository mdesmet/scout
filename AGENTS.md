# Opportunity Scout development instructions

Opportunity Scout is a local research workspace that helps a solo founder find and assess customer
problems. Keep changes reviewable and tie them to an explicit user-visible, research-quality, or
operational outcome.

## Sources of truth

- Current behavior: executable code and tests under `scout/`, `src/`, and `tests/`.
- Target behavior: an accepted proposal under `planning/proposals/`.
- Implementation approach: the matching file under `planning/plans/`, when one is required.
- Explanatory documentation: `README.md` and `docs/`.
- Historical reports and local data are outputs, not authoritative product contracts.

When these sources disagree, surface the discrepancy. Do not silently change a proposal to match the
code or describe unshipped intent as current behavior.

## Product and safety invariants

- Research evidence must remain traceable to its cited source. Never invent, strengthen, or merge
  evidence to satisfy a qualification gate.
- Unsupported scores remain `Unknown`; there is no composite score or probability of success.
- Deterministic qualification gates remain separate from model judgment and fail conservatively when
  required evidence is missing or malformed.
- Historical reports retain their original context and are never silently rewritten.
- Founder context, memory, local research artifacts, and Codex event logs remain local unless the user
  explicitly exports or publishes them.
- Research workers stay isolated from user configuration, plugins, connected apps, shell tools, and
  private-account access.
- The server remains loopback-only unless an accepted proposal defines authentication, authorization,
  deployment, and data-handling requirements for a broader trust boundary.
- Synthetic examples remain visibly labeled and cannot contaminate learning or user outcomes.

## Repository map

| Path | Responsibility |
| --- | --- |
| `scout/` | FastAPI application, research orchestration, scoring policy, persistence, and exports. |
| `src/` | React workspace and report interfaces. |
| `tests/` | Backend and browser behavior. |
| `scripts/` | Bounded development and live-smoke utilities. |
| `docs/` | Demonstration and quality documentation. |
| `planning/` | Human-reviewed proposals and implementation plans. |
| `.agents/skills/` | On-demand development procedures. |

## Proposal workflow

Use the `shape-proposal` skill before implementation when a change affects user-visible behavior,
research or scoring contracts, persistent data, privacy or trust boundaries, rollout compatibility,
or two or more major subsystems. Small bug fixes, dependency updates, documentation corrections, and
behavior-preserving refactors can proceed directly from an issue.

An agent may draft a proposal but may not mark its own proposal `accepted`. Implementation begins only
after human acceptance. Use `planning/README.md` for the lifecycle and required content.

## Skills

- `shape-proposal`: decide whether a proposal is required and create or refine it without coding.
- `safe-git-workflow`: isolate work, curate commits, rebase, and prepare branches safely.
- `verify-change`: select and run path-appropriate verification.
- `review-change`: review a diff against its proposal, invariants, and fresh evidence.

Keep always-applicable guardrails here. Put detailed, task-specific procedures in skills.

## Verification

- Backend changes require `.venv/bin/python -m pytest -q`.
- Frontend changes require `npm run build`; browser behavior changes also require `npm test`.
- Proposal, plan, skill, or agent-instruction changes require `make development-check`.
- A live smoke check consumes Codex usage and requires explicit user authorization.
- Use `verify-change` for the complete path-aware matrix before completion.

## Git and shared-repository safety

- Prefer a dedicated worktree when the main checkout has user changes or concurrent work.
- Stage explicit paths and inspect the staged diff before committing.
- Rebase onto `origin/main`; do not merge `main` into a topic branch.
- Review branch scope with a three-dot diff.
- Keep commits buildable and independently revertible.
- Commit subjects use `type(scope): outcome`; explain non-obvious rationale and exclusions in the body.
- Use the `safe-git-workflow` skill for the complete procedure.
