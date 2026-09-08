from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

DIMENSIONS = {
    "pain_severity": ("Pain severity", "1: minor annoyance; 3: material repeated work; 5: severe documented operational or financial consequences"),
    "pain_frequency": ("Pain frequency", "1: exceptional; 3: monthly or periodic; 5: daily or pervasive in the target workflow"),
    "willingness_to_pay": ("Willingness to pay", "1: documented refusal or no viable budget; 3: paid workaround or active buying intent; 5: repeated actual spending to solve the same pain. Lack of evidence is Unknown, not 1."),
    "demand_momentum": ("Demand momentum", "1: corroborated decline; 3: steady need; 5: multiple dated catalysts increasing need. Funding or excitement alone is insufficient."),
    "competitive_opening": ("Competitive opening", "1: existing alternatives demonstrably solve it; 3: segment-specific gap; 5: documented unmet need despite alternatives"),
    "customer_reachability": ("Customer reachability", "1: unidentified buyer or inaccessible channel; 3: identifiable audience; 5: concrete repeatable channel to budget owners"),
    "solo_feasibility": ("Solo feasibility", "1: requires a team or inaccessible assets; 3: bounded product with material dependencies; 5: one founder can build, sell and support a narrow product"),
    "economic_potential": ("Economic potential", "1: costs swamp plausible revenue; 3: plausible bounded costs and price; 5: strong recurring value and supported favorable unit economics"),
    "defensibility": ("Defensibility", "1: trivial copy with no accumulated advantage; 3: useful workflow or integration depth; 5: defensible access, distribution or cumulative data advantage"),
}
RUBRIC_VERSION = "2.0"

class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")

class Source(Strict):
    id: str
    url: str
    title: str
    published_at: str | None
    retrieved_at: str
    kind: Literal["firsthand", "vendor", "pricing", "documentation", "research", "news", "directory"]
    speaker: str | None
    organization: str | None
    origin_url: str | None
    excerpt: str
    supports: str
    accessed: bool

class TrailItem(Strict):
    id: str
    stage: Literal["pain_discovery", "product_synthesis", "market_scan", "assessment", "challenge", "evidence_gate"]
    subject_type: Literal["pain", "product", "market", "opportunity", "research_path"]
    subject_id: str
    title: str
    decision: Literal["found", "advanced", "merged", "watch", "rejected", "insufficient_evidence", "skipped"]
    summary: str
    reasons: list[str]
    source_ids: list[str]
    related_ids: list[str]
    next_evidence: list[str]

class Pain(Strict):
    id: str
    title: str
    customer: str
    buyer: str
    workflow: str
    problem: str
    frequency: str
    consequence: str
    workaround: str
    spending_evidence: str
    source_ids: list[str]
    consequence_source_ids: list[str]
    uncertainties: list[str]

class Discovery(Strict):
    summary: str
    pains: list[Pain]
    sources: list[Source]
    search_notes: list[str]
    limitations: list[str]
    research_trail: list[TrailItem] = Field(default_factory=list)

Dimension = Literal["pain_severity", "pain_frequency", "willingness_to_pay", "demand_momentum", "competitive_opening", "customer_reachability", "solo_feasibility", "economic_potential", "defensibility"]

class Score(Strict):
    dimension: Dimension
    value: int | None = Field(ge=1, le=5)
    confidence: Literal["low", "medium", "high"]
    rationale: str
    source_ids: list[str]
    assumptions: list[str]
    counterevidence: str
    next_evidence: str

class Competitor(Strict):
    name: str
    offering: str
    price_evidence: str
    gap: str
    source_ids: list[str]
    category: Literal["direct", "adjacent", "native", "manual"] | None = None
    target_customer: str = ""
    adoption_evidence: str = ""
    switching_costs: str = ""
    pricing_source_ids: list[str] = Field(default_factory=list)

class ProductThesis(Strict):
    name: str
    category: str
    target_customer: str
    buyer: str
    job_to_be_done: str
    related_pain_ids: list[str]
    workflow_steps: list[str]
    why_one_product: str
    recurring_value: str
    entry_point: str
    expansion_path: str
    scope: Literal["standalone_product", "feature", "bugfix", "service", "unknown"]
    incumbent_absorption_risk: str
    source_ids: list[str]
    segment_alignment: Literal["aligned", "mixed", "unknown"] = "unknown"
    segment_alignment_reason: str = ""
    user_persona: str = ""
    user_job: str = ""
    buyer_persona: str = ""
    buyer_goal: str = ""
    buyer_user_relationship: Literal["same_person", "different_people", "unknown"] = "unknown"
    purchase_trigger: str = ""
    persona_source_ids: list[str] = Field(default_factory=list)

class MarketSignal(Strict):
    claim: str
    kind: Literal["customer_spending", "active_buying", "paid_adoption", "growth_driver", "counterevidence"]
    source_ids: list[str]

class ProductHuntCheck(Strict):
    product_name: str
    url: str
    launch_date: str | None
    positioning: str
    relevance: str
    source_ids: list[str]

class AcquisitionChannel(Strict):
    name: str
    target_role: str
    evidence: str
    source_ids: list[str]

class MarketAssessment(Strict):
    verdict: Literal["supported", "unproven", "contradicted"]
    category: str
    target_segment: str
    buying_signals: list[MarketSignal]
    reachable_market: str
    pricing_logic: str
    differentiation: str
    switching_trigger: str
    competitor_search_notes: list[str]
    counterevidence: list[str]
    remaining_validation: list[str]
    source_ids: list[str]
    acquisition_channels: list[AcquisitionChannel] = Field(default_factory=list)
    bottom_up_market_estimate: str = ""
    market_size_assumptions: list[str] = Field(default_factory=list)
    product_hunt_checks: list[ProductHuntCheck] = Field(default_factory=list)
    product_hunt_search_notes: list[str] = Field(default_factory=list)

class MarketCandidate(Strict):
    product_name: str
    competitors: list[Competitor]
    buying_signals: list[MarketSignal]
    acquisition_channels: list[AcquisitionChannel]
    bottom_up_market_evidence: str
    counterevidence: list[str]
    source_ids: list[str]
    product_hunt_checks: list[ProductHuntCheck]
    product_hunt_search_notes: list[str]

class ProductDiscovery(Discovery):
    product_hypotheses: list[ProductThesis]

class MarketDiscovery(ProductDiscovery):
    market_candidates: list[MarketCandidate]

class Opportunity(Strict):
    id: str
    pain_id: str
    title: str
    thesis: str
    solution: str
    why_now: str
    why_now_source_ids: list[str]
    buyer: str
    status: Literal["worth_validating", "watch", "reject"]
    ranking_reason: str
    founder_fit: str
    scores: list[Score]
    competitors: list[Competitor]
    mvp: str
    build_effort: str
    upfront_cost: str
    monthly_cost: str
    support_burden: str
    sales_effort: str
    time_to_pilot: str
    dependencies: list[str]
    solo_blockers: list[str]
    constraint_conflicts: list[str]
    acquisition: str
    validation_experiment: str
    kill_criteria: list[str]
    uncertainties: list[str]
    changes_since_previous: str
    product: ProductThesis | None = None
    market: MarketAssessment | None = None

class Report(Discovery):
    opportunities: list[Opportunity]
    rejected_directions: list[str]

class RunInput(Strict):
    keywords: str = Field(min_length=2, max_length=1000)
    context: str = Field(default="", max_length=12000)
    days: int = Field(default=90, ge=1, le=730)
    max_opportunities: int = Field(default=5, ge=1, le=5)
    timeout_minutes: int = Field(default=20, ge=1, le=60)

class PromptDiscoveryInput(Strict):
    focus: str = Field(default="", max_length=3000)
    max_prompts: int = Field(default=5, ge=2, le=8)
    timeout_minutes: int = Field(default=8, ge=2, le=20)

class PromptSource(Strict):
    id: str
    url: str
    title: str
    excerpt: str
    signal_type: Literal["pain", "user_persona", "buyer", "budget", "competition", "timing"]
    published_at: str | None
    platform: Literal["reddit", "product_hunt", "github", "marketplace", "community", "jobs", "procurement", "regulatory", "other"] = "other"
    trend_window: Literal["daily", "weekly", "monthly", "none"] = "none"

class ScoutPrompt(Strict):
    id: str
    title: str
    scout_keywords: str
    scout_context: str
    problem_signal: str
    user_persona: str
    buyer_persona: str
    why_founder_fit: str
    why_now: str
    source_ids: list[str]
    uncertainties: list[str]

class PromptDiscoveryResult(Strict):
    summary: str
    prompts: list[ScoutPrompt]
    sources: list[PromptSource]
    searches: list[str]
    limitations: list[str]

class InvestigationInput(Strict):
    opportunity_id: str = Field(min_length=1, max_length=200)
    dimension: Dimension
    guidance: str = Field(default="", max_length=5000)
    timeout_minutes: int = Field(default=10, ge=1, le=30)

class ReframeInput(Strict):
    opportunity_id: str = Field(min_length=1, max_length=200)
    guidance: str = Field(default="", max_length=5000)
    timeout_minutes: int = Field(default=20, ge=1, le=60)

class Finding(Strict):
    claim: str
    evidence_type: Literal["spending", "buying_intent", "operating_cost", "counterevidence", "other"]
    source_ids: list[str]

class InvestigationResult(Strict):
    summary: str
    score: Score
    sources: list[Source]
    findings: list[Finding]
    conclusion: str
    status: Literal["worth_validating", "watch", "reject"]
    ranking_reason: str
    search_notes: list[str]
    limitations: list[str]

class Steering(Strict):
    message: str = Field(min_length=2, max_length=5000)
    remember: bool = False
    impact: Literal["auto", "source_refinement", "market_refinement", "product_reframing", "full_restart"] = "auto"

class Feedback(Strict):
    run_id: str
    opportunity_id: str | None = None
    kind: Literal["interested", "reject", "correction", "outcome", "direction"]
    reason: str = Field(min_length=1, max_length=5000)
    remember: bool = False
    outcome: Literal["interview", "pilot", "paid", "no_demand", "other"] | None = None
    amount: float | None = Field(default=None, ge=0)
    preference_tag: Literal["self_serve", "emerging_markets", "low_operations", "solo_buildable", "accessible_data", "other"] | None = None

    @model_validator(mode="after")
    def validate_outcome(self):
        if self.kind == "outcome" and self.outcome is None:
            raise ValueError("Choose the type of customer outcome.")
        if self.kind != "outcome" and (self.outcome is not None or self.amount is not None):
            raise ValueError("Outcome details belong only to outcome feedback.")
        return self

class MemoryEdit(Strict):
    text: str = Field(min_length=1, max_length=5000)
    active: bool = True
    confirmed: bool = True

class ProfileInput(Strict):
    skills: str = Field(default="", max_length=3000)
    interests: str = Field(default="Emerging AI and data opportunities", max_length=3000)
    customer_access: str = Field(default="", max_length=3000)
    geography: str = Field(default="", max_length=1000)
    time_available: str = Field(default="", max_length=1000)
    budget: str = Field(default="", max_length=1000)
    assets: str = Field(default="", max_length=3000)
    exclusions: str = Field(default="", max_length=3000)

def output_schema(model):
    schema = model.model_json_schema()
    def visit(v):
        if isinstance(v, dict):
            v.pop("default", None)
            if v.get("type") == "object":
                v["additionalProperties"] = False
                v["required"] = list(v.get("properties", {}))
            for child in v.values():
                visit(child)
        elif isinstance(v, list):
            for child in v:
                visit(child)
    visit(schema)
    return schema
