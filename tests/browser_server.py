"""Isolated deterministic browser-test server. Never calls Codex or external sites."""
import os
import tempfile
import time
import json
import copy
from scout.app import create_app
from scout.engine import Engine
from scout.demo import sample_payload, synthesis_payload
from scout.models import Discovery

def provider(stage,prompt,directory,check,emit):
    for _ in range(8):
        check();time.sleep(.1)
    if stage=="prompt_discovery":
        return dict(summary="Two synthetic directions matched the saved founder context.",prompts=[dict(id="D1",title="Release assurance for AI analytics",scout_keywords="AI analytics release assurance",scout_context="Verify recurring release-review pain, distinct user and buyer, existing spending, alternatives, and a narrow solo-founder entry point.",problem_signal="Analytics teams repeatedly review generated metrics before customer delivery.",user_persona="Analytics engineer",buyer_persona="Analytics engineering lead",why_founder_fit="Matches data engineering and dbt experience.",why_now="More teams are publishing AI-generated analysis.",source_ids=["PS1"],uncertainties=["Real willingness to pay remains unverified."])],sources=[dict(id="PS1",url="https://example.com/prompt-signal",title="Synthetic problem signal",excerpt="We review these metrics manually every week.",signal_type="pain",published_at="2026-09-01")],searches=["Synthetic Reddit, Product Hunt, and GitHub search"],limitations=["Synthetic browser fixture; no external search."]),dict(stage=stage,usage=[],web_calls_observed=0)
    data=sample_payload()
    if stage in ("investigate","verify_investigation"):
        brief=json.loads(prompt.split("FOLLOW-UP BRIEF:\n",1)[1].split("\nIMMUTABLE BASELINE",1)[0])
        baseline=json.loads(prompt.split("IMMUTABLE BASELINE (EVIDENCE TO CHECK):\n",1)[1].split("\nDRAFT TO CHALLENGE:",1)[0])
        o=next(o for o in baseline["opportunities"] if o["id"]==brief["opportunity_id"])
        score=copy.deepcopy(next(s for s in o["scores"] if s["dimension"]==brief["focus_dimension"]))
        score.update(value=4,confidence="medium",source_ids=["N1"],rationale="Synthetic buyer reports a paid workaround.")
        source=copy.deepcopy(data["sources"][0]);source.update(id="N1",url="https://example.com/new-buyer",speaker="Example buyer C",organization="Example C",excerpt="We pay for this recurring manual workflow.")
        result=dict(summary="Focused synthetic test result.",score=score,sources=[source],findings=[dict(claim="A synthetic buyer reports paying for a workaround.",evidence_type="spending",source_ids=["N1"])],conclusion="The follow-up found a new firsthand account of spending on this workflow. A paid product pilot is still required.",status="worth_validating",ranking_reason="New buying evidence improves this score only.",search_notes=["Synthetic browser test, no web access."],limitations=["Synthetic test data."])
        return result,dict(stage=stage,usage=[],web_calls_observed=0)
    if "Followup unknown demo" in prompt:
        data["opportunities"][0]["scores"][2].update(value=None,confidence="low",source_ids=[])
        data["opportunities"][0]["status"]="watch"
    if "Feature-only test" in prompt:
        data["opportunities"][0]["product"]["scope"]="feature"
    if stage=="synthesis":
        result=synthesis_payload(data)
        if "Empty synthesis trail test" in prompt:result["product_hypotheses"]=[]
        return result,dict(stage=stage,usage=[],web_calls_observed=0)
    if stage=="market_scan":
        product=synthesis_payload(data);market=data["opportunities"][0]["market"]
        product["market_candidates"]=[dict(product_name=data["opportunities"][0]["product"]["name"],competitors=data["opportunities"][0]["competitors"],buying_signals=market["buying_signals"],acquisition_channels=market["acquisition_channels"],bottom_up_market_evidence=market["bottom_up_market_estimate"],counterevidence=market["counterevidence"],source_ids=market["source_ids"],product_hunt_checks=[],product_hunt_search_notes=["Synthetic Product Hunt search returned no evidence."])]
        return product,dict(stage=stage,usage=[],web_calls_observed=0)
    if stage=="pain":data={k:data[k] for k in Discovery.model_fields}
    return data,dict(stage=stage,usage=[],web_calls_observed=0)

def factory(store):
    return Engine(store,provider=provider,collector=lambda *args:dict(stories=[],searches=[],discussions=[]),trending_collector=lambda *args:([],[]))

app=create_app(tempfile.mkdtemp(prefix="scout-browser-"),engine_factory=factory)
