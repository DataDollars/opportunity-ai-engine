from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from backend.database.firebase import get_db

router = APIRouter(prefix="/opportunities", tags=["Opportunities"])

@router.get("")
async def get_opportunities(
    state: Optional[str] = Query(None, description="Filter by state (case-insensitive)"),
    country: Optional[str] = Query(None, description="Filter by country (case-insensitive)"),
    industry: Optional[str] = Query(None, description="Filter by industry (case-insensitive)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    active_status: Optional[str] = Query(None, description="Filter by active status ('active' or 'inactive')")
):
    """
    Retrieves and filters opportunities.
    """
    db = get_db()
    opps_ref = db.collection("opportunities")
    
    try:
        docs = opps_ref.stream()
        results = []
        
        for doc in docs:
            opp = doc.to_dict()
            opp["id"] = doc.id
            
            # Apply filters programmatically to handle array structures and flexibility
            if active_status and opp.get("active_status") != active_status:
                continue
                
            if country and opp.get("country", "").lower() != country.lower():
                continue
                
            if state:
                opp_state = opp.get("state")
                if opp_state and opp_state.lower() != state.lower():
                    continue
                    
            if category and opp.get("category") != category:
                continue
                
            if industry:
                opp_industries = opp.get("industry") or []
                opp_ind_lower = [ind.lower() for ind in opp_industries]
                # Match if "all" in list, or industry is present as substring
                if "all" not in opp_ind_lower:
                    matched = False
                    for ind in opp_ind_lower:
                        if industry.lower() in ind or ind in industry.lower():
                            matched = True
                            break
                    if not matched:
                        continue
                        
            results.append(opp)
            
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database retrieval failed: {e}")

@router.get("/{opp_id}")
async def get_opportunity_by_id(opp_id: str):
    """
    Retrieves details of a specific opportunity.
    """
    db = get_db()
    doc_ref = db.collection("opportunities").document(opp_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Opportunity not found")
        
    opp = doc.to_dict()
    opp["id"] = doc.id
    return opp
