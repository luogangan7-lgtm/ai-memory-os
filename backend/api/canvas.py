"""Task Canvas API - simplified, task_id always 'main'."""
from fastapi import APIRouter, Depends, HTTPException
from backend.auth.middleware import get_current_team
from backend.api.db_helper import get_db_conn

router = APIRouter(prefix="/canvas", tags=["canvas"])

@router.get("")
async def get_canvas(team_id: str = Depends(get_current_team)):
    """Get all agent canvases for team (task_id always 'main')."""
    conn = await get_db_conn()
    try:
        rows = await conn.fetch(
            "SELECT * FROM task_canvas WHERE team_id=$1 AND task_id='main' ORDER BY updated_at DESC",
            team_id)
        return [dict(r) for r in rows]
    finally: await conn.close()

@router.post("")
async def update_canvas(data: dict, team_id: str = Depends(get_current_team)):
    """Update canvas for an agent (task_id always 'main')."""
    conn = await get_db_conn()
    import json as _json
    try:
        completed = data.get("completed", [])
        next_steps = data.get("next", [])
        agent_id = data.get("agent_id", "default")
        comp_str = _json.dumps(completed, ensure_ascii=False)
        next_str = _json.dumps(next_steps, ensure_ascii=False)
        await conn.execute(
            """INSERT INTO task_canvas (team_id, task_id, agent_id, task_title, canvas_mermaid, completed_steps, next_steps)
               VALUES ($1,'main',$2,$3,$4,$5::jsonb,$6::jsonb)
               ON CONFLICT (team_id, task_id, agent_id) DO UPDATE SET
                 canvas_mermaid  = EXCLUDED.canvas_mermaid,
                 task_title      = COALESCE(NULLIF(EXCLUDED.task_title,''), task_canvas.task_title),
                 completed_steps = EXCLUDED.completed_steps,
                 next_steps      = EXCLUDED.next_steps,
                 updated_at      = NOW()""",
            team_id, agent_id, data.get("title", ""), data.get("mermaid", ""), comp_str, next_str)
        return {"status": "updated", "agent_id": agent_id}
    finally: await conn.close()
