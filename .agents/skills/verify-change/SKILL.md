---
name: verify-change
description: Select and run fresh, path-appropriate verification for an Opportunity Scout change before completion, commit, or pull request. Use for backend, frontend, browser, research policy, persistence, prompts, planning, skills, or documentation changes.
---

# Verify an Opportunity Scout change

Evidence must precede completion claims. Inspect the three-dot branch diff or requested file set, then
run every applicable row. Focused tests help while iterating but do not replace final applicable checks.

## Verification matrix

| Changed area | Required verification |
| --- | --- |
| `planning/**`, `.agents/skills/**`, any `AGENTS.md` | `make development-check` |
| `scout/**`, backend `tests/**`, Python dependencies | `.venv/bin/python -m pytest -q` |
| `src/**`, TypeScript or Vite configuration | `npm run build` |
| User journeys, navigation, or browser behavior | `npm test` |
| Research stages, prompts, evidence gates, or scoring policy | focused backend tests, then the full backend suite |
| Persistence, memory, lineage, or exports | backend suite plus migration and legacy-data scenarios |
| `docs/**` or user-facing behavior | build/test the behavior described and inspect changed links |
| Setup, startup, or dependency files | run the affected setup/startup path in a clean or documented environment |

The live smoke script consumes Codex usage. Run it only with explicit user authorization. If a command
needs unavailable infrastructure or credentials, record the exact prerequisite and residual risk.

## Contract checks

- Treat Pydantic models, API schemas, persisted JSON, SQLite records, scoring rules, and checkpoint
  payloads as compatibility-sensitive contracts.
- Check old reports and partial checkpoints remain readable when their structures are affected.
- Confirm documentation describes shipped behavior, not accepted-but-unimplemented intent.
- Inspect generated or exported artifacts for unintended personal or research data.

## Completion report

Report the diff or commit verified, each command and result, manual scenarios, deferred checks and
their impact, and requirement IDs covered when a PEP exists. Do not infer that lint, build, unit,
browser, or live research checks prove one another.
