#!/usr/bin/env python3
"""Memory Daemon - auto-captures agent I/O, stores & retrieves memories."""
import os, sys, json, httpx, time, queue, threading, re
from pathlib import Path

SERVER = os.environ.get("MEMORY_OS_URL", "http://localhost:8000")
API_KEY = os.environ.get("MEMORY_OS_KEY", "")
AGENT_ID = os.environ.get("MEMORY_OS_AGENT", "auto-agent")
TEAM = os.environ.get("MEMORY_OS_TEAM", "default")

def api(method, path, **kw):
    h = {"Authorization": f"Bearer {API_KEY}"}
    if "json" in kw:
        h["Content-Type"] = "application/json"
        r = httpx.request(method, f"{SERVER}{path}", headers=h, json=kw["json"], timeout=30)
    else:
        r = httpx.request(method, f"{SERVER}{path}", headers=h, timeout=30)
    r.raise_for_status()
    return r.json()

def register():
    global API_KEY, AGENT_ID
    if not API_KEY:
        try:
            d = api("POST", "/admin/auth/register", json={"team_id": TEAM, "agent_id": AGENT_ID})
            API_KEY = d["api_key"]
            print(f"[memory] Registered: {AGENT_ID} (key: {API_KEY[:12]}...)", file=sys.stderr)
        except: pass

def remember(content: str):
    try:
        api("POST", "/memory/remember", json={
            "title": content[:80], "content": content,
            "category": "agent-memory", "importance": 0.6
        })
    except: pass

def search(query: str, top_k=5) -> list[str]:
    try:
        results = api("POST", "/memory/search", json={"query": query, "top_k": top_k})
        return [f"[{r['memory']['title']}] {r['memory']['content'][:200]}" for r in results]
    except:
        return []

_capture_queue = queue.Queue()

def _capture_worker():
    """Single worker thread for memory storage."""
    while True:
        try: text = _capture_queue.get(timeout=30)
        except queue.Empty: continue
        try: remember(text)
        except: pass

threading.Thread(target=_capture_worker, daemon=True).start()

def auto_capture(text: str, min_len=50):
    """Enqueue interesting agent outputs for storage."""
    if len(text) > min_len and not text.startswith("[memory]"):
        _capture_queue.put_nowait(text)

def inject_memories(text: str) -> str:
    """Search for relevant memories and prepend them."""
    queries = re.findall(r'(?:search|find|recall|what do we know about|look up)\s+(.+?)(?:\?|\.|$)', text, re.I)
    if not queries:
        return text
    all_results = []
    for q in queries[:2]:
        results = search(q.strip(), top_k=3)
        if results:
            all_results.append(f"[Memory: {q.strip()}]")
            all_results.extend(results)
    if all_results:
        return "[MEMORY CONTEXT]\n" + "\n".join(all_results) + "\n[/MEMORY CONTEXT]\n\n" + text
    return text

# ── Main: pipe mode ──
def pipe_mode():
    """Read stdin line by line, auto-store, inject on search triggers."""
    register()
    print("[memory] Daemon active. Pipe your agent I/O through here.", file=sys.stderr)
    for line in sys.stdin:
        line = line.strip()
        if not line: continue
        # Auto-store interesting output
        auto_capture(line)
        # Inject memories on search triggers
        enhanced = inject_memories(line)
        print(enhanced, flush=True)

if __name__ == "__main__":
    pipe_mode()
