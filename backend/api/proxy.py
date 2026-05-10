from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse
import httpx, json, time, uuid
from datetime import datetime, timezone
from backend.auth.middleware import get_current_team, get_agent_id

router = APIRouter(prefix="/v1", tags=["proxy"])

@router.post("/chat/completions")
async def chat_completions(
    request: Request,
    team_id: str = Depends(get_current_team),
    agent_id: str = Depends(get_agent_id)
):
    body = await request.json()
    messages = body.get("messages", [])
    user_msg = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    
    # Get active provider settings
    from backend.services.config import settings
    provider_config = settings.providers.get(settings.active_provider, {})
    real_key = provider_config.get("api_key")
    if not real_key:
        raise HTTPException(status_code=500, detail=f"No API key configured for {settings.active_provider}")
        
    base_url = "https://api.openai.com"
    if settings.active_provider == "aliyun":
        base_url = "https://dashscope.aliyuncs.com/compatible-mode"
    elif settings.active_provider == "zhipu":
        base_url = "https://open.bigmodel.cn/api/paas/v4"
    
    # 1. Search memory for relevant context
    memory_context = ""
    t0 = time.time()
    from backend.api.routes import pg_repo, retrieval, registry
    if user_msg and retrieval and registry:
        try:
            results = await retrieval.search(
                query=user_msg, embedding_fn=registry.embed_single,
                team_id=team_id, top_k=5, use_rerank=False
            )
            ctx_parts = [f"[{r['payload'].get('title', '')}] {r['payload'].get('text', '')[:200]}" for r in results[:3]]
            if ctx_parts:
                memory_context = "[MEMORY CONTEXT]\n" + "\n".join(ctx_parts) + "\n[/MEMORY CONTEXT]"
        except Exception as e:
            pass
    t1 = time.time()
    
    # 2. Inject memory into system message
    if memory_context:
        sys_idx = next((i for i, m in enumerate(messages) if m["role"] == "system"), None)
        if sys_idx is not None:
            messages[sys_idx]["content"] = memory_context + "\n\n" + messages[sys_idx]["content"]
        else:
            messages.insert(0, {"role": "system", "content": memory_context})
    
    # 3. Forward to real API
    headers = {"Authorization": f"Bearer {real_key}", "Content-Type": "application/json"}
    payload = {**body, "messages": messages}
    
    is_stream = body.get("stream", False)
    client = httpx.AsyncClient(timeout=120)
    
    try:
        if is_stream:
            # We use send to get the response stream, then stream it back
            req = client.build_request("POST", f"{base_url}/v1/chat/completions", json=payload, headers=headers)
            resp = await client.send(req, stream=True)
            t2 = time.time()
            # Store memory internally (fire and forget basically)
            if user_msg and pg_repo:
                await pg_repo.insert(
                    id=str(uuid.uuid4()), team_id=team_id, workspace_id="default", agent_id=agent_id,
                    category="agent-memory", subcategory=None, topic=None, memory_type="general",
                    title=user_msg[:80], content=user_msg, embedding_model="text-embedding-v3",
                    importance=0.6, confidence=0.8, source_type="agent", tags=[]
                )
            return StreamingResponse(resp.aiter_bytes(), media_type="text/event-stream", background=client.aclose)
        else:
            resp = await client.post(f"{base_url}/v1/chat/completions", json=payload, headers=headers)
            t2 = time.time()
            data = resp.json()
            
            # Record metrics
            try:
                from backend.services.cost_tracker import CostTracker
                usage = data.get("usage", {})
                in_tok = usage.get("prompt_tokens", 0)
                out_tok = usage.get("completion_tokens", 0)
                # Compute baseline token count difference roughly
                base_in = sum(len(m["content"]) for m in body.get("messages", [])) // 2
                saved = (base_in + len(memory_context) // 2) - in_tok if memory_context else 0
                CostTracker.record(f"proxy-{settings.active_provider}", in_tok, out_tok, round((t2-t1)*1000, 1))
            except Exception: pass
            
            # Auto-store the conversation including the assistant response
            if user_msg and pg_repo:
                assistant_msg = next((c["message"]["content"] for c in data.get("choices", []) if "message" in c), "")
                content_to_save = f"User: {user_msg}\nAssistant: {assistant_msg}"
                await pg_repo.insert(
                    id=str(uuid.uuid4()), team_id=team_id, workspace_id="default", agent_id=agent_id,
                    category="agent-memory", subcategory=None, topic=None, memory_type="dialogue",
                    title=user_msg[:80], content=content_to_save, embedding_model="text-embedding-v3",
                    importance=0.7, confidence=0.9, source_type="agent", tags=[]
                )
            
            await client.aclose()
            return data
    except Exception as e:
        await client.aclose()
        raise HTTPException(500, f"Proxy request failed: {str(e)}")
