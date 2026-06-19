import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from google.genai import types
from backend.ai.scheme_parser import get_gemini_client
from backend.config import settings

logger = logging.getLogger(__name__)

class CompanyProfile(BaseModel):
    company_name: str
    industry: str
    state: str
    employees: int
    turnover: float  # Turnover in Rupees or base currency
    business_type: str = "MSME"  # MSME, Startup, Partnership, etc.
    country: str = "India"

class MatchDetail(BaseModel):
    score: int = Field(description="Match eligibility score from 0 to 100")
    reason: str = Field(description="Brief justification of why this company matches or qualifies")
    missing_requirements: List[str] = Field(default=[], description="List of documents or requirements the company might be missing")

def run_local_match_heuristics(company: CompanyProfile, opp: Dict[str, Any]) -> MatchDetail:
    """
    Heuristics-based scoring for local running/mock fallback.
    """
    score = 50  # Base score
    reason_parts = []
    missing = []
    
    # State check
    opp_state = opp.get("state")
    if opp_state:
        if opp_state.lower() == company.state.lower():
            score += 20
            reason_parts.append(f"Target state matches company location ({company.state}).")
        else:
            score -= 30
            reason_parts.append(f"Scheme is specific to {opp_state} but company is in {company.state}.")
    else:
        score += 15
        reason_parts.append("Scheme applies nationally.")

    # Industry check
    opp_industries = opp.get("industry") or opp.get("industries") or []
    opp_ind_lower = [ind.lower() for ind in opp_industries]
    if "all" in opp_ind_lower or not opp_industries:
        score += 15
        reason_parts.append("Scheme is open to all industries.")
    elif company.industry.lower() in opp_ind_lower:
        score += 25
        reason_parts.append(f"Industry matches company's sector ({company.industry}).")
    else:
        # Check substring match
        matched = False
        for ind in opp_ind_lower:
            if ind in company.industry.lower() or company.industry.lower() in ind:
                score += 20
                reason_parts.append(f"Industry partially matches sector ({ind}).")
                matched = True
                break
        if not matched:
            score -= 20
            reason_parts.append(f"Scheme is targeted for {', '.join(opp_industries)} instead of {company.industry}.")
            missing.append(f"Company is not in the required industry sectors: {', '.join(opp_industries)}")

    # Target users/business type
    opp_users = opp.get("target_users") or []
    opp_users_lower = [u.lower() for u in opp_users]
    if company.business_type.lower() in opp_users_lower:
        score += 10
        reason_parts.append(f"Target users matches business profile ({company.business_type}).")
    elif "all" in opp_users_lower or not opp_users:
        score += 5
    else:
        missing.append(f"Requires registered status as: {', '.join(opp_users)}")

    # Clamp score
    score = max(0, min(100, score))
    
    # Generate missing docs
    opp_docs = opp.get("documents_required") or opp.get("documents") or []
    if opp_docs:
        missing.extend(opp_docs[:2])
        
    reason = " ".join(reason_parts)
    if score >= 75:
        reason = f"Excellent Match! {reason}"
    elif score >= 50:
        reason = f"Potential Match. {reason}"
    else:
        reason = f"Low Compatibility. {reason}"

    return MatchDetail(score=score, reason=reason, missing_requirements=missing)

async def match_opportunity(company: CompanyProfile, opp: Dict[str, Any]) -> MatchDetail:
    """
    Matches a single opportunity with a company profile.
    Uses Gemini structured output or falls back to rules if Gemini is unavailable.
    """
    client = get_gemini_client()
    if not client:
        return run_local_match_heuristics(company, opp)

    try:
        prompt = f"""
        Evaluate if the following company matches the requirements of the government scheme/opportunity.
        
        Company Profile:
        - Name: {company.company_name}
        - Location: {company.state}, {company.country}
        - Industry: {company.industry}
        - Employees: {company.employees}
        - Turnover: {company.turnover}
        - Business Type: {company.business_type}

        Opportunity Details:
        - Name: {opp.get('name') or opp.get('scheme_name')}
        - Description: {opp.get('description')}
        - Target State/Location: {opp.get('state')}
        - Target Industries: {opp.get('industry') or opp.get('industries')}
        - Eligibility Criteria: {opp.get('eligibility')}
        - Benefits: {opp.get('benefits')}
        - Documents Required: {opp.get('documents') or opp.get('documents_required')}
        """

        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=MatchDetail,
                system_instruction=(
                    "You are a professional business opportunity matching engine. Evaluate the eligibility percentage (0 to 100), "
                    "provide a concise justification matching their specific profile to the scheme, and list missing documents or requirements."
                ),
                temperature=0.2
            )
        )
        
        if response.parsed:
            return response.parsed
        else:
            return run_local_match_heuristics(company, opp)

    except Exception as e:
        logger.error(f"Gemini matching failed: {e}. Running heuristics fallback.")
        return run_local_match_heuristics(company, opp)

def filter_opportunities_stage1(company: CompanyProfile, opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Stage 1: Fast rule-based filtering.
    Checks location match, basic industry filter, and active status.
    """
    filtered = []
    for opp in opportunities:
        # Check active status
        if opp.get("active_status") == "inactive":
            continue
            
        # 1. Location match
        opp_state = opp.get("state")
        if opp_state and opp_state.lower() not in ["national", "all", "india"]:
            # If scheme is state specific, company state must match
            if opp_state.lower() != company.state.lower():
                continue

        # 2. Basic Industry match (if scheme has specific industries)
        opp_industries = opp.get("industry") or opp.get("industries") or []
        opp_ind_lower = [ind.lower() for ind in opp_industries]
        
        if opp_industries and "all" not in opp_ind_lower:
            # Check if company industry matches any of the scheme's industries
            # Simple substring match to be broad
            matched = False
            for ind in opp_ind_lower:
                if ind in company.industry.lower() or company.industry.lower() in ind:
                    matched = True
                    break
            if not matched:
                continue

        filtered.append(opp)
    
    return filtered
