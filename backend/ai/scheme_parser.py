import logging
import hashlib
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from backend.config import settings

logger = logging.getLogger(__name__)

class SchemeExtraction(BaseModel):
    scheme_name: str = Field(description="Official name of the scheme/grant/subsidy")
    description: str = Field(description="Detailed description of what the scheme is and its objectives")
    country: str = Field(description="Country where this scheme applies")
    state: Optional[str] = Field(default=None, description="Specific state where this scheme applies, or null if it applies nationally")
    ministry: Optional[str] = Field(default=None, description="Ministry, department or organization offering the scheme")
    target_users: Optional[List[str]] = Field(default=None, description="Type of target audience: e.g. MSME, Startup, Women Entrepreneurs, Farmers, Exporters")
    industries: Optional[List[str]] = Field(default=None, description="Specific industries targeted: e.g. Food Processing, Textile, Tech, Manufacturing, Agriculture, or ['All']")
    business_stage: Optional[List[str]] = Field(default=None, description="Eligible stages: e.g. Ideation, Validation, Scaling, Estabilished, or ['All']")
    eligibility: Optional[str] = Field(default=None, description="Clear description of the eligibility criteria")
    benefits: Optional[str] = Field(default=None, description="Details of the financial/non-financial benefits, subsidies or grants available")
    financial_amount: Optional[str] = Field(default=None, description="Amount/Percentage of funding/subsidy/loan available, e.g. '15% upfront capital subsidy up to 15 Lakhs'")
    documents_required: Optional[List[str]] = Field(default=None, description="List of required documents for application")
    application_process: Optional[str] = Field(default=None, description="Steps to apply for the scheme")
    deadline: Optional[str] = Field(default=None, description="Application deadline date or info (e.g. 'FY end 2026', 'Rolling')")
    official_link: Optional[str] = Field(default=None, description="Official application or detail URL")
    tags: Optional[List[str]] = Field(default=None, description="Relevent search keywords or categories")

def generate_opportunity_hash(scheme_name: str, source_id: str, ministry: Optional[str]) -> str:
    """
    Generates a deterministic unique hash using: scheme_name + source + ministry.
    """
    cleaned_name = "".join(scheme_name.lower().split())
    cleaned_source = "".join(source_id.lower().split())
    cleaned_ministry = "".join((ministry or "").lower().split())
    
    combined = f"{cleaned_name}:{cleaned_source}:{cleaned_ministry}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()

def get_gemini_client() -> Optional[genai.Client]:
    if not settings.GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY is not configured. AI extraction will run in Mock Mode.")
        return None
    try:
        return genai.Client(api_key=settings.GEMINI_API_KEY)
    except Exception as e:
        logger.error(f"Failed to initialize Gemini Client: {e}")
        return None

async def parse_scheme_text(raw_text: str, source_id: str, default_url: str = None) -> SchemeExtraction:
    """
    Sends raw scraped text to Gemini to extract a structured SchemeExtraction model.
    Falls back to heuristics-based mock extraction if Gemini API is unavailable.
    """
    client = get_gemini_client()
    if client:
        try:
            logger.info(f"Extracting scheme using Gemini model {settings.GEMINI_MODEL}...")
            
            prompt = f"""
            Analyze the following scraped text and extract all details related to a government scheme, subsidy, grant, or business opportunity.
            Text Content:
            {raw_text}
            """
            
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=SchemeExtraction,
                    system_instruction=(
                        "You are an expert government scheme parser. Extract structured details from raw scraped text. "
                        "Do not make up information. If a field is not mentioned or cannot be inferred, set it to null. "
                        "Clean up and structure text descriptions cleanly."
                    ),
                    temperature=0.1
                )
            )
            
            if response.parsed:
                return response.parsed
            else:
                logger.warning("Gemini did not return parsed structure. Falling back to default parser.")
        except Exception as e:
            logger.error(f"Gemini schema extraction failed: {e}. Falling back to heuristics.")

    # Fallback / Mock Parser for Sandbox Mode or API Errors
    logger.info("Executing mock/heuristics parser fallback.")
    
    # Try simple heuristic extraction from raw text
    text_lower = raw_text.lower()
    
    # Match title
    scheme_name = "Government Incentive Scheme"
    first_line = raw_text.split("\n")[0].strip()
    if len(first_line) > 5 and len(first_line) < 150:
        scheme_name = first_line

    state = None
    if "maharashtra" in text_lower:
        state = "Maharashtra"
    elif "karnataka" in text_lower:
        state = "Karnataka"
    elif "gujarat" in text_lower:
        state = "Gujarat"

    ministry = None
    if "ministry of msme" in text_lower or "msme" in text_lower:
        ministry = "Ministry of MSME"
    elif "textiles" in text_lower:
        ministry = "Ministry of Textiles"
    elif "food processing" in text_lower:
        ministry = "Ministry of Food Processing Industries"
    elif "startup india" in text_lower:
        ministry = "DPIIT, Ministry of Commerce and Industry"

    industries = ["All"]
    if "food" in text_lower:
        industries = ["Food Processing", "Agriculture"]
    elif "textile" in text_lower or "loom" in text_lower:
        industries = ["Textiles"]

    target_users = ["MSME"]
    if "startup" in text_lower:
        target_users = ["Startup"]

    return SchemeExtraction(
        scheme_name=scheme_name,
        description=f"Automated parse of opportunities from {source_id}. Raw details: {raw_text[:200]}...",
        country="India",
        state=state,
        ministry=ministry,
        target_users=target_users,
        industries=industries,
        business_stage=["All"],
        eligibility="Check raw details",
        benefits="Check raw details",
        financial_amount="See raw text",
        documents_required=["Aadhaar", "Pan Card", "Registration Proof"],
        application_process="Apply online at the official link",
        deadline="Rolling",
        official_link=default_url,
        tags=[source_id, "government", "subsidy"]
    )
