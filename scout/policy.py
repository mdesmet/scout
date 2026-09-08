from __future__ import annotations
from datetime import datetime, timezone, timedelta
import hashlib
import re
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from .models import DIMENSIONS, Discovery, Report, RUBRIC_VERSION

def canonical_url(url):
    try:
        p = urlsplit(url)
        if p.scheme not in ("https", "http") or not p.hostname or p.username or p.password:
            return ""
        host = p.hostname.lower().removeprefix("www.")
        if host in ("localhost", "127.0.0.1", "::1") or host.endswith(".local"):
            return ""
        import ipaddress
        try:
            if not ipaddress.ip_address(host).is_global:
                return ""
        except ValueError:
            pass
        params = [(k,v) for k,v in parse_qsl(p.query) if not k.lower().startswith("utm_") and k not in ("ref", "source")]
        return urlunsplit(("https", host, p.path.rstrip("/") or "/", urlencode(sorted(params)), ""))
    except (TypeError, ValueError):
        return ""

def date_value(text):
    if not text: return None
    try:
        return datetime.fromisoformat(text.replace("Z","+00:00")).replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None

def actor(source):
    name = re.sub(r"[^a-z0-9]", "", (source.get("speaker") or "").lower())
    if not name or name in {"anonymous", "unknown", "verifiedreviewer", "user", "customer", "unnamed"}:
        return None
    org = re.sub(r"[^a-z0-9]", "", (source.get("organization") or "").lower())
    # Same organization/author is not treated as two independent customer accounts.
    return "org:" + org if org and org not in {"unknown","none","na"} else "speaker:" + name

def evaluate(payload, *, days=90, at=None, max_opportunities=5):
    data = Report.model_validate(payload).model_dump()
    at = at or datetime.now(timezone.utc)
    issues = []
    sources = {}
    fingerprints = set()
    for s in data["sources"]:
        if s["id"] in sources:
            raise ValueError("Duplicate source identifier: " + s["id"])
        url = canonical_url(s["url"])
        retrieval = date_value(s["retrieved_at"])
        published = date_value(s["published_at"])
        origin = (canonical_url(s["origin_url"]) if s["origin_url"] else "") or url
        fingerprint = hashlib.sha256(re.sub(r"\s+", " ", s["excerpt"].lower()).strip().encode()).hexdigest()
        valid = bool(url and s["accessed"] and s["excerpt"].strip() and retrieval and retrieval.date() <= at.date() and (not published or published.date() <= at.date()))
        duplicate = bool(url in fingerprints or origin in fingerprints or fingerprint in fingerprints)
        if url: fingerprints.add(url)
        if origin: fingerprints.add(origin)
        fingerprints.add(fingerprint)
        s["usable"] = valid
        s["duplicate"] = duplicate
        s["stale"] = bool(published and published < at-timedelta(days=days))
        s["date_known"] = bool(published)
        if not valid: issues.append("Source " + s["id"] + " is inaccessible, incomplete, future-dated, or has an invalid URL.")
        sources[s["id"]] = s
    pains = {}
    for p in data["pains"]:
        if p["id"] in pains: raise ValueError("Duplicate pain identifier: " + p["id"])
        for ref in p["source_ids"] + p["consequence_source_ids"]:
            if ref not in sources: raise ValueError("Unknown pain source: " + ref)
        p_sources = [sources[i] for i in p["source_ids"]]
        independent = {actor(s) for s in p_sources if s["usable"] and not s["duplicate"] and s["kind"] == "firsthand" and actor(s)}
        consequence = any(i in p["source_ids"] and sources[i]["usable"] and not sources[i]["duplicate"] and sources[i]["kind"] == "firsthand" for i in p["consequence_source_ids"])
        p["independent_accounts"] = len(independent)
        p["qualified"] = len(independent) >= 2 and consequence
        p["gate_reason"] = "Two independent firsthand accounts and a sourced consequence/workaround." if p["qualified"] else "Needs two independent firsthand accounts and at least one sourced consequence/workaround."
        pains[p["id"]] = p
    seen = set()
    for o in data["opportunities"]:
        if o["id"] in seen: raise ValueError("Duplicate opportunity identifier.")
        seen.add(o["id"])
        if o["pain_id"] not in pains: raise ValueError("Unknown pain identifier.")
        if len(o["scores"]) != len(DIMENSIONS) or {s["dimension"] for s in o["scores"]} != set(DIMENSIONS):
            raise ValueError("Each opportunity must have exactly the nine score dimensions.")
        refs = o["why_now_source_ids"] + [i for c in o["competitors"] for i in c["source_ids"]]
        for ref in refs:
            if ref not in sources: raise ValueError("Unknown opportunity source: " + ref)
        warnings = []
        for score in o["scores"]:
            for ref in score["source_ids"]:
                if ref not in sources: raise ValueError("Unknown score source: " + ref)
            usable = [sources[i] for i in score["source_ids"] if sources[i]["usable"]]
            if score["value"] is not None and not usable:
                score["value"] = None
                score["confidence"] = "low"
                warnings.append(score["dimension"] + ": no usable support; changed to Unknown.")
            if not score["rationale"].strip():
                score["value"] = None
                score["confidence"] = "low"
                warnings.append(score["dimension"] + ": missing rationale; changed to Unknown.")
            if usable and all(s["stale"] or not s["date_known"] for s in usable):
                score["confidence"] = "low"
                warnings.append(score["dimension"] + ": old or undated evidence; confidence reduced.")
        pain = pains[o["pain_id"]]
        o["qualified"] = pain["qualified"]
        if o["status"] == "worth_validating":
            if not pain["qualified"]:
                o["status"] = "watch"
                warnings.append("Pain gate failed: " + pain["gate_reason"])
            if o["solo_blockers"] or o["constraint_conflicts"]:
                o["status"] = "reject"
                warnings.append("Unresolved solo blocker or explicit founder constraint.")
            scores = {s["dimension"]:s["value"] for s in o["scores"]}
            if any(scores[k] is None for k in ["pain_severity", "willingness_to_pay", "solo_feasibility"]):
                o["status"] = "watch" if o["status"] != "reject" else "reject"
                warnings.append("Critical dimension remains Unknown.")
            elif scores["pain_severity"] < 3 or scores["willingness_to_pay"] < 3 or scores["solo_feasibility"] < 3:
                o["status"] = "watch" if o["status"] != "reject" else "reject"
                warnings.append("Pain, buying evidence, and solo feasibility must each reach the rubric's middle anchor.")
        o["warnings"] = warnings
        from .market import product_market_gates
        o["market_checks"] = product_market_gates(o,pains,sources)
        if o.get("product",{}) and o["product"]["scope"] in ("bugfix","feature"):
            o["status"] = "reject"
        elif o.get("market",{}) and o["market"]["verdict"] == "contradicted":
            o["status"] = "reject"
        elif o["status"] == "worth_validating" and not o["market_checks"]["passed"]:
            o["status"] = "watch"
        if o["status"] == "worth_validating":
            opening = next(s["value"] for s in o["scores"] if s["dimension"] == "competitive_opening")
            if opening is None or opening < 3:
                o["status"] = "watch"
                o["market_checks"]["reasons"].append("The proposed competitive opening is weak or unestablished.")
        o["warnings"].extend(o["market_checks"]["reasons"])
        o["fingerprint"] = hashlib.sha256(re.sub(r"[^a-z0-9]", "", o["buyer"].lower()+"|"+pain["workflow"].lower()+"|"+o["solution"].lower()).encode()).hexdigest()[:16]
    if len(data["opportunities"]) > max_opportunities:
        raise ValueError("Report exceeds the requested opportunity limit.")
    data["validation_issues"] = issues
    data["rubric_version"] = RUBRIC_VERSION
    data["assessed_at"] = at.isoformat()
    data["qualification_note"] = "Scores are research assessments, not probabilities of success. Source classification and claim entailment are model judgments; validation checks structural evidence quality, not authenticity."
    return data

def validate_discovery(payload):
    d = Discovery.model_validate(payload).model_dump()
    ids = [s["id"] for s in d["sources"]]
    if len(set(ids)) != len(ids): raise ValueError("Duplicate discovery sources.")
    if len({p["id"] for p in d["pains"]}) != len(d["pains"]): raise ValueError("Duplicate pains.")
    if any(i not in ids for p in d["pains"] for i in p["source_ids"] + p["consequence_source_ids"]):
        raise ValueError("Discovery contains unresolved citations.")
    return d
