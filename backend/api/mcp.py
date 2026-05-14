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
# Maps connection_id -> asyncio.Queue for sending events to client
connections: Dict[str, asyncio.Queue] = {}


# --- Core MCP Specification Endpoints ---

@router.get("")
async def mcp_get_handler(request: Request):
    """Establishes the SSE Stream channel for the MCP client."""
    connection_id = str(uuid.uuid4())
    queue = asyncio.Queue()
    connections[connection_id] = queue

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

    payload = await request.json()
    req_id = payload.get("id")
    method = payload.get("method")
    params = payload.get("params", {})

    logger.info(f"Received MCP Request - ID: {req_id}, Method: {method}")

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
        await connections[connection_id].put(response)
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
                    }
                ]
            }
        }
        await connections[connection_id].put(response)
        return {"status": "ok"}

    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        # Import core modules dynamically to avoid circular dependencies
        from backend.api.routes import pg_repo, retrieval, registry
        team_id = "default"  # Default single tenant key, extensible to JWT multi-tenant

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
                    # Execute hybrid search
                    raw_results = await retrieval.search(
                        query=query,
                        embedding_fn=registry.embed_single,
                        team_id=team_id,
                        workspace_id=workspace_id,
                        top_k=top_k,
                        use_graph=True
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
        await connections[connection_id].put(response)
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
    await connections[connection_id].put(response)
    return {"status": "ok"}
