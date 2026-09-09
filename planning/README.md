# Opportunity Scout quality enhancement proposals

This directory contains reviewed intent and implementation approaches for significant changes.
GitHub issues and pull requests track live work; these documents preserve decisions that future humans
and agents need to understand or extend.

## When a proposal is required

Create a Product Enhancement Proposal (PEP) when a change does any of the following:

- Adds or materially changes user-visible behavior.
- Changes research stages, evidence rules, scoring, qualification, or recommendation semantics.
- Changes API payloads, persisted data, exports, or compatibility contracts.
- Changes privacy, worker isolation, local-only operation, authentication, networking, or another
  trust boundary.
- Requires migration, staged rollout, rollback strategy, or coordinated delivery.
- Spans two or more major subsystems such as backend, frontend, persistence, and research orchestration.

A small bug with established expected behavior, dependency update, documentation correction, or
behavior-preserving refactor can proceed directly from an issue. When uncertain, use the
`shape-proposal` skill. Prefer a short proposal over hiding a consequential decision in an
implementation pull request.

## Identity and layout

Open the tracking issue first. Its number supplies the stable identity:

```text
planning/proposals/<issue-number>-<slug>.md  -> PEP-<issue-number>
planning/plans/<issue-number>-<slug>.md      -> implementation plan, when required
```

Copy `proposal-template.md` to start. Keep one proposal focused on one independently understandable
enhancement. Split it when reviewers could accept one outcome while rejecting another.

## Lifecycle

```text
draft -> accepted -> implementing -> implemented
                   -> deferred
draft/accepted -> rejected
implemented -> superseded
```

- `draft`: incomplete or under discussion; it may merge to preserve review history.
- `accepted`: a human approved product behavior, boundaries, and unresolved decisions. An agent may not
  assign this status to its own proposal.
- `implementing`: at least one implementation pull request is open or merged.
- `implemented`: acceptance criteria are satisfied and implementation links are recorded.
- `deferred`: valid proposal with no current delivery commitment.
- `rejected`: considered and deliberately not pursued; preserve the rationale.
- `superseded`: replaced by another PEP; link both directions.

Implementation starts only from `accepted`. A proposal cannot become `accepted` or `implemented` while
it contains scope-changing open questions or placeholder markers.

## From proposal to code

1. Create the tracking issue and proposal-only branch.
2. Draft the PEP with `shape-proposal`; do not change production code in that pass.
3. Obtain human review, resolve material questions, set `status: accepted`, and merge the proposal.
4. For work spanning components or pull requests, write `planning/plans/<issue-number>-<slug>.md`.
5. Implement independently valuable slices. Each pull request references the PEP and requirement IDs.
6. Run `verify-change`, then `review-change`, using fresh evidence from the current commit.
7. The final implementation pull request sets the PEP to `implemented` and records implementation links.
8. Keep authoritative behavior in code, models, and tests; proposals explain decisions without
   duplicating those contracts.

## Source-of-truth conflicts

- Code and executable tests describe what exists now.
- An accepted PEP describes intended target behavior.
- An implementation plan describes how to reach that target.
- Product documentation describes behavior users can rely on after it ships.

Record and resolve disagreements. Do not rewrite proposal history or claim proposed behavior is shipped.

## Index

Add one row for every proposal, including rejected and superseded proposals.

| ID | Title | Status | Owner | Tracking issue |
| --- | --- | --- | --- | --- |
