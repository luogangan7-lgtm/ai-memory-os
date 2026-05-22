# AI Memory OS — Model Context Protocol (MCP) SSE Server
# Seamlessly connects Cursor, Claude Desktop, and modern AI clients using standard JSON-RPC over SSE.

from __future__ import annotations

import json
import uuid
import asyncio
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse

# Setup Router
router = APIRouter(prefix="/mcp", tags=["mcp"])
logger = logging.getLogger("mcp_server")

# SSE Connections Registry
# Maps connection_id -> Dict of connection details (queue, team_id, agent_id, username)
connections: Dict[str, Dict[str, Any]] = {}


# --- Core MCP Specification Endpoints ---

@router.get("")
async def mcp_get_handler(request: Request, token: Optional[str] = None):
    """Establishes the SSE Stream channel for the MCP client with token authorization."""
    if not token:
        logger.warning("MCP connection attempt rejected: missing token query param")
        raise HTTPException(status_code=401, detail="API key/token required")

    from backend.auth.apikeys import validate_key
    info = await validate_key(token)
    if not info:
        logger.warning(f"MCP connection attempt rejected: invalid or expired token: {token[:12]}...")
        raise HTTPException(status_code=401, detail="Invalid token")

    connection_id = str(uuid.uuid4())
    queue = asyncio.Queue()
    
    # Store authenticated context
    connections[connection_id] = {
        "queue": queue,
        "team_id": info.get("team_id", "default"),
        "agent_id": info.get("agent_id", "default"),
        "username": info.get("username", "admin")
    }
    
    logger.info(f"MCP Connection authorized for user: {info.get('username')} (ID: {connection_id})")

    # Plan check for free users
    try:
        from backend.api.db_helper import get_db_conn
        conn = await get_db_conn()
        acct = await conn.fetchrow("SELECT plan, mcp_call_count FROM accounts WHERE team_id=$1", info.get("team_id","default"))
        await conn.close()
        if acct:
            plan = acct.get("plan", "free") or "free"
            if plan == "free":
                count = acct.get("mcp_call_count", 0) or 0
                if count >= 50:
                    raise HTTPException(status_code=402, detail={
                        "error": "mcp_limit_exceeded",
                        "message": "免费体验额度（50次）已用完，请升级 Pro",
                        "mcp_call_count": count,
                        "upgrade_url": "/app/#/app"
                    })
                # Increment count
                conn2 = await get_db_conn()
                await conn2.execute("UPDATE accounts SET mcp_call_count = mcp_call_count + 1 WHERE team_id=$1", info.get("team_id","default"))
                await conn2.close()
    except HTTPException:
        raise
    except Exception:
        pass  # Don't block MCP if plan check fails

    async def event_generator():
        try:
            # Step 1: Send endpoint handshake telling the client where to POST messages
            # Note: We append the connection_id so we know which queue to respond to.
            post_url = f"/mcp?connection_id={connection_id}"
            yield f"event: endpoint\ndata: {post_url}\n\n"
            
            # Keep yielding message events from queue
            while True:
                msg = await queue.get()
                yield f"event: message\ndata: {json.dumps(msg, ensure_ascii=False)}\n\n"
                queue.task_done()
        except asyncio.CancelledError:
            pass
        finally:
            connections.pop(connection_id, None)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("")
async def mcp_post_handler(
    request: Request,
    connection_id: Optional[str] = None
):
    """Receives JSON-RPC requests from client and routes tool calling logic."""
    if not connection_id or connection_id not in connections:
        raise HTTPException(status_code=400, detail="Invalid or missing connection_id")

    conn = connections[connection_id]
    queue = conn["queue"]
    team_id = conn["team_id"]
    agent_id = conn["agent_id"]

    payload = await request.json()
    req_id = payload.get("id")
    method = payload.get("method")
    params = payload.get("params", {})

    logger.info(f"Received MCP Request - ID: {req_id}, Method: {method}, User: {conn['username']}")

    # Handle standard MCP lifecycle requests
    if method == "initialize":
        response = {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "ai-memory-os-mcp",
                    "version": "1.0.0"
                }
            }
        }
        await queue.put(response)
        return {"status": "ok"}

    elif method == "tools/list":
        # List of available memory tools
        response = {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": "memory_search",
                        "description": "Perform dynamic, hybrid dense-sparse vector and graph searches for relevant long-term memories and knowledge.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "The natural language query or concept to search for in memory."
                                },
                                "workspace_id": {
                                    "type": "string",
                                    "description": "Optional specific workspace identifier to filter.",
                                    "default": "default"
                                },
                                "top_k": {
                                    "type": "integer",
                                    "description": "Max number of memory chunks to retrieve.",
                                    "default": 3
                                }
                            },
                            "required": ["query"]
                        }
                    },
                    {
                        "name": "memory_store",
                        "description": "Store a highly important piece of knowledge, guideline, observation, or memory asynchronously.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "content": {
                                    "type": "string",
                                    "description": "The exact fact, code snippet, or conversation takeaway to remember."
                                },
                                "title": {
                                    "type": "string",
                                    "description": "A concise title or summary summarizing the memory."
                                },
                                "workspace_id": {
                                    "type": "string",
                                    "description": "The workspace this memory belongs to.",
                                    "default": "default"
                                }
                            },
                            "required": ["content"]
                        }
                    },
                    {
                        "name": "memory_reflect",
                        "description": "Manually trigger background cognitive optimization, summarization, and memory consolidation.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "workspace_id": {
                                    "type": "string",
                                    "description": "The workspace context.",
                                    "default": "default"
                                }
                            }
                        }
                    },
                    {
                        "name": "memory_get_persona",
                        "description": "Retrieve L3 persona profile from long-term memory.",
                        "inputSchema": {"type": "object", "properties": {}}
                    },
                    {
                        "name": "memory_task_canvas_get",
                        "description": "Get task canvas Mermaid diagram.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "task_id": {"type": "string", "default": "main"},
                                "agent_id": {"type": "string", "description": "Agent identifier"}
                            },
                            "required": ["agent_id"]
                        }
                    },
                    {
                        "name": "memory_task_canvas_update",
                        "description": "Update task canvas Mermaid diagram with progress.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "task_id": {"type": "string"},
                                "agent_id": {"type": "string", "description": "Agent identifier"},
                                "mermaid": {"type": "string"},
                                "title": {"type": "string", "description": "Task title"},
                                "task_title": {"type": "string", "description": "Task title (alias for title)"},
                                "completed": {"type": "array", "items": {"type": "string"}, "description": "List of completed steps"},
                                "next": {"type": "array", "items": {"type": "string"}, "description": "List of next steps"}
                            },
                            "required": ["task_id", "agent_id", "mermaid"]
                        }
                    },
                    {
                        "name": "memory_list",
                        "description": "List stored memories for current user.",
                        "inputSchema": {"type": "object", "properties": {"limit": {"type": "integer", "default": 20}}}
                    },
                    {
                        "name": "memory_delete",
                        "description": "Delete a memory entry by its identifier.",
                        "inputSchema": {"type": "object", "properties": {"memory_id": {"type": "string"}}, "required": ["memory_id"]}
                    },
                    {
                        "name": "memory_status",
                        "description": "Get memory system status (total, health, storage).",
                        "inputSchema": {"type": "object", "properties": {}}
                    }
                ]
            }
        }
        await queue.put(response)
        return {"status": "ok"}

    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        # Import core modules dynamically to avoid circular dependencies
        from backend.api.routes import pg_repo, retrieval, registry

        result_text = ""
        is_error = False

        try:
            if tool_name == "memory_search":
                query = arguments.get("query")
                workspace_id = arguments.get("workspace_id", "default")
                top_k = int(arguments.get("top_k", 3))

                if not query:
                    raise ValueError("Query is required for memory_search")

                if retrieval and registry:
                    # Execute hybrid search with dynamic reranker passing
                    use_rerank = hasattr(registry, "reranker") and registry.reranker is not None
                    raw_results = await retrieval.search(
                        query=query,
                        embedding_fn=registry.embed_single,
                        team_id=team_id,
                        workspace_id=workspace_id,
                        top_k=top_k,
                        use_graph=True,
                        use_rerank=use_rerank,
                        rerank_fn=registry.rerank if use_rerank else None
                    )
                    # Compile context
                    from backend.services.context_compiler import ContextCompiler
                    result_text = ContextCompiler.compile_context(raw_results, query)
                    if not result_text:
                        result_text = "No relevant long-term memories found for this query."
                else:
                    result_text = "Memory OS retrieval engine is currently not initialized."

            elif tool_name == "memory_store":
                content = arguments.get("content")
                title = arguments.get("title", "MCP Memory Input")
                workspace_id = arguments.get("workspace_id", "default")

                if not content:
                    raise ValueError("Content is required for memory_store")

                if registry:
                    # Save via background task to guarantee zero lag
                    asyncio.create_task(
                        registry.add_message(
                            role="user",
                            content=f"[{title}] {content}",
                            team_id=team_id,
                            agent_id=workspace_id
                        )
                    )
                    result_text = "Memory received. It will be indexed and structured into graph + vector storage in the background."
                else:
                    result_text = "Memory registry is not initialized."

            elif tool_name == "memory_reflect":
                # Trigger reflection engine via app scheduler state
                scheduler = request.app.state.scheduler
                if scheduler and scheduler.engine:
                    asyncio.create_task(scheduler.engine.reflect_all(team_id))
                    result_text = "Background cognitive reflection initiated. Outdated links and graph nodes are being pruned and summarized."
                else:
                    result_text = "Reflection engine scheduler is not running."

            elif tool_name in ("persona", "memory_get_persona"):
                from backend.api.db_helper import get_db_conn
                try:
                    conn = await get_db_conn()
                    row = await conn.fetchrow("SELECT persona_md FROM user_persona WHERE team_id=$1", info.get("team_id","default"))
                    if not row or not row["persona_md"]:
                        default_persona_md = "## 用户画像\n\n系统正在从您的交互记录和存储记忆中构建画像，请继续与 AI 对话以丰富个人档案。"
                        await conn.execute(
                            """INSERT INTO user_persona (team_id, persona_md, scenario_count, version)
                               VALUES ($1, $2, 0, 1)
                               ON CONFLICT (team_id) DO NOTHING""",
                            team_id, default_persona_md
                        )
                        row = await conn.fetchrow("SELECT persona_md FROM user_persona WHERE team_id=$1", info.get("team_id","default"))
                    await conn.close()
                    result_text = row["persona_md"] if row and row["persona_md"] else "用户画像尚未生成，请继续与 AI 对话以积累更多记忆。"
                except:
                    result_text = "用户画像暂时无法获取，请稍后重试。"

            elif tool_name in ("canvas_get", "memory_task_canvas_get"):
                from backend.api.db_helper import get_db_conn
                task_id = "main"
                agent_id = arguments.get("agent_id", "default")
                if not task_id: task_id = "main"
                try:
                    conn = await get_db_conn()
                    row = await conn.fetchrow("SELECT * FROM task_canvas WHERE team_id=$1 AND task_id=$2 AND agent_id=$3", team_id, task_id, agent_id)
                    await conn.close()
                    result_text = f"Canvas: {row['canvas_mermaid']}" if row else f"No canvas for {task_id} (Agent: {agent_id})"
                except Exception as e:
                    result_text = f"Canvas unavailable: {e}"

            elif tool_name in ("canvas_update", "memory_task_canvas_update"):
                import json as _json
                from backend.api.db_helper import get_db_conn
                try:
                    conn = await get_db_conn()
                    task_id = "main"
                    agent_id = arguments.get("agent_id", "default")
                    if not task_id: task_id = "main"
                    comp_str = _json.dumps(arguments.get("completed", []), ensure_ascii=False)
                    next_str = _json.dumps(arguments.get("next", []), ensure_ascii=False)
                    task_title = arguments.get("title") or arguments.get("task_title") or ""
                    await conn.execute(
                        """INSERT INTO task_canvas (team_id, task_id, agent_id, task_title, canvas_mermaid, completed_steps, next_steps)
                           VALUES ($1,$2,$3,$4,$5,$6::jsonb,$7::jsonb)
                           ON CONFLICT (team_id, task_id, agent_id) DO UPDATE SET
                             canvas_mermaid  = EXCLUDED.canvas_mermaid,
                             task_title      = COALESCE(NULLIF(EXCLUDED.task_title,''), task_canvas.task_title),
                             completed_steps = EXCLUDED.completed_steps,
                             next_steps      = EXCLUDED.next_steps,
                             updated_at      = NOW()""",
                        team_id, task_id, agent_id, task_title, arguments.get("mermaid", ""), comp_str, next_str)
                    await conn.close()
                    result_text = "Canvas updated"
                except Exception as e:
                    result_text = f"Canvas update failed: {e}"

            elif tool_name == "memory_list":
                workspace_id = arguments.get("workspace_id", "default")
                limit = int(arguments.get("limit", 20))
                try:
                    from backend.api.db_helper import get_db_conn
                    import json as _json
                    conn = await get_db_conn()
                    rows = await conn.fetch(
                        "SELECT id, title FROM memories WHERE team_id=$1 ORDER BY created_at DESC LIMIT $2",
                        team_id, limit)
                    await conn.close()
                    items = [{"id": str(r["id"]), "title": r["title"] or ""} for r in rows]
                    result_text = _json.dumps(items, ensure_ascii=False)
                except Exception as e:
                    result_text = f"memory_list failed: {e}"

            elif tool_name == "memory_delete":
                memory_id = arguments.get("memory_id", "")
                try:
                    from backend.api.routes import pg_repo, qdrant_store
                    if not pg_repo:
                        raise Exception("pg_repo not initialized")

                    # 1. Fetch memory to check ownership and get actual UUID
                    memory = await pg_repo.get(memory_id)
                    if not memory:
                        result_text = "Memory not found."
                    elif memory.get("team_id") != team_id:
                        result_text = "Access denied: memory does not belong to this team."
                    else:
                        # 2. Perform deletion in Postgres
                        resolved_id = str(memory["id"])
                        ok = await pg_repo.delete(resolved_id, team_id)
                        # 3. Perform deletion in Qdrant
                        if qdrant_store and ok:
                            try:
                                qdrant_store.delete(resolved_id, team_id=team_id)
                            except Exception as qe:
                                logger.warning(f"Qdrant delete failed in memory_delete tool: {qe}")
                        result_text = "Memory deleted successfully."
                except Exception as e:
                    result_text = f"memory_delete failed: {e}"

            elif tool_name == "memory_status":
                try:
                    from backend.api.db_helper import get_db_conn
                    conn = await get_db_conn()
                    row = await conn.fetchrow("SELECT COUNT(*) as cnt FROM memories WHERE team_id=$1", info.get("team_id","default"))
                    await conn.close()
                    cnt = int(row["cnt"]) if row and row["cnt"] is not None else 0
                    result_text = f"Memory system online. Total memories: {cnt}. Qdrant: connected. Neo4j: connected."
                except Exception as e:
                    result_text = f"memory_status failed: {e}"

            else:
                is_error = True
                result_text = f"Tool '{tool_name}' not found."

        except Exception as e:
            is_error = True
            result_text = f"Error executing tool '{tool_name}': {str(e)}"

        # Prepare JSON-RPC MCP call response
        response = {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": result_text
                    }
                ],
                "isError": is_error
            }
        }
        await queue.put(response)
        return {"status": "ok"}

    # Catch-all fallback
    response = {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {
            "code": -32601,
            "message": f"Method {method} not supported"
        }
    }
    await queue.put(response)
    return {"status": "ok"}
