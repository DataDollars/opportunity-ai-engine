import logging
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from backend.database.firebase import get_db
from backend.ai.matcher import CompanyProfile, match_opportunity, filter_opportunities_stage1

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/match", tags=["Matching Engine"])

@router.post("")
async def match_company_profile(
    profile: CompanyProfile,
    limit: Optional[int] = Query(10, description="Max number of candidate schemes to run Gemini scoring on")
):
    """
    Ranks schemes for a given company profile using the two-stage matching engine.
    """
    db = get_db()
    
    # 1. Fetch opportunities
    try:
        opps_docs = db.collection("opportunities").stream()
        all_opps = []
        for doc in opps_docs:
            data = doc.to_dict()
            data["id"] = doc.id
            all_opps.append(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch opportunities from DB: {e}")

    # 2. Stage 1: Fast filtering (Location/State, Category, basic industry matches)
    stage1_candidates = filter_opportunities_stage1(profile, all_opps)
    
    # 3. Stage 2: Deep evaluation (Gemini scoring or local heuristics if Gemini is unavailable)
    matched_results = []
    
    # Limit number of opportunities evaluated by Gemini to avoid overloading and rate limits
    evaluated_candidates = stage1_candidates[:limit]
    
    for opp in evaluated_candidates:
        try:
            # Perform single opportunity evaluation
            match_res = await match_opportunity(profile, opp)
            
            result_item = {
                "opportunity_id": opp["id"],
                "opportunity_name": opp.get("name") or opp.get("scheme_name"),
                "category": opp.get("category"),
                "state": opp.get("state"),
                "benefits": opp.get("benefits"),
                "documents": opp.get("documents") or opp.get("documents_required"),
                "apply_url": opp.get("apply_url"),
                "match_score": match_res.score,
                "match_reason": match_res.reason,
                "missing_requirements": match_res.missing_requirements
            }
            matched_results.append(result_item)
        except Exception as e:
            # Log single match error but do not fail entire request
            logger.error(f"Error matching opportunity {opp.get('id')}: {e}")

    # Sort results by score (descending)
    matched_results.sort(key=lambda x: x["match_score"], reverse=True)
    
    # Write company profile & matches to database if not in dry-run mode (future analytics)
    try:
        # Save company profile
        comp_ref = db.collection("companies").document()
        comp_ref.set(profile.model_dump())
        
        # Save match records
        for res in matched_results:
            match_ref = db.collection("matches").document()
            match_ref.set({
                "company_id": comp_ref.id,
                "opportunity_id": res["opportunity_id"],
                "match_score": res["match_score"],
                "match_reason": res["match_reason"],
                "missing_requirements": res["missing_requirements"],
                "matched_at": res.get("matched_at") or None
            })
    except Exception as e:
        # DB write failure is logged but doesn't block response
        logger.warning(f"Could not log matches to Firestore analytics: {e}")

    return {
        "company_profile": profile,
        "total_candidates_found": len(stage1_candidates),
        "total_evaluated": len(matched_results),
        "matches": matched_results
    }
