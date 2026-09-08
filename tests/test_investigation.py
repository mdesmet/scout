import copy
import json
import threading
import time
import pytest
from fastapi.testclient import TestClient
from scout.app import create_app
from scout.demo import create_demo
from scout.engine import Engine
from scout.investigation import merge_investigation, focused_prompt
from scout.models import InvestigationResult, output_schema
from scout.store import Store
from tests.test_scout import completed_run, fake_provider, fake_collector

@pytest.fixture
def setup(tmp_path):
    store=Store(tmp_path/"data")
    parent=completed_run(store)
    parent["report"]["opportunities"][0]["status"]="watch"
    score=next(s for s in parent["report"]["opportunities"][0]["scores"] if s["dimension"]=="willingness_to_pay")
    score.update(value=None,confidence="low",source_ids=[],rationale="Buying evidence is unestablished.")
    store.put("run",parent["id"],parent)
    engine=Engine(store,collector=lambda *args:pytest.fail("Focused research must not rerun broad HN collection."))
    return store,parent,engine

def result(run,*,value=4,source_kind="firsthand",finding_type="spending"):
    source=copy.deepcopy(run["parent_report_snapshot"]["sources"][0])
    source={k:v for k,v in source.items() if k not in ("usable","duplicate","stale","date_known")}
    source.update(id="N1",url="https://new-example.com/customer",speaker="Another buyer",organization="New company",excerpt="We pay for manual review of our generated metrics.",kind=source_kind)
    before=next(s for s in run["parent_report_snapshot"]["opportunities"][0]["scores"] if s["dimension"]==run["focus_dimension"])
    score=copy.deepcopy(before)
    score.update(value=value,confidence="medium",source_ids=["N1"],rationale="New firsthand evidence supports spending on this exact workaround.")
    return dict(summary="Focused investigation of this buying gap.",score=score,sources=[source],
                findings=[dict(claim="A customer reports paying for a workaround.",evidence_type=finding_type,source_ids=["N1"])],
                conclusion="New named buyer evidence establishes spending on the existing workflow; the proposed product itself still needs a paid pilot.",
                status="worth_validating",ranking_reason="Buying evidence improved; other business dimensions remain unchanged.",search_notes=["Searched for paid workarounds."],limitations=["Example evidence is synthetic in tests."])

def child_from(parent,engine):
    return engine.investigate(parent["id"],dict(opportunity_id="O1",dimension="willingness_to_pay",guidance="Find paid workarounds."))

def test_followup_preserves_parent_and_eight_scores(setup):
    store,parent,e=setup
    original=copy.deepcopy(store.get("run",parent["id"]))
    child=child_from(parent,e)
    calls=[]
    def provider(stage,prompt,path,check,emit):
        calls.append(stage);check()
        assert "Do NOT brainstorm" in prompt and "willingness_to_pay" in prompt
        return result(child),dict(stage=stage,usage=[])
    e.provider=provider
    e.execute(child)
    finished=store.get("run",child["id"])
    assert finished["status"]=="completed"
    assert calls==["investigate","verify_investigation"]
    assert store.get("run",parent["id"])==original
    report=finished["report"]
    assert report["investigation"]["before"]["value"] is None
    assert report["investigation"]["after"]["value"]==4
    assert report["investigation"]["new_source_ids"]==["N1"]
    before=parent["report"]["opportunities"][0]
    after=report["opportunities"][0]
    assert before["id"]==after["id"] and before["solution"]==after["solution"] and before["buyer"]==after["buyer"]
    assert [s for s in before["scores"] if s["dimension"]!="willingness_to_pay"]==[s for s in after["scores"] if s["dimension"]!="willingness_to_pay"]
    assert report["pains"][0]["problem"]==parent["report"]["pains"][0]["problem"]
    assert report["sources"][:len(parent["report"]["sources"])]==parent["report"]["sources"]
    assert report["opportunities"][0]["score_changes"][0]["before"] is None

def test_no_new_evidence_is_successful_unchanged_unknown(setup):
    store,parent,e=setup
    child=child_from(parent,e)
    payload=result(child,value=None)
    payload.update(sources=[],findings=[],status="watch",conclusion="No further buying evidence could be established.")
    payload["score"].update(source_ids=[],confidence="low",rationale="Unknown remains appropriate.")
    report=merge_investigation(child,payload)
    assert not report["investigation"]["score_changed"]
    assert report["investigation"]["after"]["value"] is None
    assert report["opportunities"][0]["status"]=="watch"

@pytest.mark.parametrize("source_kind,finding_type",[("pricing","spending"),("vendor","buying_intent"),("firsthand","operating_cost"),("firsthand","other")])
def test_prices_and_frustration_do_not_establish_buying_evidence(setup,source_kind,finding_type):
    _,parent,e=setup
    child=child_from(parent,e)
    report=merge_investigation(child,result(child,source_kind=source_kind,finding_type=finding_type))
    assert report["investigation"]["after"]["value"] is None
    assert report["opportunities"][0]["status"]=="watch"

@pytest.mark.parametrize("mutation",["dimension","source_id","finding_ref","empty_refs"])
def test_scope_and_evidence_violations_fail(setup,mutation):
    _,parent,e=setup
    child=child_from(parent,e)
    payload=result(child)
    if mutation=="dimension":payload["score"]["dimension"]="pain_severity"
    if mutation=="source_id":payload["sources"][0]["id"]="S1"
    if mutation=="finding_ref":payload["findings"][0]["source_ids"]=["missing"]
    if mutation=="empty_refs":payload["findings"][0]["source_ids"]=[]
    with pytest.raises(ValueError):merge_investigation(child,payload)

def test_other_solo_blockers_still_prevent_recommendation(setup):
    _,parent,e=setup
    child=child_from(parent,e)
    child["parent_report_snapshot"]["opportunities"][0]["solo_blockers"]=["Requires an operating team."]
    assert merge_investigation(child,result(child))["opportunities"][0]["status"]=="reject"

def test_failed_verification_resumes_from_focused_checkpoint(setup):
    store,parent,e=setup
    child=child_from(parent,e)
    def fail(stage,*args):
        if stage=="verify_investigation":raise RuntimeError("temporary provider failure")
        return result(child),dict(stage=stage,usage=[])
    e.provider=fail;e.execute(child)
    partial=store.get("run",child["id"])
    assert partial["status"]=="partial" and partial["report"]["investigation"]
    calls=[]
    e.provider=lambda stage,*args:(calls.append(stage) or result(child),dict(stage=stage,usage=[]))
    e.control(child["id"],"resume");e.execute(store.get("run",child["id"]))
    assert calls==["verify_investigation"]
    assert store.get("run",child["id"])["status"]=="completed"

def test_redirect_does_not_publish_obsolete_followup(setup):
    store,parent,e=setup
    child=child_from(parent,e);entered=threading.Event()
    def slow(stage,prompt,path,check,emit):
        entered.set()
        while True:check();time.sleep(.01)
    e.provider=slow
    t=threading.Thread(target=e.execute,args=(child,));t.start()
    assert entered.wait(2)
    e.steer(child["id"],"Focus only on small teams.",False)
    t.join(3)
    current=store.get("run",child["id"])
    assert not t.is_alive() and current["revision"]==2 and current["report"] is None
    assert current["parent_run_id"]==parent["id"]
    assert store.get("run",parent["id"])==parent

def test_source_refinement_during_focused_verification_preserves_investigation(setup):
    store,parent,e=setup
    child=child_from(parent,e)
    child.update(status="partial",stage="verify_investigation")
    child["checkpoints"]["1"]={"investigate":result(child)}
    store.put("run",child["id"],child)
    steered=e.steer(child["id"],"Verify with another firsthand source",False,"source_refinement")
    assert steered["steering"][-1]["restart_from"]=="verify_investigation"
    assert steered["steering"][-1]["preserved_stages"]==["investigate"]
    assert set(steered["checkpoints"]["2"])=={"investigate"}

def test_followup_api_validation_and_lineage(setup):
    store,parent,e=setup
    app=create_app(store.root,start_worker=False)
    with TestClient(app) as client:
        route="/api/runs/"+parent["id"]+"/investigate"
        assert client.post(route,json={"opportunity_id":"O1","dimension":"not-a-dimension"}).status_code==422
        assert client.post(route,json={"opportunity_id":"absent","dimension":"willingness_to_pay"}).status_code==404
        demo=create_demo(store)
        assert client.post("/api/runs/example/investigate",json={"opportunity_id":"O1","dimension":"willingness_to_pay"}).status_code==409
        response=client.post(route,json={"opportunity_id":"O1","dimension":"willingness_to_pay"})
        assert response.status_code==200
        child=response.json()
        assert child["parent_run_id"]==parent["id"] and child["max_opportunities"]==1
        assert "parent_report_snapshot" not in client.get("/api/runs").json()[0]
        assert client.post(route,json={"opportunity_id":"O1","dimension":"willingness_to_pay"}).status_code==409

def test_exports_include_parent_score_diff_and_new_findings(setup):
    from scout.reports import export
    _,parent,e=setup
    child=child_from(parent,e)
    child["report"]=merge_investigation(child,result(child));child["status"]="completed"
    for fmt in ("md","html","json","csv"):
        text=export(child,fmt)[0]
        assert parent["id"] in text
        assert "new-example.com/customer" in text
    assert "Unknown" in export(child,"md")[0]
    assert "4/5" in export(child,"html")[0]

def test_chained_followup_uses_latest_assessment_as_baseline(setup):
    store,parent,e=setup
    first=child_from(parent,e)
    first["report"]=merge_investigation(first,result(first));first["status"]="completed"
    store.put("run",first["id"],first)
    second=child_from(first,e)
    assert next(s for s in second["parent_report_snapshot"]["opportunities"][0]["scores"] if s["dimension"]=="willingness_to_pay")["value"]==4
    assert second["parent_run_id"]==first["id"]

def test_followup_does_not_resurrect_forgotten_memory(setup):
    store,parent,e=setup
    memory=store.memories()[0]
    assert any(m["id"]==memory["id"] for m in parent["memory_snapshot"])
    store.edit_memory(memory["id"],dict(text="",active=False,forgotten=True))
    child=child_from(parent,e)
    assert all(m["id"]!=memory["id"] for m in child["memory_snapshot"])
