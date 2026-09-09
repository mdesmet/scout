---
name: review-change
description: Review an Opportunity Scout branch or pull-request diff against its issue, accepted PEP, implementation plan, repository invariants, compatibility requirements, and verification evidence. Use for self-review, pull-request review, privacy review, or final readiness assessment.
---

# Review an Opportunity Scout change

## Establish the review contract

1. Read root and affected scoped `AGENTS.md` files.
2. Read the issue, accepted PEP, implementation plan, and related decisions. If a proposal-required
   change has no accepted PEP, report that as a process blocker.
3. Inspect the three-dot diff against its true base, including data-model and dependency changes.
4. Read enough surrounding code and tests to separate regressions from pre-existing behavior.
5. Read fresh verification output; do not treat a completion statement as evidence.

## Review dimensions

- **Requirements:** implemented behavior maps to requirements and acceptance criteria; no undocumented
  scope was added.
- **Correctness:** success, boundary, invalid-input, concurrency, retry, interruption, and failure paths
  behave as intended.
- **Evidence integrity:** citations, source independence, qualification gates, `Unknown` scores, and
  model-versus-deterministic responsibilities preserve repository invariants.
- **Privacy and safety:** founder context, memory, research artifacts, worker isolation, origin checks,
  loopback binding, and synthetic-data boundaries remain intact.
- **Compatibility:** API payloads, stored reports, checkpoints, exports, and frontend types remain
  compatible with historical data or have an explicit transition.
- **Tests:** tests demonstrate changed behavior and regression coverage, not merely framework behavior.
- **Operations:** errors are actionable, interruption and recovery are safe, and logs avoid sensitive
  content.
- **Maintainability:** the change follows nearby patterns and avoids unrelated refactors or duplicate
  sources of truth.

## Findings

Report concrete issues supported by a specific path and line. Order findings by severity and explain
the observable failure, violated requirement or invariant, and a safe correction. Separate blocking
defects from non-blocking improvements.

If no findings remain, state which diff and evidence were reviewed and any residual risk or checks that
could not be performed. Do not approve or merge on behalf of the human reviewer.
