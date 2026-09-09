---
name: Product enhancement proposal (PEP)
about: Track a consequential change that must be designed and accepted before implementation
title: "[PEP] "
labels: ""
assignees: ""
---

<!--
Use this template when the change affects product behavior, research or scoring contracts,
persistent data, trust boundaries, rollout compatibility, or multiple major subsystems.

The issue number becomes the PEP number. After opening this issue, draft
planning/proposals/<issue-number>-<slug>.md from planning/proposal-template.md.
Remove instructional comments before submitting, but keep every section. Write "None" or
"No change" with a reason where appropriate.
-->

## Proposed outcome

<!-- State the user-visible, research-quality, or operational outcome and who benefits. -->

## Problem and evidence

<!-- Describe current behavior and link reproducible evidence. Separate verified facts from assumptions. -->

## Why a PEP is required

<!-- Select every applicable trigger. -->

- [ ] User-visible behavior changes materially.
- [ ] Research, evidence, scoring, qualification, or recommendation semantics change.
- [ ] An API, persisted-data, export, or compatibility contract changes.
- [ ] Privacy, isolation, networking, authentication, or another trust boundary changes.
- [ ] Migration, staged rollout, rollback, or coordinated delivery is required.
- [ ] The work spans two or more major subsystems.

## Goals

<!-- List measurable outcomes. -->

-

## Non-goals

<!-- List adjacent outcomes explicitly excluded. -->

-

## Scenarios and candidate requirements

<!-- Describe independently testable scenarios and observable, implementation-independent requirements. -->

## Evidence, privacy, and trust boundaries

<!-- Cover source traceability, data flow, local artifacts, secrets, worker isolation, failure behavior, and abuse cases. -->

## Contracts, rollout, and rollback

<!-- Identify affected interfaces and historical data, delivery constraints, migration needs, and a viable rollback. -->

## Open questions, risks, and alternatives

<!-- Record decisions still needed, important alternatives, risks, and the consequence of doing nothing. -->

## Process checklist

- [ ] This issue number will be used for the PEP identity and filename.
- [ ] No production implementation will begin until a human marks the PEP accepted.
