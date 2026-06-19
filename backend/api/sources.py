from fastapi import APIRouter, HTTPException, Body
from typing import List, Dict, Any
from backend.database.firebase import get_db
from backend.scheduler.daily_sync import load_sources_from_json

router = APIRouter(prefix="/sources", tags=["Sources"])

@router.get("")
async def get_sources():
    """
    List all configured opportunity source websites.
    """
    db = get_db()
    try:
        sources_ref = db.collection("sources")
        docs = sources_ref.stream()
        results = []
        for doc in docs:
            src = doc.to_dict()
            src["id"] = doc.id
            results.append(src)
            
        if not results:
            # Fallback to local config load
            return load_sources_from_json()
            
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch sources: {e}")

@router.post("")
async def create_or_update_source(
    source_id: str = Body(..., embed=True),
    name: str = Body(..., embed=True),
    url: str = Body(..., embed=True),
    country: str = Body("India", embed=True),
    category: str = Body("government_schemes", embed=True),
    method: str = Body("crawler", embed=True),
    priority: int = Body(3, embed=True),
    active: bool = Body(True, embed=True)
):
    """
    Add a new source or update an existing crawler configuration.
    """
    db = get_db()
    source_data = {
        "id": source_id,
        "name": name,
        "url": url,
        "country": country,
        "category": category,
        "method": method,
        "priority": priority,
        "active": active,
    }
    try:
        db.collection("sources").document(source_id).set(source_data, merge=True)
        return {"status": "success", "message": f"Source {source_id} successfully saved", "data": source_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write source to DB: {e}")
