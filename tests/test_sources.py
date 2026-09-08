from datetime import datetime, timezone
from scout import research
from scout.sources import CATALOG, source_plan, trending_plan, collect_github_trending

def test_source_catalog_covers_pain_persona_budget_competition_and_timing():
    covered={kind for source in CATALOG for kind in source["evidence_classes"]}
    assert {"pain","user_persona","buyer","budget","competition","timing"} <= covered
    assert {source["id"] for source in CATALOG} >= {"github","stack_exchange","ted","sam","jobs","marketplaces","regulators","edgar"}

def test_source_plan_records_purpose_for_every_search():
    plan=source_plan("AI regulatory data")
    assert len(plan)>=7
    assert all(item["source"] and item["query"] and item["purpose"] for item in plan)
    assert any("budget" in item["purpose"] for item in plan)
    assert any("persona" in item["purpose"] for item in plan)

def test_trending_plan_covers_both_platforms_and_all_windows():
    plan=trending_plan(datetime(2026,9,7,tzinfo=timezone.utc))
    assert {(item["platform"],item["window"]) for item in plan}=={(platform,window) for platform in ("GitHub","Product Hunt") for window in ("daily","weekly","monthly")}
    assert any("/leaderboard/weekly/2026/37" in item["url"] for item in plan)

def test_github_trending_parser_preserves_window_and_momentum(monkeypatch):
    page=b'''<article class="Box-row"><h2><a href="/owner/useful-repo"> owner / useful-repo </a></h2><p>A workflow tool</p><span>1,234 stars today</span></article>'''
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):return None
        def read(self):return page
    monkeypatch.setattr("urllib.request.urlopen",lambda *args,**kwargs:Response())
    rows,logs=collect_github_trending(lambda:None,lambda *args:None)
    assert len(rows)==3 and {row["window"] for row in rows}=={"daily","weekly","monthly"}
    assert rows[0]["name"]=="owner/useful-repo" and rows[0]["stars_in_window"]==1234
    assert all(log["error"] is None for log in logs)

def test_public_signal_collection_merges_open_sources_and_search_log(monkeypatch):
    monkeypatch.setattr(research,"collect_hn",lambda *args:dict(stories=[],discussions=[],searches=[{"source":"HN Algolia","query":"AI"}],retrieved_at="now",note="HN note."))
    monkeypatch.setattr(research,"collect_open_sources",lambda terms,since,check,emit:dict(github_issues=[{"title":"Manual workflow"}],stackexchange_questions=[{"title":"Recurring question"}],procurement_notices=[{"record":{"buyer":"Agency"}}],source_searches=[{"source":"GitHub Issues","query":"AI","fetched":1,"error":None}]))
    result=research.collect_public_signals("AI data",90,lambda:None,lambda *args:None)
    assert result["github_issues"][0]["title"]=="Manual workflow"
    assert result["procurement_notices"][0]["record"]["buyer"]=="Agency"
    assert {s["source"] for s in result["searches"]}=={"HN Algolia","GitHub Issues"}
    assert result["source_catalog"]==CATALOG and len(result["source_plan"])>=7
    assert "discovery leads" in result["note"]
