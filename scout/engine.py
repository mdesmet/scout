from __future__ import annotations
import json
import copy
import re
import threading
import time
from pathlib import Path
from .models import RunInput, InvestigationInput, InvestigationResult, Discovery, ProductDiscovery, MarketDiscovery, ReframeInput, PromptDiscoveryInput, PromptDiscoveryResult, DIMENSIONS
from .policy import evaluate, validate_discovery
from .research import collect_public_signals, codex_stage, make_prompt, make_prompt_discovery_prompt, ResearchInterrupted
from .store import now, uid, Superseded
from .sources import collect_github_trending

class Engine:
    def __init__(self, store, provider=codex_stage, collector=collect_public_signals, trending_collector=collect_github_trending):
        self.store = store
        self.provider = provider
        self.collector = collector
        self.trending_collector = trending_collector
        self.stop_event = threading.Event()
        self.thread = None

    def start(self):
        # Interrupted jobs become resumable; completed evidence remains untouched.
        for r in self.store.all("run"):
            if r["status"] in ("running","queued"):
                self.store.update_run(r["id"], dict(status="paused", message="Server restarted. Resume from the last completed checkpoint."))
        for discovery in self.store.all("prompt_discovery"):
            if discovery["status"] in ("queued","running"):
                discovery.update(status="failed",message="Server restarted before direction discovery completed.",updated_at=now())
                self.store.put("prompt_discovery",discovery["id"],discovery)
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()

    def shutdown(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=6)

    def busy(self, except_id=None):
        return (any(r["id"] != except_id and r["status"] in ("queued","running") for r in self.store.all("run"))
                or any(r["id"] != except_id and r["status"] in ("queued","running") for r in self.store.all("prompt_discovery")))

    def discover_prompts(self,payload):
        request=PromptDiscoveryInput.model_validate(payload).model_dump()
        with self.store.lock:
            if self.busy(): raise ValueError("A research job is already active. Finish or pause it before discovering directions.")
            ctx=self.store.context();discovery_id=uid()
            record=dict(id=discovery_id,**request,status="running",message="Searching for founder-matched problem spaces.",created_at=now(),updated_at=now(),profile_snapshot=ctx["profile"],memory_snapshot=ctx["memory"],result=None,usage=None)
            self.store.put("prompt_discovery",discovery_id,record)
        started=time.monotonic()
        def check():
            if time.monotonic()-started>=request["timeout_minutes"]*60:raise TimeoutError("Direction discovery reached its time limit.")
        def emit(kind,message):self.store.event(discovery_id,kind,message)
        try:
            trending_seeds,trending_logs=self.trending_collector(check,emit)
            prompt=make_prompt_discovery_prompt(request,dict(profile=ctx["profile"],memory=ctx["memory"],feedback=ctx["feedback"][:20],trending_searches=trending_logs),trending_seeds)
            workdir=self.store.root/"prompt-discoveries"/discovery_id
            output,usage=self.provider("prompt_discovery",prompt,workdir,check,emit)
            result=PromptDiscoveryResult.model_validate(output).model_dump()
            source_ids={s["id"] for s in result["sources"]}
            if len(source_ids)!=len(result["sources"]):raise ValueError("Direction discovery returned duplicate source IDs.")
            if len(result["prompts"])>request["max_prompts"]:raise ValueError("Direction discovery exceeded the requested prompt limit.")
            if any(not set(item["source_ids"])<=source_ids for item in result["prompts"]):raise ValueError("A direction cites an unknown source.")
            record.update(status="completed",message=f'{len(result["prompts"])} scouting directions found.',result=result,usage=usage,updated_at=now())
            self.store.put("prompt_discovery",discovery_id,record)
            return record
        except Exception as exc:
            record.update(status="failed",message=str(exc)[:1400],updated_at=now())
            self.store.put("prompt_discovery",discovery_id,record)
            raise

    def create(self, payload, *, lineage=None):
        with self.store.lock:
            if self.busy():
                raise ValueError("A scout is already running. Pause or stop it before starting another.")
            brief = RunInput.model_validate(payload).model_dump()
            ctx = self.store.context()
            run_id = uid()
            run = dict(id=run_id, **brief, revision=1, status="queued", stage="queued", message="Research queued.",
                       created_at=now(), updated_at=now(), steering=[], profile_snapshot=ctx["profile"],
                       memory_snapshot=ctx["memory"], feedback_snapshot=ctx["feedback"], elapsed_seconds=0,
                       checkpoints={}, report=None, usage=[], demo=False, corrections_pending=False, pipeline_version=2)
            if lineage:
                run.update(lineage)
            self.store.put("run", run_id, run)
            self.store.event(run_id, "brief", "Starting with customer pain and your current preferences.", revision=1)
            return run

    def investigate(self, parent_id, payload):
        import copy
        request = InvestigationInput.model_validate(payload).model_dump()
        with self.store.lock:
            parent = self.store.get("run", parent_id)
            if parent is None: raise KeyError(parent_id)
            if parent.get("demo"): raise ValueError("Synthetic examples cannot be investigated. Select a completed live report.")
            if parent["status"] != "completed" or not parent.get("report"):
                raise ValueError("Finish or resume the parent research before investigating a score.")
            o = next((o for o in parent["report"]["opportunities"] if o["id"] == request["opportunity_id"]), None)
            if o is None: raise KeyError(request["opportunity_id"])
            lineage = dict(parent_run_id=parent_id, parent_opportunity_id=o["id"],
                           parent_opportunity_title=o["title"], focus_dimension=request["dimension"],
                           investigation_guidance=request["guidance"], parent_report_snapshot=copy.deepcopy(parent["report"]),
                           profile_snapshot=copy.deepcopy(parent["profile_snapshot"]))
            child = self.create(dict(keywords=parent["keywords"], context=parent["context"], days=parent["days"],
                                     max_opportunities=1, timeout_minutes=request["timeout_minutes"]),lineage=lineage)
            self.store.event(child["id"],"investigation", "Investigating "+DIMENSIONS[request["dimension"]][0]+" for "+o["title"]+". Original report preserved.",revision=1)
            return child

    def reframe(self, parent_id, payload):
        import copy
        request = ReframeInput.model_validate(payload).model_dump()
        with self.store.lock:
            parent = self.store.get("run",parent_id)
            if parent is None: raise KeyError(parent_id)
            if parent.get("demo") or parent["status"] != "completed" or not parent.get("report"):
                raise ValueError("Select a completed live report to reframe its product and market.")
            o = next((o for o in parent["report"]["opportunities"] if o["id"]==request["opportunity_id"]),None)
            if o is None: raise KeyError(request["opportunity_id"])
            seed = dict(previous_opportunity=copy.deepcopy(o), pains=copy.deepcopy(parent["report"]["pains"]), sources=copy.deepcopy(parent["report"]["sources"]))
            child = self.create(dict(keywords=parent["keywords"],context=parent["context"],days=parent["days"],max_opportunities=parent["max_opportunities"],timeout_minutes=request["timeout_minutes"]),
                                lineage=dict(reframed_from_run_id=parent_id,reframed_from_opportunity_id=o["id"],reframe_seed=seed,reframe_guidance=request["guidance"]))
            self.store.event(child["id"],"reframe","Reframing the underlying customer problem into a product, then validating its market. The old report is preserved.",revision=1)
            return child

    def control(self, run_id, action):
        with self.store.lock:
            r = self.store.get("run", run_id)
            if r is None: raise KeyError(run_id)
            if action == "resume":
                if r["status"] not in ("paused","partial","failed"):
                    raise ValueError("Only paused or incomplete runs can resume.")
                if self.busy(run_id): raise ValueError("Another run is active.")
                # Each explicit resume grants a new configured research window.
                r["elapsed_seconds"] = 0
                r["status"] = "queued"
                r["message"] = "Resuming from completed checkpoints."
                if r.get("pipeline_version",1) < 2 and not r.get("parent_run_id"):
                    r["revision"] += 1
                    r.update(pipeline_version=2,stage="queued",report=None,message="Resuming with product synthesis and market validation. Earlier checkpoints are retained as source leads.")
            elif action in ("pause","cancel"):
                if r["status"] not in ("queued","running","paused"):
                    raise ValueError("This run is not active.")
                r["status"] = "paused" if action == "pause" else "cancelled"
                r["message"] = "Paused; completed evidence is retained." if action == "pause" else "Stopped; completed evidence is retained."
            else:
                raise ValueError("Unknown control.")
            self.store.put("run", run_id, r)
            self.store.event(run_id, action, r["message"], revision=r["revision"])
            return r

    def steer(self, run_id, message, remember, impact="auto"):
        with self.store.lock:
            r = self.store.get("run", run_id)
            if not r: raise KeyError(run_id)
            if r.get("demo"): raise ValueError("Start a live run to redirect research.")
            if self.busy(run_id): raise ValueError("Another run is active.")
            if r["status"] not in ("running","queued","paused","partial","failed"):
                raise ValueError("This run has finished. Start another search with your new direction.")
            if remember:
                m = self.store.add_memory(message, "explicit", ["Steering on run "+run_id], True)
            requested_impact = impact
            resolved_impact = self.classify_steering(message,r,impact)
            previous_revision = r["revision"]
            old_cp = r["checkpoints"].get(str(previous_revision),{})
            restart_from, preserved = self.steering_checkpoint_plan(r,resolved_impact,old_cp)
            r["revision"] += 1
            new_cp = {stage:copy.deepcopy(old_cp[stage]) for stage in preserved if stage in old_cp}
            r["checkpoints"][str(r["revision"])] = new_cp
            r["steering"].append(dict(message=message, remember=remember, at=now(), revision=r["revision"],
                                      requested_impact=requested_impact,resolved_impact=resolved_impact,
                                      restart_from=restart_from,preserved_stages=preserved))
            r["status"] = "queued"
            r["stage"] = "queued"
            r["report"] = None
            ctx = self.store.context()
            r.update(profile_snapshot=ctx["profile"], memory_snapshot=ctx["memory"], feedback_snapshot=ctx["feedback"])
            labels={"signals":"signal collection","pain":"customer pain","synthesis":"product synthesis","market_scan":"market evidence","assessment":"scoring","challenge":"skeptical review","investigate":"focused evidence","verify_investigation":"focused verification"}
            r["message"] = "Direction updated. Preserved "+(", ".join(preserved) if preserved else "no completed stages")+"; resuming at "+labels.get(restart_from,restart_from)+"."
            self.store.put("run", run_id, r)
            self.store.event(run_id, "steer", message, revision=r["revision"], remembered=remember,
                             requested_impact=requested_impact,resolved_impact=resolved_impact,
                             restart_from=restart_from,preserved_stages=preserved)
            return r

    def classify_steering(self,message,run,impact="auto"):
        allowed={"source_refinement","market_refinement","product_reframing","full_restart"}
        if impact in allowed:return impact
        text=message.casefold()
        patterns=[
            ("full_restart",r"\b(new|different|change|switch)\s+(customer|audience|industry|market|problem|topic|keywords?)\b|\bstart over\b"),
            ("product_reframing",r"\b(product|solution|scope|bundle|workflow|reframe|mvp|feature set)\b"),
            ("market_refinement",r"\b(competitor|alternative|pricing|price|willingness|market size|tam|demand|buyer|channel|product hunt|switching)\b"),
            ("source_refinement",r"\b(source|evidence|citation|date|verify|review|forum|search query|firsthand|corroborat)\b"),
        ]
        for name,pattern in patterns:
            if re.search(pattern,text):return name
        return "source_refinement"

    def steering_checkpoint_plan(self,run,impact,checkpoint):
        focused=bool(run.get("parent_run_id"))
        order=["investigate","verify_investigation"] if focused else ["signals","pain","synthesis","market_scan","assessment","challenge"]
        if focused:
            target=run.get("stage") if impact=="source_refinement" and run.get("stage") in order else "investigate"
        else:
            targets={"source_refinement":run.get("stage"),"market_refinement":"market_scan","product_reframing":"synthesis","full_restart":"signals"}
            target=targets.get(impact,"signals")
            if target not in order:target=next((s for s in order if s not in checkpoint),"challenge")
            current=run.get("stage")
            if current in order and order.index(current)<order.index(target):target=current
        index=order.index(target)
        preserved=[stage for stage in order[:index] if stage in checkpoint]
        return target,preserved

    def loop(self):
        while not self.stop_event.is_set():
            queued = [r for r in self.store.all("run") if r["status"] == "queued"]
            if queued:
                self.execute(queued[-1])
            else:
                self.stop_event.wait(0.25)

    def execute(self, run):
        run_id, revision = run["id"], run["revision"]
        segment_start = time.monotonic()
        elapsed_before = run["elapsed_seconds"]
        def check():
            latest = self.store.get("run", run_id)
            if self.stop_event.is_set() or latest["status"] not in ("queued","running") or latest["revision"] != revision:
                raise ResearchInterrupted()
            if elapsed_before + time.monotonic()-segment_start >= run["timeout_minutes"]*60:
                raise TimeoutError("Research time limit reached. Resume to grant another research window.")
        def emit(kind, message):
            check()
            self.store.event(run_id, kind, message, revision=revision)
        def checkpoint(name, payload):
            check()
            with self.store.lock:
                latest = self.store.get("run", run_id)
                if latest["revision"] != revision: raise ResearchInterrupted()
                latest["checkpoints"].setdefault(str(revision), {})[name] = payload
                self.store.put("run", run_id, latest)
            out = self.store.root/"runs"/run_id/str(revision)
            out.mkdir(parents=True, exist_ok=True)
            (out/(name+".json")).write_text(json.dumps(payload, indent=2))
        try:
            check()
            self.store.update_run(run_id, dict(status="running"), revision)
            cp = run["checkpoints"].get(str(revision), {}).copy()
            if run.get("parent_run_id"):
                report = self.execute_investigation(run,cp,check,emit,checkpoint)
                with self.store.lock:
                    check()
                    self.store.update_run(run_id,dict(report=report,status="completed",stage="complete",message="Focused investigation complete. Compare the new evidence and score with the original report.",corrections_pending=False),revision)
                self.store.event(run_id,"complete", "Follow-up complete; the original report and other eight scores are preserved.",revision=revision)
                from .reports import write_exports
                write_exports(self.store.root/"runs"/run_id/"exports",self.store.get("run",run_id))
                return
            if "signals" not in cp:
                self.store.update_run(run_id, dict(stage="discover", message="Collecting dated public signals."), revision)
                cp["signals"] = self.collector(run["keywords"], run["days"], check, emit)
                checkpoint("signals", cp["signals"])
            history = []
            for previous in self.store.all("run"):
                if previous["id"] != run_id and not previous.get("demo") and previous.get("report"):
                    for o in previous["report"]["opportunities"]:
                        rejected = [f["reason"] for f in self.store.all("feedback") if f["run_id"] == previous["id"] and f.get("opportunity_id") == o["id"] and f["kind"] == "reject"]
                        history.append(dict(run_id=previous["id"], opportunity_id=o["id"], title=o["title"], buyer=o["buyer"], status=o["status"], rejected_by_user=rejected, thesis=o["thesis"], fingerprint=o.get("fingerprint"), ranking_reason=o["ranking_reason"], scores=[dict(dimension=s["dimension"],value=s["value"],confidence=s["confidence"]) for s in o["scores"]], at=previous["created_at"]))
            for stage, previous in [("pain",None),("synthesis","pain"),("market_scan","synthesis"),("assessment","market_scan"),("challenge","assessment")]:
                if stage == "market_scan" and not cp.get("synthesis",{}).get("product_hypotheses"):
                    report = self.no_product_report(cp["synthesis"],run)
                    with self.store.lock:
                        check()
                        self.store.update_run(run_id,dict(report=report,status="completed",stage="complete",message="No coherent standalone product passed synthesis. Market research stopped early.",corrections_pending=False),revision)
                    self.store.event(run_id,"complete","No coherent product thesis; skipped competitor and market stages.",revision=revision)
                    from .reports import write_exports
                    write_exports(self.store.root/"runs"/run_id/"exports",self.store.get("run",run_id))
                    return
                if stage in cp: continue
                check()
                messages = {"pain":"Finding related customer problems and buying categories.", "synthesis":"Grouping related pains into coherent product hypotheses.", "market_scan":"Mapping competitors, substitutes, pricing, buying evidence, and customer channels.", "assessment":"Validating the product market and scoring the opportunity.", "challenge":"Challenging standalone product value, market demand, and OPC feasibility."}
                self.store.update_run(run_id, dict(stage=stage, message=messages[stage]), revision)
                emit("stage", messages[stage])
                prior = cp.get(previous) if previous else None
                if stage == "pain" and revision > 1 and run.get("steering") and run["steering"][-1].get("restart_from")=="pain":
                    old = self.store.get("run", run_id)["checkpoints"].get(str(revision-1), {})
                    prior = {"superseded_brief_evidence_only": old.get("pain"), "instruction": "Reuse relevant source evidence, but reassess every pain under the new direction. Old conclusions are not approved."}
                prompt = make_prompt(stage, run, cp["signals"], prior, history[:25], self.store.learning_summary())
                # New attempt directories avoid accepting stale output after an interrupted stage.
                workdir = self.store.root/"runs"/run_id/str(revision)/(stage+"-"+uid())
                output, usage = self.provider(stage, prompt, workdir, check, emit)
                check()
                if stage == "pain":
                    output = validate_discovery(output)
                elif stage == "synthesis":
                    output = ProductDiscovery.model_validate(output).model_dump()
                    validate_discovery({k:v for k,v in output.items() if k != "product_hypotheses"})
                    pain_ids = {p["id"] for p in output["pains"]}
                    source_ids = {s["id"] for s in output["sources"]}
                    for product in output["product_hypotheses"]:
                        if not set(product["related_pain_ids"]) <= pain_ids or not set(product["source_ids"]) <= source_ids:
                            raise ValueError("Product synthesis references unknown pain or source IDs.")
                elif stage == "market_scan":
                    output = MarketDiscovery.model_validate(output).model_dump()
                    validate_discovery({k:v for k,v in output.items() if k in Discovery.model_fields})
                    product_names = {p["name"] for p in output["product_hypotheses"]}
                    source_ids = {s["id"] for s in output["sources"]}
                    for market in output["market_candidates"]:
                        if market["product_name"] not in product_names:
                            raise ValueError("Market scan references an unknown product hypothesis.")
                        refs = market["source_ids"]
                        refs += [x for c in market["competitors"] for x in c["source_ids"]+c["pricing_source_ids"]]
                        refs += [x for signal in market["buying_signals"] for x in signal["source_ids"]]
                        refs += [x for channel in market["acquisition_channels"] for x in channel["source_ids"]]
                        refs += [x for product in market["product_hunt_checks"] for x in product["source_ids"]]
                        if not set(refs) <= source_ids:
                            raise ValueError("Market scan references unknown sources.")
                else:
                    from .investigation import clean_report
                    output = clean_report(evaluate(output, days=run["days"], max_opportunities=run["max_opportunities"]))
                from .trail import merge_trail
                output = merge_trail(stage,output,cp.get(previous) if previous else None)
                checkpoint(stage, output)
                cp[stage] = output
                latest = self.store.get("run", run_id)
                self.store.update_run(run_id, dict(usage=latest["usage"]+[usage]), revision)
            check()
            report = evaluate(cp["challenge"], days=run["days"], max_opportunities=run["max_opportunities"])
            from .trail import merge_trail
            report = merge_trail("challenge",report,cp.get("assessment"))
            self.annotate_changes(report, history)
            with self.store.lock:
                check()
                self.store.update_run(run_id, dict(report=report, status="completed", stage="complete", message="Research complete. Review the scorecards and tell Scout what to learn.", corrections_pending=False), revision)
            self.store.event(run_id, "complete", f'{sum(o["status"]=="worth_validating" for o in report["opportunities"])} opportunities worth validating; all nine dimensions assessed separately.', revision=revision)
            from .reports import write_exports
            write_exports(self.store.root/"runs"/run_id/"exports", self.store.get("run",run_id))
        except (ResearchInterrupted, Superseded):
            pass
        except Exception as e:
            latest = self.store.get("run", run_id)
            if latest["revision"] == revision and latest["status"] in ("queued","running"):
                partial = latest["checkpoints"].get(str(revision),{}).get("assessment")
                partial_report = evaluate(partial,days=run["days"],max_opportunities=run["max_opportunities"]) if partial else None
                if run.get("parent_run_id"):
                    draft = latest["checkpoints"].get(str(revision),{}).get("investigate")
                    if draft:
                        from .investigation import merge_investigation
                        partial_report = merge_investigation(run,draft)
                self.store.update_run(run_id, dict(status="partial" if latest["checkpoints"] else "failed", message=str(e)[:1400], report=partial_report), revision)
                self.store.event(run_id, "error", str(e)[:1400], revision=revision)
        finally:
            with self.store.lock:
                latest = self.store.get("run", run_id)
                if latest:
                    latest["elapsed_seconds"] += round(time.monotonic()-segment_start,2)
                    if self.stop_event.is_set() and latest["status"] == "running":
                        latest.update(status="paused",message="Server stopped. Resume from completed checkpoints.")
                    self.store.put("run", run_id, latest)

    def execute_investigation(self,run,cp,check,emit,checkpoint):
        from .investigation import focused_prompt, merge_investigation
        messages = {"investigate":"Searching specifically for "+DIMENSIONS[run["focus_dimension"]][0].lower()+" evidence.",
                    "verify_investigation":"Challenging the new evidence and proposed score."}
        for stage in ("investigate","verify_investigation"):
            if stage in cp: continue
            check()
            self.store.update_run(run["id"],dict(stage=stage,message=messages[stage]),run["revision"])
            emit("stage",messages[stage])
            draft = cp.get("investigate")
            if draft is None and run["revision"] > 1:
                draft = self.store.get("run",run["id"])["checkpoints"].get(str(run["revision"]-1),{}).get("investigate")
            prompt = focused_prompt(stage,run,draft)
            workdir = self.store.root/"runs"/run["id"]/str(run["revision"])/(stage+"-"+uid())
            output,usage = self.provider(stage,prompt,workdir,check,emit)
            check()
            output = InvestigationResult.model_validate(output).model_dump()
            merge_investigation(run,output)  # Reject ID collisions or unrelated scores before checkpointing.
            checkpoint(stage,output)
            cp[stage] = output
            latest = self.store.get("run",run["id"])
            self.store.update_run(run["id"],dict(usage=latest["usage"]+[usage]),run["revision"])
        report = merge_investigation(run,cp["verify_investigation"])
        o = report["opportunities"][0]
        parent_o = next(o for o in run["parent_report_snapshot"]["opportunities"] if o["id"] == run["parent_opportunity_id"])
        rejected = parent_o["status"] == "reject" or any(f["kind"] == "reject" and f["run_id"] == run["parent_run_id"] and f.get("opportunity_id") == parent_o["id"] for f in self.store.all("feedback"))
        if rejected and o["status"] == "worth_validating" and (not report["investigation"]["new_source_ids"] or len(report["investigation"]["conclusion"].strip()) < 40):
            o["status"] = "watch"
            o["warnings"].append("Previously rejected; needs a material change supported by new evidence.")
            report["investigation"]["status"] = o["status"]
        return report

    def annotate_changes(self, report, history):
        by_name = {h["title"].casefold():h for h in reversed(history)}
        for o in report["opportunities"]:
            previous = next((h for h in history if h.get("fingerprint") == o["fingerprint"]), None) or by_name.get(o["title"].casefold())
            o["score_changes"] = []
            if previous:
                prev = {s["dimension"]:s["value"] for s in previous["scores"]}
                o["score_changes"] = [dict(dimension=s["dimension"], before=prev.get(s["dimension"]), after=s["value"]) for s in o["scores"] if prev.get(s["dimension"]) != s["value"]]
                o["previous_status"] = previous["status"]
                if (previous["status"] == "reject" or previous.get("rejected_by_user")) and o["status"] == "worth_validating":
                    explanation = o["changes_since_previous"].strip()
                    if len(explanation) < 40 or explanation.lower().startswith(("first assessment", "first illustrative", "no change", "new opportunity")):
                        o["status"] = "watch"
                        o["warnings"].append("Previously rejected. A specific material change must be explained before recommending it again.")
            else:
                o["previous_status"] = None

    def no_product_report(self,synthesis,run):
        payload = dict(summary="No coherent standalone product could be formed from the researched customer pains.",
                       pains=synthesis["pains"],sources=synthesis["sources"],search_notes=synthesis["search_notes"],research_trail=synthesis.get("research_trail",[]),
                       limitations=synthesis["limitations"]+["Competitor, Product Hunt, market-size and scoring stages were skipped because there was no product thesis to validate."],
                       opportunities=[],rejected_directions=["Issue-level findings did not combine into a recurring product job for one aligned buyer segment."])
        return evaluate(payload,days=run["days"],max_opportunities=run["max_opportunities"])
