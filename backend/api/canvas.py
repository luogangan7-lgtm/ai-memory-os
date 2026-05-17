"""Task Canvas API - Mermaid-based short-term task state visualization."""
from fastapi import APIRouter, Depends, HTTPException
from backend.auth.middleware import get_current_team
import asyncpg, os

router = APIRouter(prefix="/canvas", tags=["canvas"])
DATABASE_URL = os.getenv("DATABASE_URL", "")

async def get_conn(): return await asyncpg.connect(DATABASE_URL)

@router.get("/{task_id}")
async def get_canvas(task_id: str, team_id: str = Depends(get_current_team)):
    conn = await get_conn()
    try:
        row = await conn.fetchrow(
            "SELECT * FROM task_canvas WHERE team_id=$1 AND task_id=$2", team_id, task_id)
        if not row: raise HTTPException(404, "Task not found")
        return dict(row)
    finally: await conn.close()

@router.post("/{task_id}")
async def update_canvas(task_id: str, data: dict, team_id: str = Depends(get_current_team)):
    conn = await get_conn()
    try:
        await conn.execute(
            """INSERT INTO task_canvas (team_id, task_id, task_title, canvas_mermaid, completed_steps, next_steps)
               VALUES ($1,$2,$3,$4,$5,$6)
               ON CONFLICT (team_id, task_id) DO UPDATE SET canvas_mermaid=$4, completed_steps=$5, next_steps=$6, updated_at=NOW()""",
            team_id, task_id, data.get("title",""), data.get("mermaid",""), data.get("completed",[]), data.get("next",[]))
        return {"status": "updated", "task_id": task_id}
    finally: await conn.close()
