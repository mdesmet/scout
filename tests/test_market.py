import copy
import pytest
from fastapi.testclient import TestClient
from scout.app import create_app
from scout.demo import sample_payload, synthesis_payload
from scout.engine import Engine
from scout.models import Discovery, ProductDiscovery, output_schema
from scout.policy import evaluate
from scout.store import Store
from tests.test_scout import completed_run,fake_provider,fake_collector

@pytest.mark.parametrize("scope",["bugfix","feature"])
def test_isolated_issue_cannot_be_recommended_even_with_high_scores(scope):
    p=sample_payload()
    p["opportunities"][0]["product"]["scope"]=scope
    for s in p["opportunities"][0]["scores"]:s["value"]=5
    o=evaluate(p)["opportunities"][0]
    assert o["status"]=="reject"
    assert not o["market_checks"]["product_supported"]

@pytest.mark.parametrize("case",["one_pain","duplicate_ids","same_problem","unsupported_pain","empty_product_sources"])
def test_product_requires_distinct_supported_related_pains(case):
    p=sample_payload();product=p["opportunities"][0]["product"]
    if case=="one_pain":product["related_pain_ids"]=["P1"]
    if case=="duplicate_ids":product["related_pain_ids"]=["P1","P1"]
    if case=="same_problem":p["pains"][1]["problem"]=p["pains"][0]["problem"]
    if case=="unsupported_pain":p["pains"][1]["source_ids"]=[]
    if case=="empty_product_sources":product["source_ids"]=[]
    o=evaluate(p)["opportunities"][0]
    assert not o["market_checks"]["product_supported"] and o["status"]=="watch"

@pytest.mark.parametrize("case",["no_competitors","no_substitute","no_pricing","empty_market","pricing_is_not_demand","weak_gap","unproven"])
def test_market_evidence_is_a_real_gate(case):
    p=sample_payload();o=p["opportunities"][0]
    if case=="no_competitors":o["competitors"]=[]
    if case=="no_substitute":o["competitors"][1]["category"]="adjacent"
    if case=="no_pricing":o["competitors"][0]["pricing_source_ids"]=[]
    if case=="empty_market":o["market"]=None
    if case=="pricing_is_not_demand":o["market"]["buying_signals"][0]["source_ids"]=["S4"]
    if case=="weak_gap":next(s for s in o["scores"] if s["dimension"]=="competitive_opening")["value"]=2
    if case=="unproven":o["market"]["verdict"]="unproven"
    result=evaluate(p)["opportunities"][0]
    assert result["status"]=="watch"

@pytest.mark.parametrize("case",["mixed_segment","no_channel","unsourced_channel","unknown_bottom_up","no_assumptions","no_product_hunt_search"])
def test_segment_reachability_and_bottom_up_market_are_gates(case):
    p=sample_payload();o=p["opportunities"][0]
    if case=="mixed_segment":o["product"]["segment_alignment"]="mixed"
    if case=="no_channel":o["market"]["acquisition_channels"]=[]
    if case=="unsourced_channel":o["market"]["acquisition_channels"][0]["source_ids"]=[]
    if case=="unknown_bottom_up":o["market"]["bottom_up_market_estimate"]="Unknown; buyer count has not been established."
    if case=="no_assumptions":o["market"]["market_size_assumptions"]=[]
    if case=="no_product_hunt_search":o["market"]["product_hunt_search_notes"]=[]
    result=evaluate(p)["opportunities"][0]
    assert result["status"]=="watch"

def test_empty_competitor_evidence_does_not_count():
    p=sample_payload();p["sources"][2]["excerpt"]="";p["sources"][3]["excerpt"]=""
    result=evaluate(p)["opportunities"][0]
    assert not result["market_checks"]["competition_checked"]
    assert result["status"]=="watch"

def test_supported_product_market_is_not_rejected_for_having_competitors():
    report=evaluate(sample_payload())
    o=report["opportunities"][0]
    assert report["rubric_version"]=="2.0"
    assert o["market_checks"]["passed"] and o["status"]=="worth_validating"
    assert o["market_checks"]["persona_supported"]

@pytest.mark.parametrize("field",["user_persona","user_job","buyer_persona","buyer_goal","purchase_trigger"])
def test_product_requires_a_sourced_user_and_buyer_path(field):
    p=sample_payload();p["opportunities"][0]["product"][field]=""
    o=evaluate(p)["opportunities"][0]
    assert not o["market_checks"]["persona_supported"]
    assert not o["market_checks"]["product_supported"]
    assert o["status"]=="watch"

def test_persona_relationship_and_sources_are_required():
    p=sample_payload();p["opportunities"][0]["product"]["buyer_user_relationship"]="unknown"
    assert not evaluate(p)["opportunities"][0]["market_checks"]["persona_supported"]
    p=sample_payload();p["opportunities"][0]["product"]["persona_source_ids"]=[]
    assert not evaluate(p)["opportunities"][0]["market_checks"]["persona_supported"]

def test_contradicted_market_rejected():
    p=sample_payload();p["opportunities"][0]["market"]["verdict"]="contradicted"
    assert evaluate(p)["opportunities"][0]["status"]=="reject"

def test_unresolved_product_source_and_pain_ids_rejected():
    p=sample_payload();p["opportunities"][0]["product"]["related_pain_ids"].append("NONEXISTENT")
    with pytest.raises(ValueError):evaluate(p)
    p=sample_payload();p["opportunities"][0]["market"]["buying_signals"][0]["source_ids"]=["FAKE"]
    with pytest.raises(ValueError):evaluate(p)

def test_legacy_report_stays_readable_but_cannot_pass_new_market_gates():
    p=sample_payload()
    o=p["opportunities"][0]
    o.pop("product");o.pop("market")
    for c in o["competitors"]:
        for key in ["category","target_customer","adoption_evidence","switching_costs","pricing_source_ids"]:c.pop(key,None)
    r=evaluate(p)
    assert r["opportunities"][0]["status"]=="watch"
    assert r["opportunities"][0]["product"] is None

def test_reframe_runs_product_synthesis_without_mutating_parent(tmp_path):
    s=Store(tmp_path/"data");parent=completed_run(s);snapshot=copy.deepcopy(parent)
    e=Engine(s,provider=fake_provider,collector=fake_collector)
    child=e.reframe(parent["id"],dict(opportunity_id="O1",guidance="Find a product market rather than a patch."))
    assert child["reframed_from_run_id"]==parent["id"]
    assert "parent_run_id" not in child
    assert child["reframe_seed"]["previous_opportunity"]["id"]=="O1"
    e.execute(child)
    result=s.get("run",child["id"])
    assert result["status"]=="completed"
    assert "synthesis" in result["checkpoints"]["1"]
    assert result["report"]["opportunities"][0]["market_checks"]["passed"]
    assert s.get("run",parent["id"])==snapshot

def test_reframe_route_rejects_unknown_opportunity(tmp_path):
    app=create_app(tmp_path/"api",start_worker=False)
    parent=completed_run(app.state.store)
    with TestClient(app) as client:
        route="/api/runs/"+parent["id"]+"/reframe"
        assert client.post(route,json={"opportunity_id":"missing"}).status_code==404
        response=client.post(route,json={"opportunity_id":"O1"})
        assert response.status_code==200
        assert response.json()["reframed_from_run_id"]==parent["id"]
        assert "reframe_seed" not in client.get("/api/runs").json()[0]

def test_exports_include_product_and_market(tmp_path):
    from scout.reports import export
    s=Store(tmp_path/"data");r=completed_run(s)
    for fmt in ("md","html","csv"):
        content=export(r,fmt)[0]
        assert "Analytics quality and release management" in content
    assert "Related pains: P1, P2" in export(r,"md")[0]
    assert "User persona" in export(r,"md")[0] and "Buyer persona" in export(r,"md")[0]

def test_resuming_old_partial_run_reruns_new_pipeline_and_preserves_evidence(tmp_path):
    s=Store(tmp_path/"data");e=Engine(s,provider=fake_provider,collector=fake_collector)
    parent=completed_run(s)
    parent.update(status="partial",pipeline_version=1)
    old=copy.deepcopy(parent["checkpoints"])
    s.put("run",parent["id"],parent)
    resumed=e.control(parent["id"],"resume")
    assert resumed["revision"]==2 and resumed["report"] is None
    assert resumed["checkpoints"]==old
    e.execute(resumed)
    final=s.get("run",parent["id"])
    assert final["status"]=="completed"
    assert "synthesis" in final["checkpoints"]["2"]
    assert final["checkpoints"]["1"]==old["1"]

def test_empty_product_synthesis_stops_before_market_research(tmp_path):
    s=Store(tmp_path/"data");calls=[]
    def provider(stage,prompt,directory,check,emit):
        calls.append(stage)
        result,usage=fake_provider(stage,prompt,directory,check,emit)
        if stage=="synthesis":result["product_hypotheses"]=[]
        return result,usage
    e=Engine(s,provider=provider,collector=fake_collector)
    run=e.create({"keywords":"No coherent market"})
    e.execute(run)
    final=s.get("run",run["id"])
    assert final["status"]=="completed"
    assert calls==["pain","synthesis"]
    assert final["report"]["opportunities"]==[]
    assert "market research stopped early" in final["message"].lower()
    assert "market_scan" not in final["checkpoints"]["1"]
    trail=final["report"]["research_trail"]
    assert any(t["subject_type"]=="pain" and t["decision"]=="found" and t["source_ids"] for t in trail)
    rejected=next(t for t in trail if t["subject_id"]=="no-product")
    assert rejected["decision"]=="rejected" and rejected["reasons"] and rejected["next_evidence"]

def test_full_report_has_cumulative_source_linked_decision_trail(tmp_path):
    s=Store(tmp_path/"data");r=completed_run(s);trail=r["report"]["research_trail"]
    stages={t["stage"] for t in trail}
    assert {"pain_discovery","product_synthesis","market_scan","assessment","challenge","evidence_gate"} <= stages
    source_ids={x["id"] for x in r["report"]["sources"]}
    assert all(set(t["source_ids"]) <= source_ids for t in trail)
    assert all(t["summary"] and t["reasons"] for t in trail)
def test_trail_preserves_sources_dropped_by_later_stage():
    from scout.trail import merge_trail
    p=sample_payload()
    pain={k:copy.deepcopy(p[k]) for k in Discovery.model_fields}
    first=merge_trail("pain",pain)
    synthesis=synthesis_payload(p)
    synthesis["sources"]=[s for s in synthesis["sources"] if s["id"]!="S1"]
    second=merge_trail("synthesis",synthesis,first)
    assert "S1" in {s["id"] for s in second["sources"]}
    assert any("S1" in t["source_ids"] for t in second["research_trail"])
