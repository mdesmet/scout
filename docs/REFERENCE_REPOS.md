# Reference repository review

Reviewed locally on 2026-09-07. These repositories are research references, not application dependencies.

| Repository | Snapshot | License | Relevance |
|---|---:|---|---|
| `VinGuar/IdeaForge` | `8da7838` | No license file | Closest product analogue: founder profile, five demand feeds, validation report, launch planning |
| `dzhng/deep-research` | `1f8f3e2` | MIT | Small recursive breadth/depth research loop |
| `agent-noah/noah_research` | `b419df8` | MIT | Supervisor, bounded parallel research units, reflection and explicit completion |
| `jolovicdev/shandu` | `e9123bd` | MIT | Source classification, deterministic credibility scoring, quality flags, adaptive continuation |
| `jakkapat-kingthong/Deep-research-agent` | `30407fe` | MIT | Typed claim-to-source contracts, bounded critic loop, citation metrics |

## What is useful for Scout

### 1. Search until a defined evidence gap closes

`open-deep-research` recursively turns findings into narrower follow-up queries. `noah_research` and `shandu` use a supervisor or coverage assessment to decide whether another iteration is justified. Scout currently has strong stage gates, but each model stage receives a suggested fixed search count. The better next step is to derive queries from missing gates: buyer evidence, persona evidence, pricing, native alternatives, reachable channels, or contradictory claims. Stop when the gap closes, results repeat, or the stage budget is exhausted.

### 2. Score the source separately from the opportunity

Shandu classifies sources as primary, official, technical, corporate, community, marketing, aggregator, and other classes. A deterministic function applies penalties for missing dates, anonymous authorship, promotion, and secondhand reporting. Its adaptive loop counts only evidence with adequate confidence and credibility. Scout already checks access, duplication, dates, firsthand status, and independent actors, but should add source-class and quality flags rather than leaving all source quality inside prose.

### 3. Bind atomic claims to evidence

The grounded research agent represents the report as atomic claims with non-empty source IDs and rejects references absent from the source ledger. Scout already rejects unknown source IDs at several boundaries, which is a good base. It should go further by recording claim type and entailment status for important market statements such as price, spending, persona, workflow consequence, adoption, and switching behavior. A valid URL alone does not prove that its excerpt supports the claim.

### 4. Make source collection concurrent but balanced

IdeaForge fetches five channels concurrently, logs empty sources, normalizes snippets, deduplicates them, and caps the combined corpus. Scout's new API seed collectors are resilient but currently run sequentially. Concurrent collection will reduce startup latency. The combined cap should be allocated by evidence class or source, so a high-volume GitHub query cannot crowd out procurement or buyer evidence.

### 5. Keep bounded budgets and explicit stop reasons

The mature research agents expose maximum iterations, parallelism, results per query, pages per task, retries, and completion reasons. Scout has a wall-clock limit and stage checkpoints. It should also record per-stage query/page budgets and stop reasons such as `gate_satisfied`, `results_repeating`, `source_unavailable`, or `budget_exhausted`.

## What not to copy

- IdeaForge has no repository license, so its source code must not be copied. Its public behavior can inform independent design.
- IdeaForge's single build-gate score conflicts with Scout's explicit multidimensional scoring and Unknown values.
- Raw snippets should remain leads. Calling social snippets primary evidence without opening and classifying the original page is too weak for Scout's recommendations.
- General deep-research systems optimize for comprehensive prose. Scout needs product, market, persona, and solo-founder gates, so a generic report agent is not a replacement for its domain pipeline.
- More agents are not inherently better. Parallel work should be limited to independent evidence gaps and followed by deterministic merging and source checks.

## Recommended implementation order

1. Add source classification, quality flags, and deterministic credibility to `Source`.
2. Add a typed claim ledger for the critical commercial claims and validate claim-to-source references.
3. Replace fixed search guidance with a bounded evidence-gap loop inside each stage.
4. Run API collectors concurrently with per-source quotas and record latency, failures, and stop reasons.
5. Add evaluation fixtures for citation accuracy, critical-gate coverage, false corroboration, and unsupported willingness-to-pay claims.
