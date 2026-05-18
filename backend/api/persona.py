"""User Persona API - read L3 user profiles."""
from fastapi import APIRouter, Depends, HTTPException
from backend.auth.middleware import get_current_team
from backend.api.db_helper import get_db_conn

router = APIRouter(prefix="/persona", tags=["persona"])

@router.get("/default")
async def get_persona_default(current_team: str = Depends(get_current_team)):
    """Get persona for the authenticated team. No path-param IDOR risk."""
    conn = await get_db_conn()
    try:
        row = await conn.fetchrow(
            "SELECT * FROM user_persona WHERE team_id=$1", current_team)
        if not row: raise HTTPException(404, "No persona yet")
        return dict(row)
    finally: await conn.close()

@router.get("/{team_id}")
async def get_persona(team_id: str, current_team: str = Depends(get_current_team)):
    """Get persona by team_id. Validates URL param matches JWT identity."""
    if team_id != current_team:
        raise HTTPException(status_code=403, detail="Access denied: unauthorized team context")
    conn = await get_db_conn()
    try:
        row = await conn.fetchrow(
            "SELECT * FROM user_persona WHERE team_id=$1", team_id)
        if not row: raise HTTPException(404, "No persona yet")
        return dict(row)
    finally: await conn.close()
