from fastapi import APIRouter, Request, HTTPException, Depends, status
from fastapi.responses import StreamingResponse
import httpx, json, asyncio, tiktoken
from datetime import datetime, timezone
from backend.auth.middleware import get_current_team, get_agent_id

router = APIRouter(prefix="/v1", tags=["proxy"])

def count_tokens(text: str) -> int:
    """Helper to compute exact or estimated token counts using tiktoken cl100k_base."""
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except Exception:
        # Fallback heuristic: approx 1.3 tokens per word, 2 per Chinese character
        return int(len(text) * 1.5)

@router.post("/chat/completions")
async def chat_completions(
    request: Request,
    team_id: str = Depends(get_current_team),
    agent_id: str = Depends(get_agent_id)
):
    body = await request.json()
    messages = body.get("messages", [])
    user_msg = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    
    from backend.api.routes import pg_repo, retrieval, registry
    if not pg_repo:
        raise HTTPException(status_code=503, detail="Database repository not initialized")

    # 1. Fetch user's custom active provider keys (Commercial zero-墊资 model)
    provider_config = await pg_repo.get_active_user_provider_config(team_id)
    if not provider_config:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "no_provider_configured",
                "message": "商用部署模式：请先在用户端个人设置【算力中心】配置并激活您的 AI Provider API Key，系统所有者不垫付任何费用。",
                "setup_url": "/app/settings/providers"
            }
        )

    api_key = provider_config["api_key"]
    api_base_url = provider_config["api_base_url"]
    model_name = provider_config["model_name"]
    provider_name = provider_config["provider_name"]

    # 2. Automatic Memory Retrieval (Context Injection)
    history_to_inject = []
    knowledge_context = ""
    
    try:
        # A. Fetch chronological history (Last 10 turns for continuity)
        rows = await pg_repo.list_recent(team_id, limit=10, filter="agent")
        for row in reversed(rows):
            role = "assistant" if row["source_type"] == "agent" else "user"
            history_to_inject.append({"role": role, "content": row["content"]})
        
        # B. Semantic Search (Knowledge Base)
        if user_msg and retrieval and registry:
            results = await retrieval.search(
                query=user_msg, embedding_fn=registry.embed_single,
                team_id=team_id, top_k=3
            )
            from backend.services.context_compiler import ContextCompiler
            knowledge_context = ContextCompiler.compile_context(results, user_msg)
    except Exception as e:
        print(f"[Memory OS] Background memory retrieval failed: {e}")

    # 3. Message Deduplication and System Context Injection
    existing_contents = {m["content"] for m in messages}
    new_history = [m for m in history_to_inject if m["content"] not in existing_contents]
    final_messages = new_history + messages
    
    if knowledge_context:
        sys_msg = next((m for m in final_messages if m["role"] == "system"), None)
        if sys_msg:
            sys_msg["content"] = f"{knowledge_context}\n{sys_msg['content']}"
        else:
            final_messages.insert(0, {"role": "system", "content": knowledge_context})

    # 4. Routing request to upstream provider
    is_stream = body.pop("stream", False)
    body.pop("messages", None)
    body.pop("model", None) # override request model with user's configured model

    upstream_endpoint = f"{api_base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model_name,
        "messages": final_messages,
        "stream": is_stream,
        **body
    }

    # Recompute prompt tokens
    prompt_tokens = count_tokens(json.dumps(final_messages))

    if not is_stream:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(upstream_endpoint, json=payload, headers=headers)
                if resp.status_code != 200:
                    raise HTTPException(resp.status_code, f"Upstream error ({resp.status_code}): {resp.text}")
                
                resp_json = resp.json()
                assistant_msg = resp_json.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                # Log usage & save message to memory
                usage = resp_json.get("usage", {})
                p_tok = usage.get("prompt_tokens", prompt_tokens)
                c_tok = usage.get("completion_tokens", count_tokens(assistant_msg))
                
                if assistant_msg:
                    asyncio.create_task(pg_repo.add_message(team_id, agent_id, "user", user_msg))
                    asyncio.create_task(pg_repo.add_message(team_id, agent_id, "assistant", assistant_msg))
                    asyncio.create_task(pg_repo.insert_user_token_usage(
                        user_id=team_id,
                        provider_name=provider_name,
                        model_name=model_name,
                        prompt_tokens=p_tok,
                        completion_tokens=c_tok,
                        total_tokens=p_tok + c_tok
                    ))
                return resp_json
        except Exception as e:
            raise HTTPException(500, f"Upstream connection failed: {str(e)}")

    # Handle Stream Mode
    else:
        async def sse_stream_generator():
            completion_text = ""
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    async with client.stream("POST", upstream_endpoint, json=payload, headers=headers) as stream:
                        async for chunk in stream.aiter_bytes():
                            yield chunk
                            
                            # Parse token deltas asynchronously from the SSE chunks
                            try:
                                chunk_str = chunk.decode(errors="ignore")
                                for line in chunk_str.split("\n"):
                                    line = line.strip()
                                    if line.startswith("data: "):
                                        data_str = line[6:]
                                        if data_str == "[DONE]":
                                            continue
                                        data_json = json.loads(data_str)
                                        delta_text = data_json.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                        completion_text += delta_text
                            except Exception:
                                pass
                
                # Asynchronously commit text to knowledge memories and user billing log
                if completion_text:
                    completion_tokens = count_tokens(completion_text)
                    asyncio.create_task(pg_repo.add_message(team_id, agent_id, "user", user_msg))
                    asyncio.create_task(pg_repo.add_message(team_id, agent_id, "assistant", completion_text))
                    asyncio.create_task(pg_repo.insert_user_token_usage(
                        user_id=team_id,
                        provider_name=provider_name,
                        model_name=model_name,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=prompt_tokens + completion_tokens
                    ))
            except Exception as stream_err:
                print(f"[Memory OS] Upstream streaming failed: {stream_err}")

        return StreamingResponse(sse_stream_generator(), media_type="text/event-stream")

