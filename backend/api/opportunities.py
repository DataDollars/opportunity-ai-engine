import logging
from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from backend.database.firebase import get_db

logger = logging.getLogger(__name__)

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

@router.get("/search")
async def search_opportunities(
    query: str = Query(..., description="Semantic search query"),
    limit: int = Query(10, description="Max number of ranked results to return")
):
    """
    Performs semantic search on government opportunities using cosine similarity
    on Hugging Face sentence embeddings.
    """
    if not query.strip():
        return []
        
    db = get_db()
    opps_ref = db.collection("opportunities")
    
    try:
        # 1. Fetch query embedding
        from backend.ai.embeddings import get_embedding, compute_cosine_similarity
        query_embedding = await get_embedding(query)
        
        # 2. Stream all opportunities
        docs = opps_ref.stream()
        results = []
        
        for doc in docs:
            opp = doc.to_dict()
            opp["id"] = doc.id
            
            # Get opportunity embedding
            opp_embedding = opp.get("embedding")
            
            # If opportunity doesn't have an embedding, compute it on the fly and update doc!
            if not opp_embedding or not isinstance(opp_embedding, list) or len(opp_embedding) != 384:
                embed_text = f"{opp.get('name', '')} {opp.get('description', '')} {opp.get('benefits', '')}".strip()
                opp_embedding = await get_embedding(embed_text)
                opp["embedding"] = opp_embedding
                try:
                    opps_ref.document(doc.id).update({"embedding": opp_embedding})
                except Exception as ex:
                    logger.warning(f"Failed to update missing embedding for {doc.id}: {ex}")
                    
            similarity = compute_cosine_similarity(query_embedding, opp_embedding)
            opp["similarity_score"] = float(similarity)
            results.append(opp)
            
        # 3. Sort by similarity score descending
        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        return results[:limit]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Semantic search failed: {e}")

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
