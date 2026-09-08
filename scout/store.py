from __future__ import annotations
import json
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

def now():
    return datetime.now(timezone.utc).isoformat()

def uid():
    return uuid.uuid4().hex[:16]

class Superseded(Exception):
    pass

class Store:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "scout.sqlite3"
        self.lock = threading.RLock()
        with self.connect() as db:
            db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS records(kind TEXT, id TEXT, data TEXT NOT NULL, PRIMARY KEY(kind,id));
            CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL, data TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS event_run ON events(run_id,id);
            """)
        if not self.get("profile", "default"):
            self.put("profile", "default", dict(skills="", interests="Emerging AI and data opportunities", customer_access="", geography="", time_available="", budget="", assets="", exclusions=""))
        if not self.get("meta", "initialized"):
            self.add_memory("Prefer opportunities suitable for one founder. Assess money and time requirements case by case; do not assume privileged access, an operating team, or exclusive data.", "explicit", ["Initial approved brief"], True)
            self.add_memory("Start with customer pain. Prefer emerging demand and a specific competitive opening over famous, crowded app categories.", "explicit", ["Initial approved brief"], True)
            self.put("meta", "initialized", {"at": now()})

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def get(self, kind, item_id):
        with self.connect() as db:
            row = db.execute("SELECT data FROM records WHERE kind=? AND id=?", (kind, item_id)).fetchone()
            return json.loads(row["data"]) if row else None

    def all(self, kind):
        with self.connect() as db:
            return [json.loads(r["data"]) for r in db.execute("SELECT data FROM records WHERE kind=? ORDER BY rowid DESC", (kind,))]

    def put(self, kind, item_id, data):
        with self.lock, self.connect() as db:
            db.execute("INSERT INTO records VALUES(?,?,?) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data", (kind, item_id, json.dumps(data)))

    def update_run(self, run_id, changes, revision=None):
        with self.lock:
            run = self.get("run", run_id)
            if run is None:
                raise KeyError(run_id)
            if revision is not None and run["revision"] != revision:
                raise Superseded()
            run.update(changes)
            run["updated_at"] = now()
            self.put("run", run_id, run)
            return run

    def event(self, run_id, kind, message, **data):
        item = dict(type=kind, message=message, at=now(), **data)
        with self.connect() as db:
            cur = db.execute("INSERT INTO events(run_id,data) VALUES(?,?)", (run_id, json.dumps(item)))
            item["id"] = cur.lastrowid
        return item

    def events(self, run_id, after=0):
        with self.connect() as db:
            return [dict(json.loads(r["data"]), id=r["id"]) for r in db.execute("SELECT id,data FROM events WHERE run_id=? AND id>? ORDER BY id", (run_id, after))]

    def memories(self, include_inactive=False):
        return [m for m in self.all("memory") if include_inactive or (m["active"] and not m.get("forgotten"))]

    def add_memory(self, text, kind, origins, confirmed=False, tag=None):
        with self.lock:
            item_id = "inferred-" + tag if tag else uid()
            old = self.get("memory", item_id)
            if old:
                if not old["active"] or old.get("forgotten"):
                    return None
                return old
            item = dict(id=item_id, text=text, kind=kind, origins=origins, confirmed=confirmed, active=True, forgotten=False, created_at=now(), updated_at=now(), history=[], tag=tag)
            self.put("memory", item_id, item)
            return item

    def edit_memory(self, item_id, changes):
        with self.lock:
            m = self.get("memory", item_id)
            if not m:
                raise KeyError(item_id)
            snapshot = {k:v for k,v in m.items() if k != "history"}
            m["history"].append(snapshot)
            m.update(changes)
            m["updated_at"] = now()
            self.put("memory", item_id, m)
            return m

    def undo_memory(self, item_id):
        with self.lock:
            m = self.get("memory", item_id)
            if not m or not m["history"]:
                raise ValueError("No earlier version to restore.")
            history = m["history"]
            previous = history.pop()
            previous.update(history=history, updated_at=now())
            self.put("memory", item_id, previous)
            return previous

    def context(self):
        memories = self.memories()
        suppressed = {o for m in self.memories(True) if not m["active"] or m.get("forgotten") for o in m["origins"]}
        feedback = [f for f in self.all("feedback") if f["id"] not in suppressed][:40]
        return dict(profile=self.get("profile", "default"), memory=memories, feedback=feedback)

    def learning_summary(self):
        feedback = self.all("feedback")
        outcomes = [f for f in feedback if f["kind"] == "outcome"]
        domain_stats = {}
        predictions = []
        for f in feedback:
            run = self.get("run", f["run_id"])
            if not run or run.get("demo") or not run.get("report"):
                continue
            report = run["report"]
            selected = next((o for o in report["opportunities"] if o["id"] == f.get("opportunity_id")), None)
            if selected and f["kind"] == "outcome":
                predictions.append(dict(opportunity=selected["title"], predicted_status=selected["status"], outcome=f["outcome"], amount=f.get("amount"), reason=f["reason"], at=f["created_at"]))
            if not selected:
                continue
            pain = next((p for p in report["pains"] if p["id"] == selected["pain_id"]), None)
            if not pain:
                continue
            from urllib.parse import urlsplit
            domains = {urlsplit(s["url"]).hostname for s in report["sources"] if s["id"] in pain["source_ids"]}
            for domain in domains:
                stats = domain_stats.setdefault(domain, dict(interested=0, rejected=0, outcomes=0))
                if f["kind"] == "interested": stats["interested"] += 1
                if f["kind"] == "reject": stats["rejected"] += 1
                if f["kind"] == "outcome": stats["outcomes"] += 1
        return dict(feedback_count=len(feedback), outcome_count=len(outcomes), comparisons=predictions[:30], source_feedback=domain_stats, caveat="Feedback counts are directional and can include repeat interactions. Paid outcomes are user-reported, not independently verified. Source popularity does not establish reliability.")

PREFERENCES = {
    "self_serve": "Tentative preference: favor products developers can adopt themselves over a long enterprise sales process.",
    "emerging_markets": "Tentative preference: favor evidence of emerging demand over mature or stagnant categories.",
    "low_operations": "Tentative preference: avoid products with a large recurring support or service burden.",
    "solo_buildable": "Tentative preference: favor a tightly bounded product one founder can build and operate.",
    "accessible_data": "Tentative preference: favor accessible data sources over exclusive partnerships or privileged data access.",
}

def infer_tag(reason):
    t = reason.lower()
    if any(x in t for x in ["self-serve", "enterprise sales", "sales cycle"]): return "self_serve"
    if any(x in t for x in ["booming", "stagnant", "emerging market", "growing market"]): return "emerging_markets"
    if any(x in t for x in ["support burden", "too much support", "too operational"]): return "low_operations"
    if any(x in t for x in ["one person", "one-person", "not opc", "large team", "solo"]): return "solo_buildable"
    if any(x in t for x in ["exclusive data", "privileged access", "partnership"]): return "accessible_data"
    return None

def learn(store, feedback):
    if feedback["remember"]:
        # Store the user's exact words as a preference, never as a market fact.
        return store.add_memory(feedback["reason"], "explicit", [feedback["id"]], True)
    tag = feedback.get("preference_tag") or infer_tag(feedback["reason"])
    if tag not in PREFERENCES or feedback["kind"] not in ("reject", "direction"):
        return None
    same = [f for f in store.all("feedback") if f["kind"] in ("reject", "direction") and (f.get("preference_tag") or infer_tag(f["reason"])) == tag]
    distinct = {(f["run_id"], f.get("opportunity_id")) for f in same}
    if len(distinct) < 2:
        return None
    return store.add_memory(PREFERENCES[tag], "inferred", [f["id"] for f in same], False, tag)
