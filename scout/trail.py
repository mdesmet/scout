"""Build a cumulative, source-linked explanation of research decisions."""
import hashlib
from .models import Discovery

STAGES = {
    "pain": "pain_discovery", "synthesis": "product_synthesis",
    "market_scan": "market_scan", "assessment": "assessment", "challenge": "challenge",
}

def trail_id(stage,subject_id,decision):
    raw=f"{stage}|{subject_id}|{decision}".encode()
    return "trail-"+hashlib.sha256(raw).hexdigest()[:12]

def item(stage,subject_type,subject_id,title,decision,summary,reasons,sources,related,next_evidence):
    return dict(id=trail_id(stage,subject_id,decision),stage=stage,subject_type=subject_type,
                subject_id=subject_id,title=title,decision=decision,summary=summary,reasons=reasons,
                source_ids=list(dict.fromkeys(sources)),related_ids=list(dict.fromkeys(related)),
                next_evidence=list(dict.fromkeys(next_evidence)))

def generated(stage,data):
    label=STAGES[stage]; result=[]
    if stage=="pain":
        for p in data.get("pains",[]):
            result.append(item(label,"pain",p["id"],p["title"],"found",p["problem"],
                ["Customer-pain signal found; qualification happens after source checks."],p["source_ids"],[],p["uncertainties"]))
    elif stage=="synthesis":
        used=set()
        for product in data.get("product_hypotheses",[]):
            used.update(product["related_pain_ids"])
            decision="advanced" if product["scope"]=="standalone_product" else "rejected" if product["scope"] in ("feature","bugfix") else "watch"
            reasons=[product["why_one_product"],"Segment alignment: "+product.get("segment_alignment","unknown")+" — "+product.get("segment_alignment_reason","")]
            result.append(item(label,"product",product["name"],product["name"],decision,product["job_to_be_done"],reasons,product["source_ids"],product["related_pain_ids"],[product["entry_point"],product["incumbent_absorption_risk"]]))
        for p in data.get("pains",[]):
            if p["id"] not in used:
                result.append(item(label,"pain",p["id"],p["title"],"insufficient_evidence","Pain was not included in a coherent product thesis.",["No product hypothesis linked this pain to a recurring job for one buyer."],p["source_ids"],[],p["uncertainties"] or ["Find related pains from the same buyer segment."]))
        if not data.get("product_hypotheses"):
            result.append(item(label,"research_path","no-product","No coherent product thesis","rejected","Issue-level findings did not combine into a standalone recurring product.",["Product synthesis returned no hypotheses."],[],[p["id"] for p in data.get("pains",[])],["Find multiple related pains for one aligned buyer and budget owner."]))
    elif stage=="market_scan":
        candidates={m["product_name"]:m for m in data.get("market_candidates",[])}
        for product in data.get("product_hypotheses",[]):
            market=candidates.get(product["name"])
            if market:
                reasons=[f'{len(market["competitors"])} alternatives mapped',f'{len(market["buying_signals"])} buying/market signals',f'{len(market["product_hunt_checks"])} Product Hunt products found']+market["counterevidence"]
                refs=market["source_ids"]+[x for c in market["competitors"] for x in c["source_ids"]+c["pricing_source_ids"]]
                result.append(item(label,"market",product["name"],product["name"],"advanced","Competitor and market evidence collected.",reasons,refs,product["related_pain_ids"],[market["bottom_up_market_evidence"]]))
            else:
                result.append(item(label,"market",product["name"],product["name"],"insufficient_evidence","No market candidate was produced.",["Competitor or market evidence was insufficient."],product["source_ids"],product["related_pain_ids"],["Map alternatives, pricing, buying evidence, and an acquisition channel."]))
    else:
        for o in data.get("opportunities",[]):
            decision={"worth_validating":"advanced","watch":"watch","reject":"rejected"}[o["status"]]
            reasons=[o["ranking_reason"]]+o.get("warnings",[])
            refs=o["why_now_source_ids"]+[x for s in o["scores"] for x in s["source_ids"]]
            nxt=[x for s in o["scores"] for x in [s["next_evidence"]] if x]+o["uncertainties"]
            result.append(item(label,"opportunity",o["id"],o["title"],decision,o["thesis"],reasons,refs,[o["pain_id"]],nxt))
            if stage=="challenge" and o.get("market_checks"):
                checks=o["market_checks"]
                gate_decision="advanced" if checks["passed"] else "rejected" if o["status"]=="reject" else "insufficient_evidence"
                gate_reasons=checks["reasons"] or ["All automated product, competition, and market research gates passed; real customer validation is still required."]
                result.append(item("evidence_gate","opportunity",o["id"],o["title"]+" — final gates",gate_decision,
                    "Product, competition, and market qualification checks.",gate_reasons,refs,[o["pain_id"]],o["market"]["remaining_validation"] if o.get("market") else ["Complete product and market assessment."]))
    return result

def merge_trail(stage,data,previous=None):
    # Later model stages sometimes omit evidence retained in the prior trail. Preserve that ledger.
    existing={s["id"]:s for s in data.get("sources",[])}
    for source in (previous or {}).get("sources",[]):
        existing.setdefault(source["id"],source)
    data["sources"]=list(existing.values())
    source_ids=set(existing)
    prior=(previous or {}).get("research_trail",[])
    model=data.get("research_trail",[])
    combined=prior+model+generated(stage,data)
    result=[];seen=set()
    for entry in combined:
        unknown=set(entry["source_ids"])-source_ids
        if unknown: raise ValueError("Research trail cites unknown sources: "+", ".join(sorted(unknown)))
        signature=(entry["stage"],entry["subject_id"],entry["decision"],entry["summary"])
        if signature in seen: continue
        seen.add(signature);result.append(entry)
    data["research_trail"]=result
    return data
