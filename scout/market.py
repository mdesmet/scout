"""Evidence gates for a coherent product and an addressable market."""
from .policy import actor

def product_market_gates(o, pains, sources):
    product, market = o.get("product"), o.get("market")
    reasons = []
    def check_refs(refs):
        for ref in refs:
            if ref not in sources: raise ValueError("Unknown product/market source: "+ref)
    def usable(refs):
        check_refs(refs)
        return [sources[ref] for ref in refs if sources[ref]["usable"] and not sources[ref]["duplicate"]]
    def substantive(text):
        value = text.strip().lower()
        return bool(value) and value not in ("unknown","n/a","none","not established","insufficient evidence") and not value.startswith(("unknown ","unknown;","not established ","unverified "))
    product_ok = False
    persona_ok = False
    market_ok = False
    if product is None:
        reasons.append("Product scope has not been assessed. Reframe related pains into a coherent product.")
    else:
        for pain_id in product["related_pain_ids"]:
            if pain_id not in pains: raise ValueError("Unknown related pain: "+pain_id)
        if o["pain_id"] not in product["related_pain_ids"]:
            raise ValueError("The primary pain must be included in the product's related pains.")
        product_evidence = usable(product["source_ids"])
        persona_evidence = usable(product.get("persona_source_ids",[]))
        linked = [pains[i] for i in set(product["related_pain_ids"])]
        accounts = {actor(s) for p in linked for s in usable(p["source_ids"]) if s["kind"]=="firsthand" and actor(s)}
        supported_pains = all(any(s["kind"]=="firsthand" for s in usable(p["source_ids"])) for p in linked)
        distinct_problems = {p["problem"].strip().casefold() for p in linked}
        persona_ok = (all(substantive(product.get(k,"")) for k in ("user_persona","user_job","buyer_persona","buyer_goal","purchase_trigger"))
                      and product.get("buyer_user_relationship") in ("same_person","different_people") and bool(persona_evidence))
        product_ok = (product["scope"]=="standalone_product" and product.get("segment_alignment")=="aligned" and persona_ok
                      and len(linked)>=2 and len(distinct_problems)>=2 and len(accounts)>=2 and supported_pains and bool(product_evidence)
                      and len({s.strip().casefold() for s in product["workflow_steps"] if s.strip()})>=2
                      and all(substantive(product[k]) for k in ("name","category","target_customer","buyer","job_to_be_done","why_one_product","recurring_value","entry_point")))
        if product["scope"] in ("bugfix","feature"):
            reasons.append("The proposed solution is a bugfix or isolated feature, not a standalone product.")
        elif product.get("segment_alignment") != "aligned":
            reasons.append("Related pain evidence comes from mixed or unknown customer segments; narrow and corroborate one buyer segment.")
        elif not persona_ok:
            reasons.append("The daily user, economic buyer, their separate goals, and purchase trigger need sourced evidence.")
        elif not product_ok:
            reasons.append("Product case needs related workflow pains, a coherent buyer/job, and recurring standalone value.")
    competitors = []
    priced_alternative = False
    for c in o["competitors"]:
        evidence = usable(c["source_ids"])
        price_evidence = usable(c.get("pricing_source_ids",[]))
        if evidence and c.get("category") and substantive(c["name"]) and substantive(c["offering"]):
            competitors.append(c)
            if c["category"] in ("direct","adjacent","native") and price_evidence and substantive(c["price_evidence"]):
                priced_alternative = True
    names = {c["name"].casefold().strip() for c in competitors}
    types = {c["category"] for c in competitors}
    competitor_ok = len(names)>=2 and bool(types & {"direct","adjacent"}) and bool(types & {"native","manual"}) and priced_alternative
    if not competitor_ok:
        reasons.append("Competition needs sourced product alternatives plus native/manual substitutes and at least one checked pricing model.")
    if market is None:
        reasons.append("The buyer segment, market demand, and switching case have not been assessed.")
    else:
        market_evidence = usable(market["source_ids"])
        buying_evidence = False
        for signal in market["buying_signals"]:
            evidence = usable(signal["source_ids"])
            if substantive(signal["claim"]) and signal["kind"] in ("customer_spending","active_buying") and any(s["kind"]=="firsthand" for s in evidence):
                buying_evidence = True
        channel_evidence = any(substantive(c["name"]) and substantive(c["target_role"]) and substantive(c["evidence"])
                               and bool(usable(c["source_ids"])) for c in market.get("acquisition_channels",[]))
        market_size_ok = substantive(market.get("bottom_up_market_estimate", "")) and bool(market.get("market_size_assumptions"))
        market_ok = (market["verdict"]=="supported" and competitor_ok and buying_evidence and bool(market_evidence)
                     and channel_evidence and market_size_ok
                     and bool(market.get("product_hunt_search_notes"))
                     and bool(market["competitor_search_notes"])
                     and all(substantive(market[k]) for k in ("target_segment","reachable_market","pricing_logic","differentiation","switching_trigger")))
        if not buying_evidence:
            reasons.append("Market demand needs firsthand spending or active buying evidence; pricing pages and funding alone are insufficient.")
        if not channel_evidence:
            reasons.append("Customer reachability needs a sourced channel that reaches the named budget owner.")
        if not market_size_ok:
            reasons.append("Market sizing needs bottom-up reasoning and explicit assumptions, or an honest Unknown.")
        if not market.get("product_hunt_search_notes"):
            reasons.append("Product Hunt competitor discovery was not documented.")
        if market["verdict"]=="contradicted":
            reasons.append("Market research contradicts the proposed product case.")
        elif not market_ok:
            reasons.append("Market case remains unproven: establish a reachable segment, differentiation, and a concrete reason to switch.")
    return dict(product_supported=product_ok, persona_supported=persona_ok, competition_checked=competitor_ok, market_supported=market_ok,
                passed=product_ok and market_ok, reasons=reasons,
                note="These gates assess research coverage and the stated business case. Customer interviews and paid pilots still need to validate the product.")
