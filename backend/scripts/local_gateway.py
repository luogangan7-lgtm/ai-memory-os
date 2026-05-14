# AI Memory OS — Local Sidecar API Gateway (localhost:9999)
# Bridging legacy/local clients (Ollama, local Hermes, raw Codex) with Cloud Memory OS.
# Intercepts prompt, pulls context, forwards using native Keys, and auto-saves.

from __future__ import annotations

import argparse
import asyncio
import json
import uvicorn
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

# Setup Local App
app = FastAPI(title="AI Memory OS Local Gateway", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# CLI arguments
CLOUD_URL = "http://localhost:8000"  # Fallback to local server
API_KEY = "default"
DEFAULT_TARGET_API = "https://api.openai.com/v1" # Target API for raw models


@app.post("/v1/chat/completions")
async def local_chat_completions(request: Request):
    """Intercepts, retrieves memory context, forwards using native client keys, and saves."""
    body = await request.json()
    messages = body.get("messages", [])
    user_msg = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")

    # Headers from client to preserve their native LLM credentials
    client_headers = {}
    auth_header = request.headers.get("Authorization")
    if auth_header:
        client_headers["Authorization"] = auth_header

    # Extract target LLM provider API endpoint from request headers or fallback
    target_api_base = request.headers.get("X-Target-API-Base", DEFAULT_TARGET_API)

    # 1. Pull Knowledge Context from Cloud Memory OS REST API
    knowledge_context = ""
    headers = {"Authorization": f"Bearer {API_KEY}"}
    
    if user_msg:
        try:
            async with httpx.AsyncClient() as client:
                # Call Cloud Memory search REST endpoint
                search_res = await client.post(
                    f"{CLOUD_URL}/memory/search",
                    json={"query": user_msg, "top_k": 3},
                    headers=headers,
                    timeout=5.0
                )
                if search_res.status_code == 200:
                    results = search_res.json()
                    # Simple local compilation fallback if ContextCompiler is cloud-only
                    ctx_parts = []
                    for r in results:
                        p = r.get("payload", r)
                        ctx_parts.append(f"[{p.get('title', '知识')}] {p.get('text', '')}")
                    if ctx_parts:
                        knowledge_context = (
                            "[LOCAL SIDECAR KNOWLEDGE INJECTION]\n" +
                            "\n".join(ctx_parts) + "\n"
                        )
        except Exception as e:
            print(f"⚠️ Cloud Memory retrieval failed: {e}")

    # 2. Inject context into message structure
    final_messages = list(messages)
    if knowledge_context:
        sys_msg = next((m for m in final_messages if m["role"] == "system"), None)
        if sys_msg:
            sys_msg["content"] = f"{knowledge_context}\n{sys_msg['content']}"
        else:
            final_messages.insert(0, {"role": "system", "content": knowledge_context})

    # Prepare forwarding payload
    forward_body = dict(body)
    forward_body["messages"] = final_messages
    is_stream = body.get("stream", False)

    # 3. Transparently forward request using client's native API keys
    async def stream_generator():
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    f"{target_api_base}/chat/completions",
                    json=forward_body,
                    headers=client_headers,
                    timeout=60.0
                ) as response:
                    # Accumulator for final assistant message
                    assistant_accumulator = []
                    async for chunk in response.aiter_bytes():
                        yield chunk
                        
                        # Background parsing of assistant reply
                        try:
                            # Convert chunks to text to extract token
                            chunk_str = chunk.decode("utf-8", errors="ignore")
                            for line in chunk_str.split("\n"):
                                if line.startswith("data: ") and not line.endswith("[DONE]"):
                                    data_json = json.loads(line[6:])
                                    content = data_json["choices"][0]["delta"].get("content", "")
                                    assistant_accumulator.append(content)
                        except: pass
                        
            # 4. Once streaming is successfully completed, save memories to Cloud asynchronously
            assistant_reply = "".join(assistant_accumulator)
            if user_msg and assistant_reply:
                asyncio.create_task(
                    save_to_cloud_memory(user_msg, assistant_reply, headers)
                )
        except Exception as e:
            print(f"⚠️ Streaming connection broke: {e}")

    # Handle Non-streaming Response
    if not is_stream:
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    f"{target_api_base}/chat/completions",
                    json=forward_body,
                    headers=client_headers,
                    timeout=60.0
                )
                res_json = res.json()
                assistant_reply = res_json["choices"][0]["message"].get("content", "")
                
                # Save to Cloud asynchronously
                if user_msg and assistant_reply:
                    asyncio.create_task(
                        save_to_cloud_memory(user_msg, assistant_reply, headers)
                    )
                return res_json
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Target model execution failed: {str(e)}")

    return StreamingResponse(stream_generator(), media_type="text/event-stream")


async def save_to_cloud_memory(user: str, assistant: str, headers: dict):
    """Asynchronously store conversation to cloud server to ensure zero lag."""
    try:
        async with httpx.AsyncClient() as client:
            # 1. Store user message
            await client.post(
                f"{CLOUD_URL}/memory/remember",
                json={"content": user, "source_type": "user"},
                headers=headers,
                timeout=5.0
            )
            # 2. Store assistant message
            await client.post(
                f"{CLOUD_URL}/memory/remember",
                json={"content": assistant, "source_type": "agent"},
                headers=headers,
                timeout=5.0
            )
            print("🚀 Successfully synced local session to Cloud Memory OS.")
    except Exception as e:
        print(f"⚠️ Asynchronous background save failed: {e}")


def main():
    global CLOUD_URL, API_KEY, DEFAULT_TARGET_API
    parser = argparse.ArgumentParser(description="AI Memory OS Local Sidecar Gateway")
    parser.add_argument("--host", default="127.0.0.1", help="Local host binding")
    parser.add_argument("--port", type=int, default=9999, help="Local port binding")
    parser.add_argument("--cloud-url", default="http://localhost:8000", help="Cloud Memory OS Endpoint URL")
    parser.add_argument("--api-key", default="default", help="Your Cloud API authorization Key")
    parser.add_argument("--target-api", default="https://api.openai.com/v1", help="Default target model base URL")
    args = parser.parse_args()

    CLOUD_URL = args.cloud_url.rstrip("/")
    API_KEY = args.api_key
    DEFAULT_TARGET_API = args.target_api.rstrip("/")

    print(f"⚡ AI Memory OS Local Gateway listening on http://{args.host}:{args.port}")
    print(f"📡 Forwarding memories to Cloud: {CLOUD_URL}")
    print(f"🤖 Default LLM Target: {DEFAULT_TARGET_API}")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
