#!/usr/bin/env python3
"""Start/check one bounded live verification run on the local Scout API."""
import argparse,json,urllib.request
def call(path,body=None):
    data=json.dumps(body).encode() if body is not None else None
    req=urllib.request.Request("http://127.0.0.1:8765/api"+path,data=data,headers={"Content-Type":"application/json"} if data else {})
    with urllib.request.urlopen(req,timeout=20) as response:return json.load(response)
p=argparse.ArgumentParser()
p.add_argument("action",choices=["start","status"])
p.add_argument("--run-id")
args=p.parse_args()
if args.action=="start":
    r=call("/runs",dict(keywords="dbt schema changes, analytics testing",context="Live verification run: investigate at most 2 pain clusters and return at most one narrowly scoped OPC opportunity. Use about 3 focused searches plus source reads in each stage. Do not fill the report with weak ideas. Keep financial assumptions explicit.",days=90,max_opportunities=1,timeout_minutes=10))
    print(json.dumps({"run_id":r["id"],"status":r["status"]}))
else:
    r=call("/runs/"+args.run_id)
    print(json.dumps({k:r.get(k) for k in ["id","status","stage","message","revision","elapsed_seconds","usage"]},indent=2))
    if r.get("report"):
        print(json.dumps({"summary":r["report"]["summary"],"sources":len(r["report"]["sources"]),"opportunities":[{"title":o["title"],"status":o["status"]} for o in r["report"]["opportunities"]]},indent=2))
