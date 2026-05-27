"""Knowledge Enhancer — Admin public knowledge completion. Supports reasoning models."""
import json, httpx, re as _re, asyncio as _asyncio
from backend.utils.response import clean_llm_content

ENHANCE_PROMPT = 'You review this knowledge entry. If short, rewrite to 200-500 chars. Reply ONLY JSON: {"title":"...","content":"...","action":"enhanced"|"kept"}'

def _parse_json(raw: str) -> dict:
    if not raw: return {}
    raw = raw.strip()
    if not raw: return {}
    # Strip reasoning prefix (MiniMax-M2.7 etc)
    nl = chr(10)
    if nl + nl in raw[:500] and raw[:4] in ("The ", "Let "):
        raw = raw.split(nl + nl, 1)[-1]
    if raw.startswith("```"):
        raw = raw.split("```")[1].removeprefix("json")
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = _re.search(r'\{[^{}]*"action"[^{}]*\}', raw)
        if m:
            try: return json.loads(m.group())
            except: pass
    return {}

async def enhance_public_knowledge(repo, registry) -> dict:
    result = {"scanned": 0, "enhanced": 0}
    async with repo.pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id,title,content,length(content) as clen FROM memories "
            "WHERE team_id='public' AND source_type='knowledge' ORDER BY length(content) ASC LIMIT 5")
    result["scanned"] = len(rows)
    if not rows:
        return result

    engine = registry.load_llm_engine_config()
    cfg = engine.get("reflection") or engine.get("classifier") or {}
    prov = cfg.get("provider", "")
    model = cfg.get("model", "")
    base = (cfg.get("base_url") or "").rstrip("/")
    key = cfg.get("api_key", "")

    if key:
        try:
            from backend.utils.crypto import decrypt_key
            key = decrypt_key(key)
        except: pass

    if not key and prov and registry.configs.get(prov):
        p = registry.configs[prov]
        key = p.api_key
        base = base or (p.api_base or "").rstrip("/")

    if not prov: return {**result, "error": "No admin LLM configured"}
    if not key: return {**result, "error": "No API key for " + prov}

    for row in rows:
        clen = row["clen"] or 0
        if clen > 300: continue
        try:
            async with httpx.AsyncClient(timeout=60) as c:
                r = await c.post(f"{base}/chat/completions",
                    headers={"Authorization": f"Bearer {key}"},
                    json={"model":model, "messages":[
                        {"role":"system","content":ENHANCE_PROMPT},
                        {"role":"user","content":f"{row['title']}: {row['content'][:500]}"}],
                        "max_tokens":800, "temperature":0.3})
            if r.status_code != 200:
                if r.status_code == 429:
                    await _asyncio.sleep(2)
                continue
            raw = clean_llm_content(r.json()["choices"][0]["message"]["content"])
            if not raw: continue
            d = _parse_json(raw)
            if not d or d.get("action") != "enhanced": continue
            async with repo.pool.acquire() as conn2:
                await conn2.execute(
                    "UPDATE memories SET title=$1, content=$2, updated_at=NOW() WHERE id=$3",
                    d.get("title", row["title"]), d.get("content", row["content"]), row["id"])
            result["enhanced"] += 1
        except Exception as e:
            print(f"[Enhancer] {row['title'][:20]}: {e}")
    return result
