import csv
import html
import io
import json
from pathlib import Path
from .models import DIMENSIONS
from .policy import canonical_url

def html_report(run):
    e = lambda value: html.escape(str(value))
    parts = ['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Scout report</title><style>body{max-width:1080px;margin:50px auto;padding:0 25px;background:#f7f6f0;color:#2c4231;font:14px/1.75 system-ui}h1{font-size:36px;letter-spacing:-1px}h2{font-size:25px;margin-top:34px}h3{font-size:16px}article,aside{padding:24px;background:#fffefa;border:1px solid #dfe4d6;border-radius:8px;margin:20px 0}a{color:#356a45}table{border-collapse:collapse;width:100%;font-size:12px}th,td{text-align:left;padding:12px 8px;border-bottom:1px solid #e7ebdf;vertical-align:top}small{color:#7b896f}.badge{padding:5px 9px;background:#e7eddd;border-radius:4px}blockquote{border-left:2px solid #b5c7a1;margin-left:0;padding-left:16px;color:#778568}.scroll{overflow:auto}pre{white-space:pre-wrap;overflow-wrap:anywhere}@media print{body{margin:0;background:white}article{break-inside:avoid}a{color:inherit}}</style></head><body>']
    parts += ['<small>OPPORTUNITY SCOUT · CUSTOMER PAIN FIRST</small><h1>'+e(run['keywords'])+'</h1>', '<p>'+e(run['created_at'])+' · Brief v'+e(run['revision'])+' · '+e(run['status'])+'</p>']
    if run.get('demo'): parts += ['<aside><strong>SYNTHETIC EXAMPLE — not market research.</strong></aside>']
    if run['status'] != 'completed': parts += ['<aside><strong>Partial run — skeptical review may be incomplete.</strong><p>'+e(run.get('message',''))+'</p></aside>']
    report = run.get('report')
    if not report:
        return ''.join(parts)+'<p>No complete assessment is available yet. Resume from the workspace.</p></body></html>'
    parts += ['<p>'+e(report['summary'])+'</p>']
    parts += ['<h2>Research decision trail</h2>']
    if report.get('research_trail'):
        for trail in report['research_trail']:
            refs=' '.join('<a href="#'+e(i)+'">'+e(i)+'</a>' for i in trail['source_ids'])
            parts += ['<article><small>'+e(trail['stage'])+' · '+e(trail['decision'])+'</small><h3>'+e(trail['title'])+'</h3><p>'+e(trail['summary'])+'</p><p><strong>Why:</strong> '+e('; '.join(trail['reasons']))+'</p><p>'+refs+'</p><p><strong>What could reopen it:</strong> '+e('; '.join(trail['next_evidence']))+'</p></article>']
    else:
        parts += ['<p>This historical report predates structured decision trails.</p>']
    if report.get('investigation'):
        f = report['investigation']
        score = lambda s: 'Unknown' if s['value'] is None else str(s['value'])+'/5'
        parts += ['<aside><h2>Focused follow-up: '+e(DIMENSIONS[f['dimension']][0])+'</h2><p>Parent report: '+e(f['parent_run_id'])+'</p><p><strong>'+e(score(f['before']))+' → '+e(score(f['after']))+'</strong> · '+e(f['before']['confidence'])+' → '+e(f['after']['confidence'])+' confidence</p><p>'+e(f['conclusion'])+'</p><p>The other eight scores are preserved. Additional source observations: '+str(len(f['new_source_ids']))+'</p>']
        for finding in f['findings']:
            refs = ' '.join('<a href="#'+e(i)+'">'+e(i)+'</a>' for i in finding['source_ids'])
            parts += ['<p>'+e(finding['evidence_type'])+': '+e(finding['claim'])+' '+refs+'</p>']
        parts += ['</aside>']
    pains = {p['id']:p for p in report['pains']}
    for o in report['opportunities']:
        p = pains[o['pain_id']]
        parts += ['<article><span class="badge">'+e(o['status'].replace('_',' '))+'</span><h2>'+e(o['title'])+'</h2><p>'+e(o['thesis'])+'</p>']
        for label,text in [('Customer',p['customer']),('Buyer',p['buyer']),('Workflow',p['workflow']),('Pain',p['problem']),('Consequence',p['consequence']),('Frequency',p['frequency']),('Workaround',p['workaround']),('Spending evidence',p['spending_evidence']),('Qualification',p['gate_reason']),('Solution',o['solution']),('Why now',o['why_now']),('Founder fit',o['founder_fit'])]:
            parts += ['<p><strong>'+e(label)+':</strong> '+e(text)+'</p>']
        if o.get('product'):
            product=o['product']
            parts += ['<h3>Product thesis: '+e(product['name'])+'</h3>']
            for key in ['category','target_customer','buyer','job_to_be_done','why_one_product','recurring_value','entry_point','expansion_path','incumbent_absorption_risk']:
                parts += ['<p><strong>'+e(key.replace('_',' ').capitalize())+':</strong> '+e(product[key])+'</p>']
            for key in ['user_persona','user_job','buyer_persona','buyer_goal','buyer_user_relationship','purchase_trigger']:
                if product.get(key): parts += ['<p><strong>'+e(key.replace('_',' ').capitalize())+':</strong> '+e(product[key])+'</p>']
            parts += ['<p>Related pains: '+e(', '.join(product['related_pain_ids']))+'</p><ol>'+''.join('<li>'+e(v)+'</li>' for v in product['workflow_steps'])+'</ol>']
        if o.get('market'):
            market=o['market']
            parts += ['<h3>Product market: '+e(market['verdict'])+'</h3>']
            for key in ['target_segment','reachable_market','pricing_logic','differentiation','switching_trigger']:
                parts += ['<p><strong>'+e(key.replace('_',' ').capitalize())+':</strong> '+e(market[key])+'</p>']
            for signal in market['buying_signals']:
                parts += ['<p>'+e(signal['kind'])+': '+e(signal['claim'])+' ('+e(', '.join(signal['source_ids']))+')</p>']
            for key in ['competitor_search_notes','counterevidence','remaining_validation']:
                parts += ['<h3>'+e(key.replace('_',' ').capitalize())+'</h3><ul>'+''.join('<li>'+e(v)+'</li>' for v in market[key])+'</ul>']
        parts += ['<h3>Nine-dimensional scorecard</h3><div class="scroll"><table><thead><tr><th>Dimension</th><th>Score</th><th>Confidence</th><th>Rationale and next evidence</th></tr></thead><tbody>']
        for s in o['scores']:
            refs=' '.join('<a href="#'+e(i)+'">'+e(i)+'</a>' for i in s['source_ids'])
            parts += ['<tr><td>'+e(DIMENSIONS[s['dimension']][0])+'</td><td>'+e(str(s['value'])+'/5' if s['value'] is not None else 'Unknown')+'</td><td>'+e(s['confidence'])+'</td><td>'+e(s['rationale'])+' '+refs+'<p><strong>Next evidence:</strong> '+e(s['next_evidence'])+'</p><p><strong>Assumptions:</strong> '+e('; '.join(s['assumptions']) or 'None recorded')+'</p><p><strong>Counterevidence:</strong> '+e(s['counterevidence'])+'</p></td></tr>']
        parts += ['</tbody></table></div><h3>Building and validating</h3>']
        for key in ['mvp','build_effort','upfront_cost','monthly_cost','support_burden','sales_effort','time_to_pilot','acquisition','validation_experiment','ranking_reason','changes_since_previous']:
            parts += ['<p><strong>'+e(key.replace('_',' ').capitalize())+':</strong> '+e(o[key])+'</p>']
        for key in ['dependencies','solo_blockers','constraint_conflicts','kill_criteria','uncertainties','warnings']:
            if o.get(key): parts += ['<h3>'+e(key.replace('_',' ').capitalize())+'</h3><ul>'+''.join('<li>'+e(v)+'</li>' for v in o[key])+'</ul>']
        for c in o['competitors']:
            parts += ['<h3>Alternative: '+e(c['name'])+'</h3><p>Category: '+e(c.get('category') or 'Unassessed')+' · Buyer: '+e(c.get('target_customer',''))+'</p><p>'+e(c['offering'])+'</p><p>Pricing: '+e(c['price_evidence'])+'</p><p>Proposed gap: '+e(c['gap'])+'</p><p>Adoption: '+e(c.get('adoption_evidence',''))+'</p><p>Switching costs: '+e(c.get('switching_costs',''))+'</p>']
        parts += ['</article>']
    parts += ['<h2>Evidence ledger</h2>']
    for s in report['sources']:
        url=canonical_url(s['url'])
        title='<a href="'+e(url)+'" rel="noreferrer">'+e(s['title'])+'</a>' if url and not run.get('demo') else e(s['title'])
        parts += ['<article id="'+e(s['id'])+'"><h3>'+e(s['id'])+' — '+title+'</h3><small>'+e(s['kind'])+' · '+e(s['speaker'] or 'Author unknown')+' · Published '+e(s['published_at'] or 'Unknown')+' · Retrieved '+e(s['retrieved_at'])+'</small><blockquote>'+e(s['excerpt'])+'</blockquote><p>'+e(s['supports'])+'</p></article>']
    for title,items in [('Rejected directions',report['rejected_directions']),('Limitations',report['limitations']+report['validation_issues']),('Search notes',report['search_notes'])]:
        parts += ['<h2>'+title+'</h2><ul>'+''.join('<li>'+e(v)+'</li>' for v in items)+'</ul>']
    parts += ['<h2>Founder context at research time</h2><pre>'+e(json.dumps(run['profile_snapshot'],ensure_ascii=False,indent=2))+'</pre><h3>Memory applied</h3><ul>'+''.join('<li>'+e(m['text'])+'</li>' for m in run['memory_snapshot'])+'</ul><p><small>'+e(report['qualification_note'])+'</small></p></body></html>']
    return ''.join(parts)

def markdown(run):
    report = run.get("report")
    lines = ["# Opportunity Scout", "", f'Brief: {run["keywords"]}', f'Status: {run["status"]} · Revision {run["revision"]} · Created {run["created_at"]}', ""]
    if run.get("demo"): lines += ["**SYNTHETIC EXAMPLE — not market research or a validated business.**", ""]
    if run["status"] != "completed": lines += ["**PARTIAL RUN — skeptical review may be incomplete.**", run.get("message",""), ""]
    if not report:
        lines += ["No complete assessment is available yet. Completed checkpoint stages:", ", ".join(run["checkpoints"].get(str(run["revision"]),{})), ""]
        return "\n".join(lines)
    lines += [report["summary"], "", report["qualification_note"], ""]
    lines += ["## Research decision trail", ""]
    if report.get("research_trail"):
        for trail in report["research_trail"]:
            lines += ["### "+trail["title"], "", "**"+trail["stage"].replace("_"," ")+" · "+trail["decision"].replace("_"," ")+"**", "", trail["summary"], "", "Why: "+"; ".join(trail["reasons"]), "", "Sources: "+(", ".join(trail["source_ids"]) or "None"), "", "What could advance or reopen it: "+("; ".join(trail["next_evidence"]) or "No next evidence recorded."), ""]
    else:
        lines += ["This historical report predates structured decision trails.", ""]
    if report.get("investigation"):
        f = report["investigation"]
        score = lambda s: "Unknown" if s["value"] is None else str(s["value"])+"/5"
        lines += ["## Focused follow-up: "+DIMENSIONS[f["dimension"]][0], "", "Parent report: "+f["parent_run_id"], "", score(f["before"])+" → "+score(f["after"])+"; confidence: "+f["before"]["confidence"]+" → "+f["after"]["confidence"], "", f["conclusion"], "", "The other eight scores are preserved. Additional source observations: "+str(len(f["new_source_ids"])), ""]
        lines += ["- "+v["evidence_type"]+": "+v["claim"]+" ("+", ".join(v["source_ids"])+")" for v in f["findings"]] + [""]
    pains = {p["id"]:p for p in report["pains"]}
    for o in report["opportunities"]:
        p = pains[o["pain_id"]]
        lines += [f'## {o["title"]}', "", f'**{o["status"].replace("_"," ")}** — {o["ranking_reason"]}', ""]
        for title, text in [("Customer",p["customer"]),("Buyer",p["buyer"]),("Workflow",p["workflow"]),("Pain",p["problem"]),("Frequency",p["frequency"]),("Consequence",p["consequence"]),("Workaround",p["workaround"]),("Spending evidence",p["spending_evidence"]),("Qualification",p["gate_reason"]),("Solution",o["solution"]),("Why now",o["why_now"]),("Founder fit",o["founder_fit"])]:
            lines += [f"**{title}:** {text}", ""]
        if o.get("product"):
            product=o["product"]
            lines += ["### Product thesis: "+product["name"], ""]
            for key in ["category","target_customer","buyer","job_to_be_done","why_one_product","recurring_value","entry_point","expansion_path","incumbent_absorption_risk"]:
                lines += ["**"+key.replace("_"," ").capitalize()+":** "+product[key], ""]
            for key in ["user_persona","user_job","buyer_persona","buyer_goal","buyer_user_relationship","purchase_trigger"]:
                if product.get(key): lines += ["**"+key.replace("_"," ").capitalize()+":** "+product[key], ""]
            lines += ["Related pains: "+", ".join(product["related_pain_ids"]), "", "Workflow:", ""]+["- "+v for v in product["workflow_steps"]]+[""]
        if o.get("market"):
            market=o["market"]
            lines += ["### Product market: "+market["verdict"], ""]
            for key in ["target_segment","reachable_market","pricing_logic","differentiation","switching_trigger"]:
                lines += ["**"+key.replace("_"," ").capitalize()+":** "+market[key], ""]
            lines += ["- "+v["kind"]+": "+v["claim"]+" ("+", ".join(v["source_ids"])+")" for v in market["buying_signals"]]+[""]
            for key in ["competitor_search_notes","counterevidence","remaining_validation"]:
                lines += ["**"+key.replace("_"," ").capitalize()+":**", ""]+["- "+v for v in market[key]]+[""]
        lines += ["| Dimension | Score | Confidence | Rationale | Sources |", "|---|---|---|---|---|"]
        clean = lambda s:str(s).replace("|","/").replace("\n"," ")
        for s in o["scores"]:
            lines += [f'| {DIMENSIONS[s["dimension"]][0]} | {s["value"] if s["value"] is not None else "Unknown"}/5 | {s["confidence"]} | {clean(s["rationale"])} | {", ".join(s["source_ids"])} |']
        lines += [""]
        for s in o["scores"]:
            lines += [f'**{DIMENSIONS[s["dimension"]][0]} — next evidence:** {s["next_evidence"]}', f'Assumptions: {"; ".join(s["assumptions"]) or "None recorded"}. Counterevidence: {s["counterevidence"]}', ""]
        for key in ["mvp","build_effort","upfront_cost","monthly_cost","support_burden","sales_effort","time_to_pilot","acquisition","validation_experiment","changes_since_previous"]:
            lines += [f'**{key.replace("_"," ").capitalize()}:** {o[key]}', ""]
        for key in ["dependencies","solo_blockers","constraint_conflicts","kill_criteria","uncertainties","warnings"]:
            if o.get(key):
                lines += [f'**{key.replace("_"," ").capitalize()}:**', ""] + ["- "+v for v in o[key]] + [""]
        if o["competitors"]:
            lines += ["**Alternatives checked:**", ""]
            for c in o["competitors"]:
                lines += [f'- {c["name"]}: {c["offering"]}. Pricing: {c["price_evidence"]}. Gap: {c["gap"]}. Sources: {", ".join(c["source_ids"])}']
            lines += [""]
    lines += ["## Rejected directions", ""] + ["- "+s for s in report["rejected_directions"]] + ["", "## Evidence ledger", ""]
    for s in report["sources"]:
        url = canonical_url(s["url"])
        title = s["title"].replace("[","(").replace("]",")")
        label = f'[{title}]({url})' if url else title
        lines += [f'**{s["id"]} — {label}**', f'Type: {s["kind"]} · Author: {s["speaker"] or "Unknown"} · Published: {s["published_at"] or "Unknown"} · Retrieved: {s["retrieved_at"]}', "", s["supports"], "", "Excerpt: "+s["excerpt"], ""]
    lines += ["## Limitations", ""] + ["- "+s for s in report["limitations"]+report["validation_issues"]] + ["", "## Search notes", ""] + ["- "+s for s in report["search_notes"]]
    lines += ["", "## Research context", "", "Founder profile at run time:", json.dumps(run["profile_snapshot"],ensure_ascii=False), "", "Memory applied:", ""] + ["- "+m["text"] for m in run["memory_snapshot"]]
    return "\n".join(lines)

def export(run, format):
    if format == "json":
        return json.dumps(run, indent=2, ensure_ascii=False), "application/json"
    md = markdown(run)
    if format == "md": return md, "text/markdown; charset=utf-8"
    if format == "html":
        return html_report(run), "text/html; charset=utf-8"
    if format == "csv":
        stream = io.StringIO()
        fields = ["title","status","buyer","qualified"] + list(DIMENSIONS) + ["ranking_reason","source_urls","parent_run_id","investigated_dimension","product_category","product_scope","market_verdict"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        report = run.get("report") or {}
        for o in report.get("opportunities",[]):
            pain = next(p for p in report["pains"] if p["id"] == o["pain_id"])
            row = {k:o.get(k,"") for k in fields}
            row.update({s["dimension"]:s["value"] if s["value"] is not None else "Unknown" for s in o["scores"]})
            refs = set(pain["source_ids"]) | {ref for score in o["scores"] for ref in score["source_ids"]}
            row["source_urls"] = "; ".join(s["url"] for s in report["sources"] if s["id"] in refs)
            row["product_category"] = (o.get("product") or {}).get("category", "Unassessed")
            row["product_scope"] = (o.get("product") or {}).get("scope", "Unassessed")
            row["market_verdict"] = (o.get("market") or {}).get("verdict", "Unassessed")
            row["parent_run_id"] = run.get("parent_run_id","")
            row["investigated_dimension"] = run.get("focus_dimension","")
            # Avoid formula execution when users open a CSV in spreadsheet applications.
            row = {k:("'"+str(v)) if str(v).startswith(("=","+","-","@")) else v for k,v in row.items()}
            writer.writerow(row)
        return stream.getvalue(), "text/csv; charset=utf-8"
    raise ValueError("Unsupported export format.")

def write_exports(path, run):
    Path(path).mkdir(parents=True,exist_ok=True)
    for fmt in ("md","html","json","csv"):
        (Path(path)/("report."+fmt)).write_text(export(run,fmt)[0])
