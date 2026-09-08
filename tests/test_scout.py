import copy
import json
import threading
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from scout.app import create_app
from scout.demo import sample_payload, synthesis_payload
from scout.engine import Engine
from scout.models import DIMENSIONS, Discovery, Report, output_schema
from scout.policy import evaluate, canonical_url
from scout.reports import export
from scout.research import ResearchInterrupted, make_prompt
from scout.store import Store, learn, now, uid

@pytest.fixture
def store(tmp_path):
    return Store(tmp_path/"data")

def fake_collector(keywords, days, check, emit):
    check()
    return {"stories":[],"discussions":[],"searches":[]}

def fake_provider(stage, prompt, directory, check, emit):
    check()
    payload=sample_payload()
    if stage=="synthesis":
        return synthesis_payload(payload), {"stage":stage,"usage":[],"web_calls_observed":1}
    if stage=="market_scan":
        product=synthesis_payload(payload)
        product["market_candidates"]=[dict(product_name=payload["opportunities"][0]["product"]["name"],competitors=payload["opportunities"][0]["competitors"],buying_signals=payload["opportunities"][0]["market"]["buying_signals"],acquisition_channels=payload["opportunities"][0]["market"]["acquisition_channels"],bottom_up_market_evidence=payload["opportunities"][0]["market"]["bottom_up_market_estimate"],counterevidence=payload["opportunities"][0]["market"]["counterevidence"],source_ids=payload["opportunities"][0]["market"]["source_ids"],product_hunt_checks=[],product_hunt_search_notes=["Synthetic Product Hunt search returned no evidence."])]
        return product, {"stage":stage,"usage":[],"web_calls_observed":1}
    if stage=="pain":
        payload={k:payload[k] for k in Discovery.model_fields}
    return payload, {"stage":stage,"usage":[],"web_calls_observed":1}

def completed_run(store):
    engine=Engine(store,provider=fake_provider,collector=fake_collector)
    run=engine.create({"keywords":"AI data"})
    engine.execute(run)
    return store.get("run",run["id"])

def test_nine_dimensions_and_no_aggregate():
    r=evaluate(sample_payload())
    o=r["opportunities"][0]
    assert o["status"]=="worth_validating"
    assert {s["dimension"] for s in o["scores"]}==set(DIMENSIONS)
    assert "total_score" not in o and "probability" not in o
    assert r["pains"][0]["independent_accounts"]==2

@pytest.mark.parametrize("change",["vendor","author","organization","duplicate_url","duplicate_excerpt","inaccessible"])
def test_false_corroboration_cannot_pass(change):
    p=sample_payload()
    a,b=p["sources"][:2]
    if change=="vendor": b["kind"]="vendor"
    if change=="author":
        b["speaker"]=a["speaker"]; a["organization"]=b["organization"]=None
    if change=="organization": b["organization"]=a["organization"]
    if change=="duplicate_url": b["origin_url"]=a["url"]
    if change=="duplicate_excerpt": b["excerpt"]=a["excerpt"]
    if change=="inaccessible": b["accessed"]=False
    r=evaluate(p)
    assert not r["pains"][0]["qualified"]
    assert r["opportunities"][0]["status"]=="watch"

def test_consequence_must_reference_actual_firsthand_pain_source():
    p=sample_payload()
    p["pains"][0]["consequence_source_ids"]=["S3"]
    assert not evaluate(p)["pains"][0]["qualified"]

def test_unknown_score_not_zero():
    p=sample_payload()
    p["opportunities"][0]["scores"][2]["source_ids"]=[]
    o=evaluate(p)["opportunities"][0]
    assert o["scores"][2]["value"] is None
    assert o["scores"][2]["confidence"]=="low"
    assert o["status"]=="watch"

def test_low_pain_cannot_be_offset_by_trend_or_easy_build():
    p=sample_payload()
    for s in p["opportunities"][0]["scores"]: s["value"]=5
    p["opportunities"][0]["scores"][0]["value"]=1
    assert evaluate(p)["opportunities"][0]["status"]=="watch"

@pytest.mark.parametrize("field",["solo_blockers","constraint_conflicts"])
def test_interest_cannot_override_founder_conflicts(field):
    p=sample_payload()
    p["opportunities"][0][field]=["Requires a large on-site team."]
    assert evaluate(p)["opportunities"][0]["status"]=="reject"

def test_future_sources_do_not_count():
    p=sample_payload()
    p["sources"][1]["published_at"]=(datetime.now(timezone.utc)+timedelta(days=20)).date().isoformat()
    assert evaluate(p)["opportunities"][0]["status"]=="watch"

def test_stale_and_unknown_dates_lower_confidence():
    p=sample_payload()
    for s in p["sources"]: s["published_at"]="2001-01-01"
    assert all(s["confidence"]=="low" for s in evaluate(p)["opportunities"][0]["scores"])
    for s in p["sources"]: s["published_at"]=None
    assert all(s["confidence"]=="low" for s in evaluate(p)["opportunities"][0]["scores"])

def test_broken_citation_and_duplicate_dimensions_are_rejected():
    p=sample_payload();p["opportunities"][0]["scores"][0]["source_ids"]=["NONEXISTENT"]
    with pytest.raises(ValueError): evaluate(p)
    p=sample_payload();p["opportunities"][0]["scores"][-1]=copy.deepcopy(p["opportunities"][0]["scores"][0])
    with pytest.raises(ValueError): evaluate(p)

def test_no_qualifying_opportunities_is_valid():
    p=sample_payload();p["opportunities"]=[]
    assert evaluate(p)["opportunities"]==[]

def test_source_urls_are_normalized_and_private_urls_rejected():
    assert canonical_url("https://www.example.com/a/?utm_source=x")=="https://example.com/a"
    for url in ["javascript:alert(1)","http://localhost:8765","http://127.0.0.1/x","http://10.0.0.1/x","https://user:password@example.com"]:
        assert canonical_url(url)==""

def test_structured_schema_requires_all_object_properties():
    schema=output_schema(Report)
    def check(v):
        if isinstance(v,dict):
            if v.get("type")=="object":
                assert v["additionalProperties"] is False
                assert set(v["required"])==set(v["properties"])
            for x in v.values(): check(x)
        elif isinstance(v,list):
            for x in v: check(x)
    check(schema)

def test_full_pipeline_and_exports(store):
    r=completed_run(store)
    assert r["status"]=="completed"
    assert set(r["checkpoints"]["1"])=={"signals","pain","synthesis","market_scan","assessment","challenge"}
    assert len(r["usage"])==5
    for fmt in ["md","html","csv","json"]:
        assert (store.root/"runs"/r["id"]/"exports"/("report."+fmt)).exists()
        assert export(r,fmt)[0]
    assert "scorecard" in r["message"].lower()

def test_one_active_run(store):
    e=Engine(store)
    e.create({"keywords":"AI data"})
    with pytest.raises(ValueError): e.create({"keywords":"Another"})
    assert len(store.all("run"))==1

def test_prompt_discovery_uses_founder_context_and_validates_source_links(store):
    captured={}
    def provider(stage,prompt,*args):
        captured.update(stage=stage,prompt=prompt)
        return dict(summary="A focused direction.",prompts=[dict(id="D1",title="Data workflow pain",scout_keywords="data workflow",scout_context="Verify the buyer and budget.",problem_signal="Teams repeat manual checks.",user_persona="Data engineer",buyer_persona="Data platform lead",why_founder_fit="Matches data engineering experience.",why_now="AI output increases review work.",source_ids=["PS1"],uncertainties=["Spending is unknown."])],sources=[dict(id="PS1",url="https://example.com/signal",title="Signal",excerpt="We repeat this check weekly.",signal_type="pain",published_at="2026-09-01")],searches=["reddit data workflow"],limitations=[]),dict(stage=stage,usage=[])
    store.put("profile","default",dict(store.get("profile","default"),skills="Data engineering and dbt"))
    result=Engine(store,provider=provider,trending_collector=lambda *args:([{"name":"trend/repo","window":"daily"}],[])).discover_prompts({"focus":"AI data","max_prompts":3})
    assert result["status"]=="completed" and result["result"]["prompts"][0]["scout_keywords"]=="data workflow"
    assert captured["stage"]=="prompt_discovery" and "Data engineering and dbt" in captured["prompt"]
    assert "Reddit" in captured["prompt"] and "Product Hunt" in captured["prompt"]

def test_prompt_discovery_rejects_unknown_source_reference(store):
    def provider(stage,prompt,*args):
        return dict(summary="Bad result.",prompts=[dict(id="D1",title="Pain",scout_keywords="pain",scout_context="Check it.",problem_signal="A problem.",user_persona="User",buyer_persona="Buyer",why_founder_fit="Relevant.",why_now="Recent.",source_ids=["missing"],uncertainties=[])],sources=[],searches=[],limitations=[]),{}
    with pytest.raises(ValueError,match="unknown source"):
        Engine(store,provider=provider,trending_collector=lambda *args:([],[])).discover_prompts({})

def test_explicit_preference_persists_and_undo_works(store):
    m=store.add_memory("Prefer self-serve developer tools","explicit",["test"],True)
    store.edit_memory(m["id"],{"text":"Prefer team tools","active":False})
    assert m["id"] not in {x["id"] for x in store.memories()}
    store.undo_memory(m["id"])
    assert store.get("memory",m["id"])["text"]==m["text"]
    again=Store(store.root)
    assert m["id"] in {x["id"] for x in again.memories()}

def add_feedback(store, opp, **kw):
    f=dict(id=uid(),run_id="r",opportunity_id=opp,kind="reject",reason="Too much support for one founder",remember=False,preference_tag="low_operations",outcome=None,amount=None,created_at=now(),**kw)
    store.put("feedback",f["id"],f)
    return f

def test_one_rejection_does_not_create_blanket_preference(store):
    f=add_feedback(store,"a")
    assert learn(store,f) is None
    assert not [m for m in store.memories() if m["kind"]=="inferred"]
    f=add_feedback(store,"a")
    assert learn(store,f) is None
    f=add_feedback(store,"b")
    learned=learn(store,f)
    assert learned["kind"]=="inferred" and not learned["confirmed"]

def test_forgotten_preference_not_relearned_from_old_feedback(store):
    learn(store,add_feedback(store,"a"))
    m=learn(store,add_feedback(store,"b"))
    store.edit_memory(m["id"],dict(text="",active=False,forgotten=True))
    assert learn(store,add_feedback(store,"c")) is None
    ctx=store.context()
    assert not any(x["id"]==m["id"] for x in ctx["memory"])
    assert not set(m["origins"]) & {f["id"] for f in ctx["feedback"]}

def test_bookmark_and_outcomes_do_not_infer_preferences(store):
    f=add_feedback(store,"a")
    f["kind"]="interested"
    assert learn(store,f) is None
    f["kind"]="outcome"
    assert learn(store,f) is None

def test_steering_suppresses_obsolete_result_and_keeps_checkpoints(store):
    entered=threading.Event()
    def slow(stage,prompt,directory,check,emit):
        if stage=="assessment" and "NEW_DIRECTION" not in prompt:
            entered.set()
            while True:
                check();time.sleep(.01)
        return fake_provider(stage,prompt,directory,check,emit)
    e=Engine(store,provider=slow,collector=fake_collector)
    r=e.create({"keywords":"AI data"})
    t=threading.Thread(target=e.execute,args=(r,));t.start()
    assert entered.wait(3)
    redirected=e.steer(r["id"],"NEW_DIRECTION: favor self-serve tools",True)
    t.join(3);assert not t.is_alive()
    current=store.get("run",r["id"])
    assert current["revision"]==2 and current["report"] is None
    assert "pain" in current["checkpoints"]["1"]
    assert set(current["checkpoints"]["2"])=={"signals","pain","synthesis","market_scan"}
    assert current["steering"][-1]["resolved_impact"]=="source_refinement"
    assert current["steering"][-1]["restart_from"]=="assessment"
    assert any("NEW_DIRECTION" in m["text"] for m in store.memories())
    e.execute(current)
    final=store.get("run",r["id"])
    assert final["status"]=="completed"
    assert "challenge" not in final["checkpoints"]["1"]
    assert "challenge" in final["checkpoints"]["2"]

@pytest.mark.parametrize("impact,stage,expected_restart,expected_preserved",[
    ("source_refinement","challenge","challenge",["signals","pain","synthesis","market_scan","assessment"]),
    ("market_refinement","assessment","market_scan",["signals","pain","synthesis"]),
    ("product_reframing","market_scan","synthesis",["signals","pain"]),
    ("full_restart","challenge","signals",[]),
    ("market_refinement","pain","pain",["signals"]),
])
def test_steering_impact_selects_safe_checkpoint_boundary(store,impact,stage,expected_restart,expected_preserved):
    e=Engine(store,provider=fake_provider,collector=fake_collector)
    r=e.create({"keywords":"AI data"})
    order=["signals","pain","synthesis","market_scan","assessment","challenge"]
    r.update(status="paused",stage=stage)
    r["checkpoints"]["1"]={name:{"name":name} for name in order[:order.index(stage)]}
    store.put("run",r["id"],r)
    steered=e.steer(r["id"],"Apply this direction",False,impact)
    decision=steered["steering"][-1]
    assert decision["restart_from"]==expected_restart
    assert decision["preserved_stages"]==expected_preserved
    assert list(steered["checkpoints"]["2"])==expected_preserved

@pytest.mark.parametrize("message,expected",[
    ("Use more firsthand forum evidence","source_refinement"),
    ("Check competitor pricing and switching behavior","market_refinement"),
    ("Bundle these pains into a workflow product","product_reframing"),
    ("Switch to a different customer audience","full_restart"),
])
def test_auto_steering_classification(store,message,expected):
    e=Engine(store)
    assert e.classify_steering(message,{})==expected

def test_steering_api_rejects_unknown_impact(store):
    app=create_app(store.root,start_worker=False)
    with TestClient(app) as client:
        run=client.post("/api/runs",json={"keywords":"AI data"}).json()
        response=client.post(f"/api/runs/{run['id']}/steer",json={"message":"Refine it","impact":"unsafe_mode"})
        assert response.status_code==422

@pytest.mark.parametrize("action,expected",[("pause","paused"),("cancel","cancelled")])
def test_controls_interrupt_research(store,action,expected):
    entered=threading.Event()
    def waiting(stage,prompt,directory,check,emit):
        entered.set()
        while True: check();time.sleep(.01)
    e=Engine(store,provider=waiting,collector=fake_collector)
    r=e.create({"keywords":"AI data"})
    t=threading.Thread(target=e.execute,args=(r,));t.start()
    assert entered.wait(2)
    e.control(r["id"],action)
    t.join(2)
    assert not t.is_alive()
    assert store.get("run",r["id"])["status"]==expected

def test_provider_failure_preserves_partial_report(store):
    def provider(stage,*args):
        if stage=="challenge": raise RuntimeError("Simulated rate limit")
        return fake_provider(stage,*args)
    e=Engine(store,provider=provider,collector=fake_collector)
    r=e.create({"keywords":"AI data"})
    e.execute(r)
    r=store.get("run",r["id"])
    assert r["status"]=="partial" and r["report"]
    e.provider=fake_provider
    e.control(r["id"],"resume")
    e.execute(store.get("run",r["id"]))
    assert store.get("run",r["id"])["status"]=="completed"

def test_server_restart_makes_inflight_run_resumable(store):
    e=Engine(store)
    r=e.create({"keywords":"AI data"})
    e.start()
    try: assert store.get("run",r["id"])["status"]=="paused"
    finally: e.shutdown()

def test_timeout_preserves_checkpoint(store):
    def delayed(stage,prompt,directory,check,emit):
        time.sleep(.04);check()
        return fake_provider(stage,prompt,directory,check,emit)
    e=Engine(store,provider=delayed,collector=fake_collector)
    r=e.create({"keywords":"AI data","timeout_minutes":1})
    r=store.update_run(r["id"],dict(elapsed_seconds=59.98))
    e.execute(r)
    result=store.get("run",r["id"])
    assert result["status"]=="partial" and "time limit" in result["message"]
    assert "signals" in result["checkpoints"]["1"]

def test_export_escapes_html_and_spreadsheet_formulas(store):
    r=completed_run(store)
    r["report"]["opportunities"][0]["title"]="=IMPORTXML(1)"
    r["report"]["summary"]="<script>alert(1)</script>"
    assert "<script>" not in export(r,"html")[0]
    assert "'=IMPORTXML" in export(r,"csv")[0]

def test_api_feedback_and_real_outcome_calibration(tmp_path):
    app=create_app(tmp_path/"api",start_worker=False)
    s=app.state.store
    r=completed_run(s)
    with TestClient(app) as client:
        assert client.get("/api/health").status_code==200
        result=client.post("/api/feedback",json={"run_id":r["id"],"opportunity_id":"O1","kind":"outcome","reason":"One paid pilot; USD","outcome":"paid","amount":250})
        assert result.status_code==200
        assert client.get("/api/learning").json()["comparisons"][0]["outcome"]=="paid"
        correction=client.post("/api/feedback",json={"run_id":r["id"],"kind":"correction","reason":"Source S1 needs checking"})
        assert correction.status_code==200
        assert client.get("/api/runs/"+r["id"]).json()["corrections_pending"]
        assert client.post("/api/profile",headers={"Origin":"https://evil.example"},json={}).status_code==403
        assert client.get("/api/health",headers={"Host":"evil.example"}).status_code==400
        assert client.get("/api/runs/absent").status_code==404

def test_demo_feedback_cannot_contaminate_learning(tmp_path):
    app=create_app(tmp_path/"api",start_worker=False)
    with TestClient(app) as client:
        r=client.post("/api/example").json()
        assert r["demo"]
        assert client.post("/api/feedback",json={"run_id":r["id"],"kind":"interested","reason":"Looks good"}).status_code==400
        assert client.get("/api/learning").json()["feedback_count"]==0

def test_rejected_opportunity_needs_a_material_change_explanation(store):
    e=Engine(store)
    report=evaluate(sample_payload())
    o=report["opportunities"][0]
    previous=dict(title=o["title"],status="reject",scores=o["scores"],fingerprint=o["fingerprint"])
    e.annotate_changes(report,[previous])
    assert report["opportunities"][0]["status"]=="watch"
    report=evaluate(sample_payload())
    report["opportunities"][0]["changes_since_previous"]="Changed founder access: a newly documented public export removes the earlier private data dependency. This must be checked with the actual buyer."
    e.annotate_changes(report,[previous])
    assert report["opportunities"][0]["status"]=="worth_validating"

def test_origin_alias_cannot_bypass_duplicate_source_gate():
    p=sample_payload()
    p["sources"][1]["url"]=p["sources"][0]["url"]
    p["sources"][1]["origin_url"]="not-a-url"
    assert not evaluate(p)["pains"][0]["qualified"]

def test_outcome_requires_an_outcome_type(tmp_path):
    app=create_app(tmp_path/"api",start_worker=False)
    with TestClient(app) as client:
        response=client.post("/api/feedback",json={"run_id":"x","kind":"outcome","reason":"Something happened"})
        assert response.status_code==422
