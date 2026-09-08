"""Public discovery sources and resilient API seed collectors."""
from __future__ import annotations
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
import html
import re

CATALOG = [
    dict(id="hacker_news",name="Hacker News",evidence_classes=["pain","timing"],access="api",stage="signals"),
    dict(id="github",name="GitHub Issues",evidence_classes=["pain","user_persona","adoption"],access="api",stage="signals"),
    dict(id="stack_exchange",name="Stack Exchange",evidence_classes=["pain","user_persona"],access="api",stage="signals"),
    dict(id="ted",name="EU TED procurement",evidence_classes=["buyer","budget","purchase_trigger"],access="api",stage="signals"),
    dict(id="sam",name="SAM.gov opportunities",evidence_classes=["buyer","budget","purchase_trigger"],access="web",stage="pain"),
    dict(id="jobs",name="Public job postings",evidence_classes=["user_persona","workflow","operating_cost"],access="web",stage="pain"),
    dict(id="marketplaces",name="Vertical app marketplaces",evidence_classes=["pain","competition","paid_adoption"],access="web_or_authenticated_api",stage="market_scan"),
    dict(id="regulators",name="Regulatory notices and consultations",evidence_classes=["timing","mandatory_work","buyer"],access="web",stage="pain"),
    dict(id="edgar",name="SEC EDGAR filings",evidence_classes=["budget","operating_cost","timing"],access="api_and_web",stage="market_scan"),
]

def source_plan(keywords):
    phrase=" ".join(keywords.split())
    return [
        dict(source="GitHub Issues",query=f'{phrase} is:issue (manual OR workaround OR painful OR missing)',purpose="pain and user workflow"),
        dict(source="Stack Exchange",query=f'{phrase} recurring problem workaround',purpose="pain and user persona"),
        dict(source="EU TED / SAM.gov",query=f'{phrase} procurement contract solicitation',purpose="named buyer, requirements and budget"),
        dict(source="Job postings",query=f'\"{phrase}\" (manual OR responsible OR internal tooling)',purpose="daily user, workflow and operating cost"),
        dict(source="App marketplaces",query=f'{phrase} app reviews alternatives pricing',purpose="paid alternatives, complaints and switching"),
        dict(source="Regulators",query=f'{phrase} rule consultation implementation deadline',purpose="mandatory work and timing"),
        dict(source="SEC EDGAR",query=f'{phrase} cost risk compliance implementation',purpose="company spending, cost and strategic urgency"),
    ]

def trending_plan(at=None):
    at=at or datetime.now(timezone.utc)
    year,week,_=at.isocalendar()
    return [
        *[dict(platform="GitHub",window=window,url=f"https://github.com/trending?since={window}",purpose="emerging repositories and developer momentum") for window in ("daily","weekly","monthly")],
        dict(platform="Product Hunt",window="daily",url=f"https://www.producthunt.com/leaderboard/daily/{at.year}/{at.month}/{at.day}",purpose="new product launches and positioning"),
        dict(platform="Product Hunt",window="weekly",url=f"https://www.producthunt.com/leaderboard/weekly/{year}/{week}",purpose="launch momentum beyond one day"),
        dict(platform="Product Hunt",window="monthly",url=f"https://www.producthunt.com/leaderboard/monthly/{at.year}/{at.month}",purpose="sustained product-category attention"),
    ]

def collect_github_trending(check,emit):
    rows=[];logs=[]
    for window in ("daily","weekly","monthly"):
        check();url=f"https://github.com/trending?since={window}"
        try:
            request=urllib.request.Request(url,headers={"User-Agent":"OpportunityScout/0.1 public-research contact=local"})
            with urllib.request.urlopen(request,timeout=12) as response:page=response.read().decode("utf-8","replace")
            articles=re.findall(r'<article[^>]*class="[^"]*Box-row[^"]*"[^>]*>(.*?)</article>',page,re.S|re.I)
            found=[]
            for article in articles[:25]:
                match=re.search(r'href="/([^"?#]+/[^"?#]+)"',article,re.I)
                if not match:continue
                name=re.sub(r"\s+","",html.unescape(match.group(1)))
                description_match=re.search(r'<p[^>]*>(.*?)</p>',article,re.S|re.I)
                description=html.unescape(re.sub(r'<[^>]+>',' ',description_match.group(1) if description_match else ''))
                description=re.sub(r"\s+"," ",description).strip()
                momentum_match=re.search(r'([\d,]+)\s+stars?\s+(?:today|this week|this month)',re.sub(r'<[^>]+>',' ',article),re.I)
                found.append(dict(name=name,url="https://github.com/"+name,description=description,window=window,stars_in_window=int(momentum_match.group(1).replace(',','')) if momentum_match else None,evidence_class=["timing","adoption"]))
            rows+=found;logs.append(dict(source="GitHub Trending",query=window,fetched=len(found),error=None));emit("collection",f"GitHub Trending: {len(found)} {window} repositories.")
        except Exception as exc:
            logs.append(dict(source="GitHub Trending",query=window,error=str(exc)));emit("warning",f"GitHub {window} trending unavailable; web research will continue.")
    return rows,logs

def _get(url):
    request=urllib.request.Request(url,headers={"User-Agent":"OpportunityScout/0.1 public-research contact=local"})
    with urllib.request.urlopen(request,timeout=12) as response:return json.load(response)

def collect_open_sources(terms,since,check,emit):
    results=dict(github_issues=[],stackexchange_questions=[],procurement_notices=[])
    logs=[]
    fromdate=int(since.timestamp())
    for term in terms[:3]:
        check()
        github="https://api.github.com/search/issues?"+urllib.parse.urlencode({"q":f'"{term}" is:issue','sort':'updated','order':'desc','per_page':20})
        try:
            data=_get(github);items=data.get("items",[])
            results["github_issues"] += [dict(title=i.get("title"),url=i.get("html_url"),state=i.get("state"),comments=i.get("comments"),updated_at=i.get("updated_at"),repository=(i.get("repository_url") or "").rsplit("/",1)[-1],excerpt=(i.get("body") or "")[:900],evidence_class=["pain","user_persona","adoption"]) for i in items]
            logs.append(dict(source="GitHub Issues",query=term,fetched=len(items),error=None));emit("collection",f'GitHub: {len(items)} issue seeds for “{term}”.')
        except Exception as exc:
            logs.append(dict(source="GitHub Issues",query=term,error=str(exc)));emit("warning","GitHub issue seeds unavailable; source-specific web research will continue.")
        check()
        stack="https://api.stackexchange.com/2.3/search/advanced?"+urllib.parse.urlencode({"site":"stackoverflow","q":term,"fromdate":fromdate,"order":"desc","sort":"activity","pagesize":20,"filter":"withbody"})
        try:
            data=_get(stack);items=data.get("items",[])
            results["stackexchange_questions"] += [dict(title=i.get("title"),url=i.get("link"),score=i.get("score"),answers=i.get("answer_count"),updated_at=datetime.fromtimestamp(i.get("last_activity_date",0),timezone.utc).isoformat(),excerpt=(i.get("body") or "")[:900],evidence_class=["pain","user_persona"]) for i in items]
            logs.append(dict(source="Stack Exchange",query=term,fetched=len(items),error=None));emit("collection",f'Stack Exchange: {len(items)} question seeds for “{term}”.')
        except Exception as exc:
            logs.append(dict(source="Stack Exchange",query=term,error=str(exc)));emit("warning","Stack Exchange seeds unavailable; source-specific web research will continue.")
    if terms:
        check();term=" ".join(terms[:2]);url="https://api.ted.europa.eu/v3/notices/search"
        escaped=term.replace('"',' ')
        expert_query=f'FT~"{escaped}" AND PD>={since.strftime("%Y%m%d")}'
        payload=json.dumps({"query":expert_query,"fields":["publication-number","notice-title","publication-date","buyer-name"],"page":1,"limit":20}).encode()
        request=urllib.request.Request(url,data=payload,headers={"User-Agent":"OpportunityScout/0.1 public-research contact=local","Content-Type":"application/json"},method="POST")
        try:
            with urllib.request.urlopen(request,timeout=15) as response:data=json.load(response)
            notices=data.get("notices") or data.get("results") or []
            def english(value):
                if isinstance(value,dict):value=value.get("eng") or next(iter(value.values()),"")
                if isinstance(value,list):return ", ".join(str(v) for v in value)
                return str(value or "")
            results["procurement_notices"]=[dict(id=n.get("publication-number"),title=english(n.get("notice-title")),buyer=english(n.get("buyer-name")),published_at=n.get("publication-date"),url=((n.get("links") or {}).get("htmlDirect") or {}).get("ENG"),evidence_class=["buyer","budget","purchase_trigger"]) for n in notices[:20]]
            logs.append(dict(source="EU TED",query=term,fetched=len(notices[:20]),error=None));emit("collection",f'EU TED: {len(notices[:20])} procurement seeds for “{term}”.')
        except Exception as exc:
            logs.append(dict(source="EU TED",query=term,error=str(exc)));emit("warning","EU procurement seeds unavailable; targeted procurement web research will continue.")
    results["source_searches"]=logs
    return results
