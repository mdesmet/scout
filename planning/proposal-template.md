---
id: PEP-000
title: Short outcome-oriented title
status: draft
owner: GitHub handle or team
created: YYYY-MM-DD
updated: YYYY-MM-DD
tracking_issue: "#000"
implementation_prs: []
supersedes: []
superseded_by: null
---

# PEP-000: Short outcome-oriented title

## Summary

State the proposed outcome and who benefits in one short paragraph.

## Problem

Describe the observed problem, current behavior, and evidence. Distinguish verified repository facts
from assumptions.

## Goals

- State measurable outcomes this proposal must deliver.

## Non-goals

- State adjacent outcomes deliberately excluded from this proposal.

## User and operator scenarios

Describe independently testable scenarios. Prefer Given/When/Then when it makes expected behavior
unambiguous.

## Requirements

- **REQ-001:** State one observable, implementation-independent requirement.

## Acceptance criteria

- [ ] Map each criterion to requirement IDs and a reproducible verification method.

## Evidence, privacy, and trust boundaries

Describe source traceability, model judgment, deterministic gates, identity, data flow, local artifacts,
secret handling, failure behavior, logs, and abuse cases. Write `No change` with justification when the
proposal genuinely has no impact.

## Public contracts and compatibility

List affected APIs, Pydantic and TypeScript models, stored reports, checkpoints, configuration, exports,
and supported historical data. Link authoritative definitions instead of copying fields.

## Rollout and rollback

Define delivery slices, feature gates when needed, data migration order, compatibility during rollout,
and a rollback that remains possible after each slice.

## Observability

State signals that demonstrate adoption, correctness, performance, and failure without exposing founder
context, memory, private research artifacts, or sensitive source content.

## Test plan

List unit, browser, compatibility, migration, recovery, and live-research scenarios. Name the command or
harness that provides evidence when known, and flag checks that consume Codex usage.

## Risks and alternatives

Record material drawbacks, rejected alternatives, and the consequence of doing nothing.

## Open questions

- List only questions that still require a decision. Write `None` before moving to `accepted`.

## Implementation history

- Record plan and implementation pull-request links, rollout milestones, and follow-up PEPs.
