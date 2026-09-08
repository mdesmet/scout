# Result Quality Audit — 2026-09-06

## What was tested

- Repeated live searches for AI data infrastructure and dbt/analytics problems.
- A full live product-synthesis run before the dedicated market-scan stage.
- Deterministic evidence gates, interruption and follow-up behavior.
- Browser flows for product/market reports, focused score research, legacy reframing, exports, memory, and mobile layout.
- Product Hunt integration through the structured research contract and UI.

The strongest live comparison produced six related pain records, two product hypotheses, and no build recommendation. It correctly rejected an incident-triage feature already covered by data-observability incumbents. It retained reviewed supplier-price ingestion as a research lead, but found mixed customer segments, existing competitors, no incremental buying evidence, and no reliable reachable-market estimate.

## Defects found and addressed

1. **Issue-level results masqueraded as products.** The previous schema tied one opportunity to one pain. Product synthesis now requires distinct related pains, one buyer/job, recurring value, a workflow, a bounded entry product, and an explicit scope. Feature and bugfix scopes are rejected and hidden from the default Products list.
2. **Competitor research did not gate recommendations.** New checks require sourced direct/adjacent products, native/manual substitutes, a verified pricing model, and a competitive opening score of at least 3 before a recommendation.
3. **Market demand was conflated with product availability.** Buying signals now distinguish firsthand spending/active buying from vendor adoption, funding or pricing. Only firsthand spending or buying intent can satisfy the market-demand gate.
4. **Mixed customer segments could be bundled.** Product hypotheses now declare segment alignment. Mixed or unknown alignment prevents recommendation until one target segment is corroborated.
5. **Reachability and TAM were vague prose.** A supported market now needs a sourced acquisition channel to the budget owner, bottom-up market reasoning, and explicit assumptions. “Unknown” does not pass as a supported estimate.
6. **Competitor sources could be unusable despite named prices.** The live run revealed blank source excerpts. The research contract now requires a short excerpt or an explicitly labeled faithful paraphrase. Empty evidence remains unusable.
7. **Competitor discovery lacked Product Hunt.** The market scan now performs at least two focused Product Hunt searches, records relevant products, launches and positioning, and verifies material features/pricing on official pages. Product Hunt attention does not count as revenue or willingness to pay.
8. **Product and market work competed for one model stage.** A dedicated market-evidence stage now runs before final scoring and skeptical review.
9. **Historical fine-grained reports had no upgrade path.** “Reframe as a product” creates a fresh linked run whose solution can change while preserving the old report.
10. **Market research ran even when no product survived synthesis.** The pipeline now stops before competitor and Product Hunt research when no coherent product thesis exists.

## Current pipeline

1. Dated signal collection.
2. Related customer-pain discovery around plausible buying categories.
3. Product synthesis across pains from the same customer segment.
4. Competitor and market evidence scan, including Product Hunt.
5. Opportunity scoring and market assessment.
6. Skeptical product/market review.
7. Deterministic evidence gates and exports.

## Remaining quality opportunities

- **Blind benchmark set:** create 15–25 research briefs with human-labeled “product / feature / reject” outcomes and compare pipeline versions. Current tests validate rules and workflows, not real-world precision.
- **Source identity resolution:** aliases, employer relationships and copied posts can still look independent. A future entity-resolution layer should preserve uncertainty rather than merge aggressively.
- **Coverage measurement:** report how many queries, source domains, customer accounts, official competitor pages and pricing pages were checked per thesis. Current logs exist but are not summarized as coverage.
- **Independent challenge:** assessment and skeptical review are separate sessions using the same default model. A different model or a rule-based claim audit would reduce correlated errors.
- **Stage budgets and early stopping:** deeper research improved the result but increased latency. Add per-stage time/tool budgets and stop when all candidate theses already fail a hard gate.
- **Market calibration:** public evidence rarely proves budgets or buyer counts. The most important next data is still interviews, pricing tests and paid pilots; outcome tracking exists but has little data.
- **Product Hunt access quality:** public search may miss products hidden behind dynamic pages or login requirements. A token-backed Product Hunt API could improve completeness if the user chooses to configure it.
- **Longitudinal tracking:** revisit promising categories on a schedule and measure new competitors, pricing changes, launches and repeated customer pain instead of treating every search as a snapshot.

## Verification

- 83 backend tests cover the final gates, including Product Hunt documentation and early stopping.
- 7 browser tests cover the product/market view, reframing, score follow-ups, memory, exports, and mobile layout.
- Live research correctly returned zero recommended opportunities when market evidence was insufficient.
- A final live run found four pain clusters but no coherent aligned product thesis, then completed through the new early-stop path without manufacturing an opportunity.
- The local server is running the latest build at http://127.0.0.1:8765.

Warnings from the test stack concern upstream TestClient deprecations and do not affect application behavior.
