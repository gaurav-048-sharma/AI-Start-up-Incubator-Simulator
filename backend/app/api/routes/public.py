from fastapi import APIRouter, HTTPException
from app.models.database import get_db_service, get_db_connection

router = APIRouter()

@router.get("/ideas/{slug}")
async def get_public_idea(slug: str):
    """Get a public idea and its reports by slug."""
    db = get_db_service()
    
    async with get_db_connection() as conn:
        async with conn.execute("SELECT * FROM ideas WHERE public_slug = ? AND is_public = 1", (slug,)) as cursor:
            idea = await cursor.fetchone()
            
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found or not public")
        
    idea_id = idea["id"]
    reports = await db.get_idea_reports(idea_id)
    
    safe_idea = dict(idea)
    safe_idea.pop("user_id", None)
    safe_idea.pop("organization_id", None)
    
    safe_reports = [dict(r) for r in reports if r.get("status") == "completed"]
    
    return {
        "idea": safe_idea,
        "reports": safe_reports
    }
