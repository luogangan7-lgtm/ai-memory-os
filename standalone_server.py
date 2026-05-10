"""Standalone server - no Docker, no PostgreSQL, no Qdrant. SQLite + in-memory vector."""
import sys, os, json, hashlib, uuid
sys.path.insert(0, 'backend')

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

app = FastAPI(title="AI Memory OS Standalone", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# SQLite persistent store
import sqlite3, atexit
DB = Path(__file__).parent / "memory_os.db"
_conn = sqlite3.connect(str(DB), check_same_thread=False)
_conn.execute("CREATE TABLE IF NOT EXISTS memories (id TEXT PRIMARY KEY, data TEXT, vector BLOB)")
_conn.commit()
atexit.register(lambda: _conn.close())

def _save_memory(mid, data, vec):
    import struct
    blob = struct.pack(f"{len(vec)}f", *vec)
    _conn.execute("INSERT OR REPLACE INTO memories VALUES(?,?,?)", (mid, json.dumps(data), blob))
    _conn.commit()

_sklearn_model = None

def _embed(text: str) -> list[float]:
    global _sklearn_model
    if _sklearn_model is None:
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            _sklearn_model = TfidfVectorizer(max_features=384)
            print("[embed] sklearn Tfidf loaded (real sparse vectors)", file=sys.stderr)
        except ImportError:
            _sklearn_model = False
            print("[embed] sklearn not available, using hash fallback", file=sys.stderr)
    
    if _sklearn_model and _sklearn_model is not False:
        try:
            vec = _sklearn_model.fit_transform([text]).toarray()[0]
            return vec.tolist()
        except: pass
    
    # Fallback: SHA256 hash
    h = hashlib.sha256(text.encode()).digest()
    return [(h[i%32]/255*2-1) for i in range(384)]

@app.get("/")
async def root():
    return {"status": "ok", "mode": "standalone", "note": "SQLite mode - no Docker needed"}

@app.post("/memory/store")
async def store(data: dict):
    mid = str(uuid.uuid4())
    vec = _embed(data.get("content", ""))
    _save_memory(mid, data, vec)
    return {"id": mid, **data}

@app.post("/memory/search")
async def search(data: dict):
    query = data.get("query", "")
    qv = _embed(query)
    top_k = data.get("top_k", 10)
    import struct
    scores = []
    for mid, data_json, blob in _conn.execute("SELECT id, data, vector FROM memories"):
        n = len(blob) // 4
        vec = list(struct.unpack(f"{n}f", blob))
        dot = sum(a*b for a,b in zip(qv[:len(vec)], vec))
        data = json.loads(data_json)
        scores.append((dot, mid, data))
    scores.sort(key=lambda x: x[0], reverse=True)
    return [{"score": s, "memory": {"id": m, "title": d.get("title",""), "content": d.get("content",""), "category": d.get("category","")}} for s, m, d in scores[:top_k]]

@app.post("/admin/auth/register")
async def register(data: dict):
    key = "mos_" + hashlib.sha256(os.urandom(32)).hexdigest()[:32]
    return {"api_key": key, "team_id": data.get("team_id", "default")}

# Serve UI
ui = Path(__file__).parent / "backend" / "app_ui"
if ui.exists():
    app.mount("/app", StaticFiles(directory=str(ui), html=True), name="app")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
