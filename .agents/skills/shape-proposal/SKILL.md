---
name: shape-proposal
description: Decide whether an Opportunity Scout change needs a PEP, then investigate and draft or refine the proposal without implementing production code. Use for meaningful product behavior, research or scoring contracts, persistent data, privacy boundaries, migrations, rollout design, or changes spanning multiple subsystems.
---

# Shape an Opportunity Scout proposal

Use this skill to establish what and why before deciding how to implement a consequential change.

## Decide whether a PEP is required

Read `planning/README.md`. Require a PEP for user-visible behavior, evidence or scoring contracts,
persistent data, privacy or trust boundaries, coordinated rollout, or work crossing two major
subsystems. A small bug with established expected behavior, dependency update, documentation
correction, or behavior-preserving refactor can proceed without one.

State the classification and evidence. If no PEP is required, stop this skill and continue through the
normal issue and pull-request workflow.

## Ground the proposal

Before writing:

1. Read `README.md`, root `AGENTS.md`, and instructions scoped to affected paths.
2. Read the tracking issue and related discussions.
3. Trace current behavior through code, tests, data models, prompts, scoring policy, and configuration.
4. Find the closest existing pattern and any previous proposal or architecture decision.
5. Separate current facts, requested intent, assumptions, and unresolved decisions.

Do not draft from an issue title or another agent's summary alone.

## Shape the decision

- Confirm the users, problem, success criteria, scope, constraints, and compatibility needs.
- Present meaningful alternatives and recommend one.
- Ask for human decisions when ambiguity changes behavior, safety, public interfaces, or scope.
- Split work when parts can be accepted or delivered independently.
- Prefer the smallest independently valuable outcome.

## Write the PEP

Copy `planning/proposal-template.md` to `planning/proposals/<issue-number>-<slug>.md`. Set
`id: PEP-<issue-number>` and keep `status: draft`. Fill every section with repository-specific
content and remove all template placeholders.

Update the index in `planning/README.md`. This is a proposal-only pass: do not change production code,
stored data, or runtime configuration.

An agent must not set its own proposal to `accepted`; that transition requires explicit human review.

## Self-review

- Verify every requirement is observable and every acceptance criterion maps to a requirement.
- Check goals against non-goals, rollout against compatibility, and tests against failure modes.
- Confirm affected evidence, privacy, persistence, and research-worker boundaries are covered.
- Link authoritative code or contracts instead of duplicating definitions.
- Run `make development-check`.

Report the draft path, key decisions, unresolved questions, and human review needed for acceptance.
