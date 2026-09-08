import { useState } from "react";
import { Search, ArrowRight, ArrowUpRight, LoaderCircle } from "lucide-react";
import type { Run, Score, Opportunity, Report } from "./types";
import { dimensions, statusLabel } from "./types";

export type InvestigationState = {run:Run; opportunity:Opportunity; score:Score};
export function InvestigationForm({value,onSubmit}:{value:InvestigationState;onSubmit:(body:unknown)=>Promise<void>}){
 const [guidance,setGuidance]=useState(value.score.dimension==="willingness_to_pay"
   ? "Find customers paying for workarounds or actively seeking a replacement for this same problem. Identify the buyer and why current options fall short. Keep Unknown unless buying evidence is supported."
   : value.score.next_evidence);
 const [minutes,setMinutes]=useState(10);const [busy,setBusy]=useState(false);const [error,setError]=useState("");
 return <form onSubmit={async e=>{e.preventDefault();setBusy(true);setError("");try{await onSubmit({opportunity_id:value.opportunity.id,dimension:value.score.dimension,guidance,timeout_minutes:minutes});}catch(err){setError((err as Error).message);setBusy(false);}}}>
   <p className="muted-text">{value.opportunity.title}</p>
   <div className="focus-baseline"><strong>{dimensions[value.score.dimension]}</strong><span>{value.score.value===null?"Unknown":value.score.value+"/5"} · {value.score.confidence} confidence</span></div>
   <label>What should this follow-up investigate?<textarea autoFocus value={guidance} maxLength={5000} onChange={e=>setGuidance(e.target.value)} rows={5}/></label>
   <label>Research time limit<select aria-label="Follow-up time limit" value={minutes} onChange={e=>setMinutes(+e.target.value)}>{[5,10,20,30].map(n=><option value={n} key={n}>{n} minutes</option>)}</select></label>
   <p className="footnote">Creates a linked follow-up for this opportunity and dimension. The original report stays intact, and the other eight scores remain unchanged. Uses your Codex research allowance.</p>
   {error&&<p role="alert" className="error-text">{error}</p>}
   <button className="primary" disabled={busy}>{busy?<LoaderCircle size={16} className="spin"/>:<Search size={16}/>}Start focused research<ArrowRight size={15}/></button>
 </form>
}
export function FollowupNotice({run,onParent}:{run:Run;onParent:(id:string)=>void}){
 if(!run.parent_run_id)return null;
 return <div className="followup-notice"><div><span className="eyebrow">TARGETED FOLLOW-UP · {dimensions[run.focus_dimension!]}</span><p>{run.parent_opportunity_title}</p></div><button className="secondary" onClick={()=>onParent(run.parent_run_id!)}>Original report<ArrowUpRight size={14}/></button></div>
}
export function InvestigationSummary({report}:{report:Report}){
 const info=report.investigation;if(!info)return null;
 const score=(s:Score)=>s.value===null?"Unknown":s.value+"/5";
 return <section className="panel investigation-summary">
  <span className="eyebrow">WHAT THIS FOLLOW-UP FOUND</span>
  <h2>{dimensions[info.dimension]}</h2>
  <div className="score-diff"><div><span>Previous assessment</span><strong>{score(info.before)}</strong><small>{info.before.confidence} confidence</small></div><ArrowRight size={20}/><div><span>Updated assessment</span><strong>{score(info.after)}</strong><small>{info.after.confidence} confidence</small></div></div>
  <p>{info.conclusion}</p>
  <p className="footnote">{info.score_changed?"Score revised.":"Score unchanged."} {info.confidence_changed?"Confidence revised.":""} Status: {statusLabel(info.previous_status)} → {statusLabel(info.status)}. The other eight scores are preserved.</p>
  <h3>Findings and supporting sources</h3>
  {info.findings.length?info.findings.map((f,i)=><div className="investigation-finding" key={i}><span className="pill">{f.evidence_type.replaceAll("_"," ")}</span><p>{f.claim}</p>{f.source_ids.map(id=>{const s=report.sources.find(s=>s.id===id);return s?<a key={id} className="citation" href={/^https?:\/\//.test(s.url)?s.url:undefined} target="_blank" rel="noreferrer" title={s.title}>{id}{info.new_source_ids.includes(id)?" · new":""}<ArrowUpRight size={11}/></a>:null;})}</div>):<p>No additional supported findings were established.</p>}
  <p className="footnote">{info.new_source_ids.length} additional source observations. Findings supplement the original pain record below.</p>
 </section>
}
