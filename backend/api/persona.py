"""User Persona API - read L3 user profiles."""
from fastapi import APIRouter, Depends, HTTPException
from backend.auth.middleware import get_current_team
import asyncpg, os

router = APIRouter(prefix="/persona", tags=["persona"])
DATABASE_URL = os.getenv("DATABASE_URL", "")

async def get_conn(): return await asyncpg.connect(DATABASE_URL)

@router.get("/{team_id}")
async def get_persona(team_id: str, _: str = Depends(get_current_team)):
    conn = await get_conn()
    try:
        row = await conn.fetchrow(
            "SELECT * FROM user_persona WHERE team_id=$1", team_id)
        if not row: raise HTTPException(404, "No persona yet")
        return dict(row)
    finally: await conn.close()
