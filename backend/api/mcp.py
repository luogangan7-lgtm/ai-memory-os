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
    queue: asyncio.Queue = asyncio.Queue()

    
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


async def index_project_bg(project_path: str, team_id: str):
    import os
    import uuid
    from backend.memory.code_parser import parse_file
    from backend.api.routes import pg_repo, graph_store
    if not pg_repo:
        return
    try:
        abs_path = os.path.abspath(project_path)
        if not os.path.exists(abs_path):
            logger.warning(f"Project path does not exist: {abs_path}")
            return
            
        file_count = 0
        entity_count = 0
        
        # Walk directory
        for root, dirs, files in os.walk(abs_path):
            # Ignore common ignore-folders
            if any(ignored in root for ignored in (".venv", "node_modules", ".git", "__pycache__", "build", "dist")):
                continue
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in (".py", ".js", ".ts", ".tsx"):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                        entities = parse_file(file_path, content)
                        
                        async with pg_repo.pool.acquire() as conn:
                            for ent in entities:
                                entity_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{team_id}:{file_path}:{ent['qualified_name']}"))
                                lang = "python" if ext == ".py" else ("typescript" if "ts" in ext else "javascript")
                                
                                # Insert or update in Postgres
                                await conn.execute("""
                                    INSERT INTO code_entities (id, team_id, project_path, entity_type, name, qualified_name, file_path, language, description, signature, start_line, end_line, indexed_at)
                                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW())
                                    ON CONFLICT (id) DO UPDATE
                                    SET team_id = EXCLUDED.team_id,
                                        project_path = EXCLUDED.project_path,
                                        entity_type = EXCLUDED.entity_type,
                                        name = EXCLUDED.name,
                                        qualified_name = EXCLUDED.qualified_name,
                                        file_path = EXCLUDED.file_path,
                                        language = EXCLUDED.language,
                                        description = EXCLUDED.description,
                                        signature = EXCLUDED.signature,
                                        start_line = EXCLUDED.start_line,
                                        end_line = EXCLUDED.end_line,
                                        indexed_at = NOW()
                                """, entity_id, team_id, abs_path, ent["entity_type"], ent["name"], ent["qualified_name"], file_path, lang, ent["description"], ent["signature"], ent["start_line"], ent["end_line"])
                                
                                # Ingest in Neo4j
                                if graph_store:
                                    await graph_store.ingest_code_entity(entity_id, ent["name"], ent["entity_type"], file_path, team_id)
                                
                                entity_count += 1
                        file_count += 1
                        if file_count >= 100:  # limit to 100 files for safety
                            break
                    except Exception as fe:
                        logger.warning(f"Failed to parse file {file_path}: {fe}")
            if file_count >= 100:
                break
        logger.info(f"Background indexing completed for {project_path}: {file_count} files, {entity_count} entities.")
    except Exception as e:
        logger.error(f"Background indexing error: {e}")


@router.post("")
async def mcp_post_handler(
    request: Request,
    connection_id: Optional[str] = None
):
    """Receives JSON-RPC requests from client and routes tool calling logic."""
    if not connection_id or connection_id not in connections:
        raise HTTPException(status_code=400, detail="Invalid or missing connection_id")

    conn_info = connections[connection_id]
    queue = conn_info["queue"]
    team_id = conn_info["team_id"]
    agent_id = conn_info["agent_id"]

    payload = await request.json()
    req_id = payload.get("id")
    method = payload.get("method")
    params = payload.get("params", {})

    logger.info(f"Received MCP Request - ID: {req_id}, Method: {method}, User: {conn_info['username']}")


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
                        "description": "Semantic search across all memory layers. Supports time range (since/until), layer filter (L1-L4), and source type filter.",
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
                                },
                                "limit": {
                                    "type": "integer",
                                    "description": "Max results",
                                    "default": 5
                                },
                                "since": {
                                    "type": "string",
                                    "description": "Start date ISO format, e.g. 2026-03-01"
                                },
                                "until": {
                                    "type": "string",
                                    "description": "End date ISO format, e.g. 2026-04-30"
                                },
                                "layer": {
                                    "type": "string",
                                    "enum": ["L1", "L2", "L3", "L4"],
                                    "description": "Memory layer filter"
                                },
                                "source_type": {
                                    "type": "string",
                                    "description": "Source filter: human/agent/document"
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
                        "name": "code_search",
                        "description": "Search indexed code entities by function/class name.",
                        "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 10}}, "required": ["query"]}
                    },
                    {
                        "name": "code_relations",
                        "description": "Query code entity relationships (calls/inherits).",
                        "inputSchema": {"type": "object", "properties": {"entity_name": {"type": "string"}}, "required": ["entity_name"]}
                    },
                    {
                        "name": "code_index",
                        "description": "Index a code project into the knowledge graph.",
                        "inputSchema": {"type": "object", "properties": {"project_path": {"type": "string"}}, "required": ["project_path"]}
                    },
                    {
                        "name": "code_impact",
                        "description": "Analyze change impact for a code entity.",
                        "inputSchema": {"type": "object", "properties": {"entity_name": {"type": "string"}}, "required": ["entity_name"]}
                    },
                    {
                        "name": "code_memory_link",
                        "description": "Link a code entity to a memory entry.",
                        "inputSchema": {"type": "object", "properties": {"entity_name": {"type": "string"}, "memory_id": {"type": "string"}}, "required": ["entity_name", "memory_id"]}
                    },
                    {
                        "name": "memory_feedback",
                        "description": "Report task outcome to improve skill quality.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "skill_id": {"type": "string", "description": "UUID of the memory skill to update"},
                                "outcome": {"type": "string", "enum": ["success", "failure", "partial"], "description": "Task execution result"},
                                "memory_ids": {"type": "array", "items": {"type": "string"}, "description": "Optional list of memories read/written"},
                                "context": {"type": "string", "description": "Optional text explanation or error traceback"}
                            },
                            "required": ["skill_id", "outcome"]
                        }
                    },

                    {
                        "name": "doc_search", "description": "Search uploaded documents.", "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 5}}, "required": ["query"]}},
                    {"name": "memory_skill_list",
                        "description": "List high-quality crystallized skills from L4 pipeline.",
                        "inputSchema": {"type": "object", "properties": {"min_effectiveness": {"type": "number", "default": 0.6}, "limit": {"type": "integer", "default": 10}}}
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
                    row = await conn.fetchrow("SELECT persona_md FROM user_persona WHERE team_id=$1", team_id)
                    if not row or not row["persona_md"]:
                        default_persona_md = "## 用户画像\n\n系统正在从您的交互记录和存储记忆中构建画像，请继续与 AI 对话以丰富个人档案。"
                        await conn.execute(
                            """INSERT INTO user_persona (team_id, persona_md, scenario_count, version)
                               VALUES ($1, $2, 0, 1)
                               ON CONFLICT (team_id) DO NOTHING""",
                            team_id, default_persona_md
                        )
                        row = await conn.fetchrow("SELECT persona_md FROM user_persona WHERE team_id=$1", team_id)
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
                    row = await conn.fetchrow("SELECT COUNT(*) as cnt FROM memories WHERE team_id=$1", team_id)
                    await conn.close()
                    cnt = int(row["cnt"]) if row and row["cnt"] is not None else 0
                    result_text = f"Memory system online. Total memories: {cnt}. Qdrant: connected. Neo4j: connected."
                except Exception as e:
                    result_text = f"memory_status failed: {e}"


            elif tool_name == "code_search":
                try:
                    query = arguments.get("query", "")
                    limit = arguments.get("limit", 10)
                    from backend.api.db_helper import get_db_conn
                    conn = await get_db_conn()
                    rows = await conn.fetch("SELECT name, entity_type, file_path, language, description FROM code_entities WHERE team_id=$1 AND (name ILIKE $2 OR description ILIKE $2) LIMIT $3", team_id, f"%{query}%", limit)
                    await conn.close()
                    if rows:
                        result_text = "\n".join(f"[{r['entity_type']}] {r['name']} ({r['language'] or '?'}) @ {r['file_path'] or '?'}" for r in rows)
                    else:
                        result_text = f"No code entities found. Index a project first."
                except Exception as e:
                    result_text = f"code_search failed: {e}"

            elif tool_name == "code_relations":
                try:
                    entity_name = arguments.get("entity_name", "")
                    from backend.graph.neo4j_store import GraphStore
                    from backend.services.config import settings
                    gs = GraphStore(uri=settings.neo4j_uri, user=settings.neo4j_user, password=settings.neo4j_password)
                    async with gs.driver.session() as session:
                        r = await session.run("MATCH (a:CodeEntity {name: $name})-[rel]->(b:CodeEntity) RETURN a.name as src, type(rel) as rel, b.name as dst", name=entity_name)
                        data = await r.data()
                    if data:
                        result_text = "\n".join(f"{d['src']} --[{d['rel']}]--> {d['dst']}" for d in data)
                    else:
                        result_text = f"No relations found for '{entity_name}'"
                except Exception as e:
                    result_text = f"code_relations failed: {e}"


            elif tool_name == "code_index":
                try:
                    project_path = arguments.get("project_path", "")
                    asyncio.create_task(index_project_bg(project_path, team_id))
                    result_text = f"Code indexing queued for {project_path}. Parsing starts asynchronously."
                except Exception as e:
                    result_text = f"code_index failed: {e}"

            elif tool_name == "code_impact":
                try:
                    entity_name = arguments.get("entity_name", "")
                    from backend.graph.neo4j_store import GraphStore
                    from backend.services.config import settings
                    gs = GraphStore(uri=settings.neo4j_uri, user=settings.neo4j_user, password=settings.neo4j_password)
                    async with gs.driver.session() as session:
                        r = await session.run("""
                            MATCH (dep)-[rel]->(tar:Code {name: $name})
                            RETURN dep.name as name, dep.entity_type as type, type(rel) as rel_type
                            LIMIT 20
                        """, name=entity_name)
                        data = await r.data()
                    await gs.close()
                    if data:
                        result_text = f"Impact analysis for '{entity_name}' (dependent elements):\n" + "\n".join(
                            f"- [{d['type'] or 'Code'}] {d['name']} --[{d['rel_type']}]--> {entity_name}" for d in data
                        )
                    else:
                        result_text = f"No direct dependencies found for '{entity_name}' in the Neo4j graph."
                except Exception as e:
                    result_text = f"code_impact failed: {e}"

            elif tool_name == "code_memory_link":
                try:
                    entity_name = arguments.get("entity_name", "")
                    memory_id = arguments.get("memory_id", "")
                    from backend.api.db_helper import get_db_conn
                    from backend.graph.neo4j_store import GraphStore
                    from backend.services.config import settings
                    conn = await get_db_conn()
                    row = await conn.fetchrow("SELECT id FROM code_entities WHERE team_id=$1 AND name=$2 LIMIT 1", team_id, entity_name)
                    await conn.close()
                    if row:
                        ent_id = str(row["id"])
                        gs = GraphStore(uri=settings.neo4j_uri, user=settings.neo4j_user, password=settings.neo4j_password)
                        await gs.create_memory_node(memory_id, "", "", "")
                        await gs.create_code_relation(memory_id, ent_id, "RELATES_TO_CODE")
                        await gs.close()
                        result_text = f"Linked memory {memory_id[:8]} to code entity {entity_name} ({ent_id[:8]})"
                    else:
                        result_text = f"Code entity '{entity_name}' not found in database. Please index the project first."
                except Exception as e:
                    result_text = f"code_memory_link failed: {e}"

            elif tool_name == "memory_feedback":
                try:
                    outcome = arguments.get("outcome", "success")
                    skill_id = arguments.get("skill_id")
                    memory_ids = arguments.get("memory_ids", [])
                    context = arguments.get("context", "")
                    
                    from backend.pipeline.skill_evolver import update_skill_effectiveness
                    from backend.api.routes import pg_repo
                    if pg_repo and skill_id:
                        res = await update_skill_effectiveness(
                            pg_repo.pool,
                            skill_id=skill_id,
                            outcome=outcome,
                            agent_id=agent_id,
                            team_id=team_id,
                            memory_ids=memory_ids,
                            context=context
                        )
                        result_text = f"Feedback recorded: {outcome}. Updated effectiveness: {res['effectiveness']:.2%}"
                    else:
                        result_text = f"Failed to record feedback. Verify that pg_repo is initialized and skill_id '{skill_id}' is provided."
                except Exception as e:
                    result_text = f"memory_feedback failed: {e}"

            elif tool_name == "doc_search":
                try:
                    query = arguments.get("query", "")
                    limit = int(arguments.get("limit", 5))
                    if not query:
                        result_text = "Please provide a query."
                    elif retrieval and registry:
                        use_rerank = hasattr(registry, "reranker") and registry.reranker is not None
                        raw_results = await retrieval.search(
                            query=query,
                            embedding_fn=registry.embed_single,
                            team_id=team_id,
                            workspace_id="default",
                            top_k=limit,
                            use_rerank=use_rerank,
                            rerank_fn=registry.rerank if use_rerank else None,
                            source_type_filter="document",
                        )
                        if raw_results:
                            from backend.services.context_compiler import ContextCompiler
                            result_text = ContextCompiler.compile_context(raw_results, query)
                        else:
                            from backend.api.db_helper import get_db_conn
                            conn = await get_db_conn()
                            rows = await conn.fetch(
                                "SELECT title, content FROM memories WHERE team_id=$1 AND source_type='document' AND content ILIKE $2 LIMIT $3",
                                team_id, "%" + query + "%", limit
                            )
                            await conn.close()
                            if rows:
                                result_text = "\n\n---\n\n".join(f"📄 {r['title']}\n{r['content'][:500]}" for r in rows)
                            else:
                                result_text = "No document content found matching query."
                    else:
                        result_text = "Retrieval engine not initialized."
                except Exception as e:
                    result_text = f"doc_search failed: {e}"

            elif tool_name == "memory_skill_list":
                try:
                    min_eff = arguments.get("min_effectiveness", 0.6)
                    limit = arguments.get("limit", 10)
                    from backend.api.db_helper import get_db_conn
                    conn = await get_db_conn()
                    rows = await conn.fetch("""
                        SELECT id, skill_name, trigger_pattern, effectiveness, usage_count, evolved_count, source_agents, verified_by
                        FROM memory_skills
                        WHERE team_id=$1 AND effectiveness >= $2
                        ORDER BY effectiveness DESC
                        LIMIT $3
                    """, team_id, min_eff, limit)
                    await conn.close()
                    if rows:
                        result_text = "\n".join(
                            f"💎 {r['skill_name']} [ID: {r['id']}] (eff={r['effectiveness']:.0%}, used {r['usage_count']}x, evolved {r['evolved_count']}x)\n"
                            f"  Trigger: {r['trigger_pattern'] or 'general'}\n"
                            f"  Agents: {', '.join(r['source_agents']) if r['source_agents'] else 'none'}"
                            for r in rows
                        )
                    else:
                        result_text = "No crystallized skills found matching requirements."
                except Exception as e:
                    result_text = f"memory_skill_list failed: {e}"

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
