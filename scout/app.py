from __future__ import annotations
import asyncio
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import shutil
from urllib.parse import urlsplit
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response, StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from .store import Store, now, uid, learn
from .models import RunInput, Steering, Feedback, MemoryEdit, ProfileInput, InvestigationInput, ReframeInput, PromptDiscoveryInput, DIMENSIONS, RUBRIC_VERSION
from .engine import Engine
from .reports import export
from .demo import create_demo

ROOT = Path(__file__).resolve().parents[1]

def create_app(data_dir=None, engine_factory=Engine, start_worker=True):
    store = Store(data_dir or os.environ.get("SCOUT_DATA_DIR", str(ROOT/"data")))
    engine = engine_factory(store)
    @asynccontextmanager
    async def lifespan(app):
        if start_worker: engine.start()
        yield
        if start_worker: engine.shutdown()
    app = FastAPI(title="Opportunity Scout", lifespan=lifespan)
    app.state.store = store
    app.state.engine = engine
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost","127.0.0.1","testserver"])

    @app.middleware("http")
    async def local_origin(request, call_next):
        origin = request.headers.get("origin")
        if request.method not in ("GET","HEAD","OPTIONS") and origin:
            parsed = urlsplit(origin)
            if parsed.scheme != "http" or parsed.hostname not in ("localhost","127.0.0.1","testserver") or (parsed.port not in (None,5173,8765) and parsed.netloc != request.url.netloc):
                return JSONResponse({"detail":"Only the local Scout workspace may make changes."},status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.exception_handler(ValueError)
    async def value_error(request, exc):
        return JSONResponse({"detail":str(exc)},status_code=409)
    @app.exception_handler(KeyError)
    async def missing(request, exc):
        return JSONResponse({"detail":"Not found."},status_code=404)

    def get_run(run_id):
        run = store.get("run",run_id)
        if run is None: raise HTTPException(404,"Run not found.")
        return run

    @app.get("/api/health")
    def health():
        return dict(ok=True,codex_available=bool(shutil.which("codex")),rubric_version=RUBRIC_VERSION,dimensions={k:v[0] for k,v in DIMENSIONS.items()},rubric=DIMENSIONS)

    @app.get("/api/profile")
    def profile():
        return store.get("profile","default")
    @app.put("/api/profile")
    def update_profile(payload:ProfileInput):
        value=payload.model_dump()
        store.put("profile","default",value)
        return value

    @app.get("/api/runs")
    def runs():
        return [{k:v for k,v in r.items() if k not in ("checkpoints","report","feedback_snapshot","parent_report_snapshot","reframe_seed")} | dict(opportunity_count=len((r.get("report") or {}).get("opportunities",[]))) for r in store.all("run")]

    @app.post("/api/runs")
    def new_run(payload:RunInput):
        return engine.create(payload.model_dump())
    @app.get("/api/prompt-discoveries")
    def prompt_discoveries():
        return store.all("prompt_discovery")
    @app.post("/api/prompt-discoveries")
    def discover_prompts(payload:PromptDiscoveryInput):
        return engine.discover_prompts(payload.model_dump())
    @app.post("/api/runs/{run_id}/investigate")
    def investigate(run_id:str,payload:InvestigationInput):
        return engine.investigate(run_id,payload.model_dump())
    @app.post("/api/runs/{run_id}/reframe")
    def reframe(run_id:str,payload:ReframeInput):
        return engine.reframe(run_id,payload.model_dump())
    @app.post("/api/example")
    def example():
        return create_demo(store)
    @app.get("/api/runs/{run_id}")
    def run_detail(run_id:str):
        return get_run(run_id)
    @app.post("/api/runs/{run_id}/steer")
    def steer(run_id:str,payload:Steering):
        return engine.steer(run_id,payload.message,payload.remember,payload.impact)
    @app.post("/api/runs/{run_id}/control/{action}")
    def control(run_id:str,action:str):
        return engine.control(run_id,action)

    @app.get("/api/runs/{run_id}/events")
    async def events(run_id:str,request:Request,after:int=0):
        get_run(run_id)
        try: last=int(request.headers.get("last-event-id",after))
        except ValueError: last=after
        async def stream():
            nonlocal last
            while not await request.is_disconnected():
                for event in store.events(run_id,last):
                    last=event["id"]
                    yield f'id: {last}\ndata: {json.dumps(event)}\n\n'
                r=get_run(run_id)
                if r["status"] not in ("running","queued"):
                    yield 'event: idle\ndata: {}\n\n'
                    return
                yield ": heartbeat\n\n"
                await asyncio.sleep(0.7)
        return StreamingResponse(stream(),media_type="text/event-stream",headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})

    @app.get("/api/runs/{run_id}/export/{format}")
    def download(run_id:str,format:str):
        if format not in ("md","html","json","csv"): raise HTTPException(400,"Unknown export format.")
        content,mime=export(get_run(run_id),format)
        return Response(content,media_type=mime,headers={"Content-Disposition":f'attachment; filename="scout-{run_id}.{format}"'})

    @app.get("/api/feedback")
    def feedback_list():
        return store.all("feedback")
    @app.post("/api/feedback")
    def feedback(payload:Feedback):
        run=get_run(payload.run_id)
        if run.get("demo"):
            raise HTTPException(400,"Example feedback is disabled so synthetic results cannot train your preferences. Add a preference in Memory instead.")
        if payload.opportunity_id and not any(o["id"]==payload.opportunity_id for o in (run.get("report") or {}).get("opportunities",[])):
            raise HTTPException(404,"Opportunity not found.")
        if payload.remember and payload.kind not in ("direction","reject"):
            raise HTTPException(400,"Only a personal preference or direction can be saved as lasting memory. Outcomes and source corrections remain evidence to verify.")
        f=dict(id=uid(),created_at=now(),**payload.model_dump())
        if payload.kind == "correction" and run.get("report"):
            f["evidence_context"] = [dict(id=s["id"],url=s["url"],supports=s["supports"]) for s in run["report"]["sources"]]
        store.put("feedback",f["id"],f)
        memory=learn(store,f)
        if payload.kind=="correction":
            store.update_run(run["id"],dict(corrections_pending=True))
        store.event(run["id"],"feedback",f'Feedback recorded: {payload.kind}.',opportunity_id=payload.opportunity_id)
        return dict(feedback=f,learned=memory)

    @app.get("/api/memory")
    def memories():
        return store.memories(True)
    @app.post("/api/memory")
    def add_memory(payload:MemoryEdit):
        return store.add_memory(payload.text,"explicit",["Added in Memory"],payload.confirmed)
    @app.put("/api/memory/{item_id}")
    def edit_memory(item_id:str,payload:MemoryEdit):
        return store.edit_memory(item_id,payload.model_dump())
    @app.post("/api/memory/{item_id}/undo")
    def undo(item_id:str):
        return store.undo_memory(item_id)
    @app.delete("/api/memory/{item_id}")
    def forget(item_id:str):
        return store.edit_memory(item_id,dict(text="",active=False,forgotten=True))
    @app.get("/api/learning")
    def learning():
        return store.learning_summary()

    dist=ROOT/"dist"
    if dist.exists():
        app.mount("/assets",StaticFiles(directory=dist/"assets"),name="assets")
        @app.get("/")
        def index(): return FileResponse(dist/"index.html")
        @app.get("/{full_path:path}")
        def workspace_route(full_path:str):
            if full_path.startswith(("api/","assets/")):
                raise HTTPException(404,"Not found.")
            return FileResponse(dist/"index.html")
    else:
        @app.get("/")
        def no_build():
            return JSONResponse({"message":"Run npm run build to serve the workspace, or npm run dev for development.","api":"/docs"})
    return app

app=create_app()
