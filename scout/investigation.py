"""Narrow follow-ups: immutable parent evidence, one opportunity, one score."""
import copy
import json
from .models import (DIMENSIONS, Report, Source, Pain, Opportunity, Score,
                     InvestigationResult)
from .policy import evaluate
from .research import BASE_PROMPT
from .store import now

FOCUS_HINTS = {
    "willingness_to_pay": "Look for actual paid workarounds, customers replacing a paid alternative, requests for vendor quotes, named budget owners, or accepted paid pilots for this SAME problem. Vendor price lists, upvotes, developer effort, and employee costs alone are NOT willingness to buy this proposed product. Classify findings as spending, buying_intent, operating_cost, counterevidence, or other.",
    "pain_frequency": "Find firsthand evidence of how often this exact workflow problem occurs. One incident or many reposts do not establish recurrence.",
    "pain_severity": "Find documented time, financial, or operational consequences for the same target customer. Distinguish measured costs from estimates.",
    "demand_momentum": "Find dated changes that increase this need and counterevidence. A launch or funding round alone is insufficient; do not fabricate a growth rate.",
    "competitive_opening": "Verify current alternatives and native platform features. Find a documented unmet need in the same buyer segment.",
    "customer_reachability": "Identify concrete buyer communities and a feasible acquisition channel. Public users are not automatically budget owners.",
    "solo_feasibility": "Investigate implementation, data access, integration maintenance, support, and selling for one founder. Do not assume private partnerships.",
    "economic_potential": "Investigate support and delivery costs, renewal value, usage expenses and plausible pricing. Label estimates and price hypotheses.",
    "defensibility": "Test whether this same product can develop a real data, workflow, integration, or distribution advantage beyond code that is easy to copy.",
}

def clean_report(report):
    data = {k:copy.deepcopy(report[k]) for k in Report.model_fields}
    for key, model in [("sources",Source),("pains",Pain),("opportunities",Opportunity)]:
        data[key] = [{k:v for k,v in item.items() if k in model.model_fields} for item in data[key]]
    return data

def focused_prompt(stage, run, draft=None):
    base = run["parent_report_snapshot"]
    opportunity = next(o for o in base["opportunities"] if o["id"] == run["parent_opportunity_id"])
    dimension = run["focus_dimension"]
    instructions = """TARGETED FOLLOW-UP. Keep the exact customer, pain, buyer, and proposed solution.
Do NOT brainstorm alternatives, broaden the buyer segment, or run broad keyword discovery.
The usual 20% adjacent discovery instruction does not apply to this focused investigation.
Investigate only the selected score dimension. The other eight scores are historical and unchanged.
Use public web search to read primary sources and firsthand customer accounts. Existing evidence
is a baseline, not permission to assume its conclusions. Search for counterevidence too.
Return InvestigationResult: one score for EXACTLY the selected dimension, source-linked findings,
a conclusion explaining what changed (or why nothing can be established), and recommended status.
Return sources only for additional observations. New IDs must not collide with any baseline ID.
Never silently rewrite an old source. Cite baseline IDs where using existing evidence.
In the verification stage, return ALL retained additional sources and findings, not just your changes.
Every finding must cite at least one source. An empty findings/sources list is acceptable.
Keep Unknown when support remains insufficient. Lack of evidence is not a negative buying decision.
Do not raise a score merely because the user requested more evidence.
Status may only improve if the ORIGINAL opportunity also passes the other recommendation gates.
Keep original solo blockers and founder constraints. A prior rejection needs material new evidence.
Use approximately 4-6 focused searches plus relevant source reads; stop when the evidence is exhausted.
"""
    if stage == "verify_investigation":
        instructions += "\nSKEPTICAL VERIFICATION: inspect the proposed findings, verify their original sources, and challenge attribution, relevance, buying intent and the proposed score. Return a complete revised InvestigationResult, even if it finds nothing.\n"
    context = dict(date=now()[:10], focus_dimension=dimension, scoring_anchor=DIMENSIONS[dimension],
                   opportunity_id=opportunity["id"], title=opportunity["title"],
                   guidance=run["investigation_guidance"], steering=run["steering"],
                   feedback=run["feedback_snapshot"], profile=run["profile_snapshot"],
                   memory=run["memory_snapshot"])
    return (BASE_PROMPT+"\n"+instructions+"\nFOCUS:\n"+FOCUS_HINTS[dimension]
            +"\nFOLLOW-UP BRIEF:\n"+json.dumps(context,ensure_ascii=False)
            +"\nIMMUTABLE BASELINE (EVIDENCE TO CHECK):\n"+json.dumps(base,ensure_ascii=False)
            +"\nDRAFT TO CHALLENGE:\n"+json.dumps(draft,ensure_ascii=False))

def merge_investigation(run, payload):
    result = InvestigationResult.model_validate(payload).model_dump()
    dimension = run["focus_dimension"]
    if result["score"]["dimension"] != dimension:
        raise ValueError("Investigation returned the wrong score dimension.")
    original = run["parent_report_snapshot"]
    data = clean_report(original)
    selected = next(o for o in data["opportunities"] if o["id"] == run["parent_opportunity_id"])
    original_selected = next(o for o in original["opportunities"] if o["id"] == selected["id"])
    data["opportunities"] = [selected]
    linked_pains = set((selected.get("product") or {}).get("related_pain_ids", [])) | {selected["pain_id"]}
    data["pains"] = [p for p in data["pains"] if p["id"] in linked_pains]
    old_ids = {s["id"] for s in data["sources"]}
    new_ids = [s["id"] for s in result["sources"]]
    if len(new_ids) != len(set(new_ids)) or old_ids.intersection(new_ids):
        raise ValueError("Follow-up source IDs must be new and unique; parent evidence is immutable.")
    data["sources"].extend(result["sources"])
    ids = old_ids | set(new_ids)
    for finding in result["findings"]:
        if not finding["claim"].strip() or not finding["source_ids"]:
            raise ValueError("Every investigation finding needs a claim and supporting sources.")
        if any(ref not in ids for ref in finding["source_ids"]):
            raise ValueError("Investigation finding cites an unknown source.")
    selected["scores"] = [result["score"] if s["dimension"] == dimension else s for s in selected["scores"]]
    selected["status"] = result["status"]
    selected["ranking_reason"] = result["ranking_reason"]
    selected["changes_since_previous"] = result["conclusion"]
    # Keep the original pain record and present fresh findings as a separate addendum.
    data["summary"] = result["summary"]
    data["search_notes"].extend(result["search_notes"])
    data["limitations"].extend(result["limitations"])
    data["limitations"].append("Focused follow-up: only "+DIMENSIONS[dimension][0]+" was reassessed. Other scores and original pain statements are retained from the parent report; new findings are an addendum.")
    report = evaluate(data,days=run["days"],max_opportunities=1)
    o = report["opportunities"][0]
    before = copy.deepcopy(next(s for s in original_selected["scores"] if s["dimension"] == dimension))
    after = next(s for s in o["scores"] if s["dimension"] == dimension)
    usable = {s["id"]:s for s in report["sources"] if s["usable"]}
    # Positive buying evidence must refer to a firsthand account, not just vendor pricing.
    if dimension == "willingness_to_pay" and after["value"] is not None and after["value"] >= 3:
        buying_sources = {ref for f in result["findings"] if f["evidence_type"] in ("spending","buying_intent") for ref in f["source_ids"]}
        if not any(ref in buying_sources and ref in usable and usable[ref]["kind"] == "firsthand" for ref in after["source_ids"]):
            after.update(value=None,confidence="low")
            o["warnings"].append("No usable firsthand spending or buying-intent finding supports a positive willingness-to-pay score; retained Unknown.")
            if o["status"] == "worth_validating": o["status"] = "watch"
    # Do not let time passing or new unrelated sources rewrite the other eight assessments.
    o["scores"] = [after if s["dimension"] == dimension else copy.deepcopy(next(old for old in original_selected["scores"] if old["dimension"] == s["dimension"])) for s in o["scores"]]
    o["previous_status"] = original_selected["status"]
    o["score_changes"] = [dict(dimension=dimension,before=before["value"],after=after["value"],before_confidence=before["confidence"],after_confidence=after["confidence"])] if before["value"] != after["value"] or before["confidence"] != after["confidence"] else []
    o["fingerprint"] = original_selected.get("fingerprint",o["fingerprint"])
    conclusion = result["conclusion"]
    if after["value"] != result["score"]["value"]:
        conclusion += " Evidence checks did not support the proposed score; the published assessment is " + ("Unknown" if after["value"] is None else str(after["value"])+"/5") + "."
    o["changes_since_previous"] = conclusion
    report["investigation"] = dict(parent_run_id=run["parent_run_id"],opportunity_id=o["id"],
                                   dimension=dimension,before=before,after=copy.deepcopy(after),
                                   new_source_ids=new_ids,findings=result["findings"],
                                   conclusion=conclusion,previous_status=original_selected["status"],
                                   status=o["status"],score_changed=before["value"]!=after["value"],
                                   confidence_changed=before["confidence"]!=after["confidence"])
    return report
