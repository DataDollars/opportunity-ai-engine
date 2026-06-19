import json
import os
import time
import logging
from typing import Dict, Any, List, Optional
from backend.database.firebase import get_db
from backend.config import settings
from backend.ingestion.scrapers.myscheme_scraper import MySchemeScraper
from backend.ingestion.scrapers.data_gov_scraper import DataGovScraper
from backend.ingestion.scrapers.msme_scraper import MSMEScraper
from backend.ingestion.scrapers.startup_india_scraper import StartupIndiaScraper
from backend.ingestion.scrapers.base_scraper import BaseScraper
from backend.ai.scheme_parser import parse_scheme_text, generate_opportunity_hash

logger = logging.getLogger(__name__)

class GenericScraper(BaseScraper):
    """
    Generic crawler fallback for newly added sources.
    """
    async def scrape(self, dry_run: bool = False) -> List[Dict[str, Any]]:
        if dry_run:
            return self.get_mock_documents()
            
        logger.info(f"Using generic scraper for {self.source_id} at {self.source_url}")
        html = await self.fetch_url(self.source_url)
        if not html:
            logger.warning(f"Could not fetch {self.source_url}. Falling back to mocks.")
            return self.get_mock_documents()
            
        from backend.ingestion.extractors.html_extractor import extract_html_data
        data = extract_html_data(html, self.source_url)
        
        return [{
            "source_id": self.source_id,
            "source_url": self.source_url,
            "title": data.get("title") or f"Generic Scraped Page - {self.source_id}",
            "raw_text": data.get("raw_text") or "Empty content",
            "pdf_url": data["pdf_links"][0] if data["pdf_links"] else None,
            "content_hash": self.generate_content_hash(data.get("raw_text") or ""),
            "scraped_at": time.time()
        }]

def scraper_factory(source_id: str, source_url: str) -> BaseScraper:
    """
    Instantiates a specific scraper subclass if defined, otherwise falls back to GenericScraper.
    This makes adding new sources extremely simple.
    """
    if source_id == "myscheme":
        return MySchemeScraper()
    elif source_id == "data_gov":
        return DataGovScraper()
    elif source_id == "msme":
        return MSMEScraper()
    elif source_id == "startup_india":
        return StartupIndiaScraper()
    else:
        return GenericScraper(source_id, source_url)

def load_sources_from_json() -> List[Dict[str, Any]]:
    """
    Loads initial sources definition.
    """
    if os.path.exists(settings.SOURCES_JSON_PATH):
        try:
            with open(settings.SOURCES_JSON_PATH, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read sources.json: {e}")
    return []

async def seed_sources_in_db():
    """
    Seed initial sources into Firestore if they don't exist.
    """
    db = get_db()
    sources = load_sources_from_json()
    for src in sources:
        doc_ref = db.collection("sources").document(src["id"])
        doc = doc_ref.get()
        if not doc.exists:
            # Add active status and last scraped
            src["active"] = True
            src["last_scraped_at"] = None
            doc_ref.set(src)
            logger.info(f"Seeded source in DB: {src['id']}")

async def run_sync_pipeline(dry_run: bool = False, target_source_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Synchronizes opportunities with configured sources.
    Flow:
    1. Load active sources from DB (falling back to JSON if empty).
    2. For each source, run scraper to obtain raw documents.
    3. Check raw documents for new content hashes.
    4. Pass new text documents to Gemini AI to extract structured schemes.
    5. Deduplicate and save schemes to Firestore opportunities.
    """
    db = get_db()
    
    # Proactively seed sources
    await seed_sources_in_db()
    
    # Load active sources
    sources_ref = db.collection("sources")
    active_sources = []
    
    try:
        # Get active sources
        docs = sources_ref.stream()
        for doc in docs:
            data = doc.to_dict()
            if data.get("active", True):
                active_sources.append(data)
    except Exception as e:
        logger.warning(f"Failed to read sources from Firestore: {e}. Loading from local JSON.")
        active_sources = load_sources_from_json()

    if target_source_id:
        active_sources = [s for s in active_sources if s["id"] == target_source_id]

    sync_results = {
        "sources_scraped": 0,
        "raw_docs_scraped": 0,
        "new_raw_docs_saved": 0,
        "opportunities_processed": 0,
        "errors": []
    }

    for source in active_sources:
        source_id = source["id"]
        source_url = source["url"]
        
        try:
            logger.info(f"Processing source: {source_id} ({source_url})")
            scraper = scraper_factory(source_id, source_url)
            
            # Scrape raw content
            raw_docs = await scraper.scrape(dry_run=dry_run)
            sync_results["sources_scraped"] += 1
            sync_results["raw_docs_scraped"] += len(raw_docs)
            
            for raw_doc in raw_docs:
                content_hash = raw_doc["content_hash"]
                
                # Check duplicate raw doc
                raw_ref = db.collection("raw_documents").document(content_hash)
                raw_snap = raw_ref.get()
                
                # If raw doc is new or changed, we save it and process
                is_new_raw_doc = not raw_snap.exists
                if is_new_raw_doc:
                    if not dry_run:
                        raw_ref.set(raw_doc)
                    sync_results["new_raw_docs_saved"] += 1
                    
                    # Extract structured opportunity via AI
                    logger.info(f"Processing AI extraction for new raw doc: '{raw_doc['title']}'")
                    extracted_scheme = await parse_scheme_text(
                        raw_text=raw_doc["raw_text"], 
                        source_id=source_id,
                        default_url=raw_doc.get("source_url") or source_url
                    )
                    
                    # Deduplicate opportunity based on hash: name + source + ministry
                    opp_id = generate_opportunity_hash(
                        scheme_name=extracted_scheme.scheme_name,
                        source_id=source_id,
                        ministry=extracted_scheme.ministry
                    )
                    
                    opp_data = {
                        "name": extracted_scheme.scheme_name,
                        "description": extracted_scheme.description,
                        "category": source.get("category", "government_schemes"),
                        "country": extracted_scheme.country,
                        "state": extracted_scheme.state,
                        "industry": extracted_scheme.industries or ["All"],
                        "eligibility": extracted_scheme.eligibility,
                        "benefits": extracted_scheme.benefits,
                        "deadline": extracted_scheme.deadline,
                        "documents": extracted_scheme.documents_required or [],
                        "apply_url": extracted_scheme.official_link or raw_doc.get("source_url") or source_url,
                        "last_updated": time.time(),
                        "active_status": "active",
                        # Extra fields from Gemini extraction
                        "ministry": extracted_scheme.ministry,
                        "target_users": extracted_scheme.target_users or [],
                        "business_stage": extracted_scheme.business_stage or ["All"],
                        "financial_amount": extracted_scheme.financial_amount,
                        "application_process": extracted_scheme.application_process,
                        "tags": extracted_scheme.tags or [],
                        "raw_document_id": content_hash
                    }
                    
                    opp_ref = db.collection("opportunities").document(opp_id)
                    opp_snap = opp_ref.get()
                    
                    if not dry_run:
                        if opp_snap.exists:
                            logger.info(f"Updating existing opportunity: '{opp_data['name']}' (ID: {opp_id})")
                            opp_ref.update(opp_data)
                        else:
                            logger.info(f"Creating new opportunity: '{opp_data['name']}' (ID: {opp_id})")
                            opp_ref.set(opp_data)
                            
                    sync_results["opportunities_processed"] += 1
            
            # Update last scraped timestamp
            if not dry_run:
                db.collection("sources").document(source_id).update({
                    "last_scraped_at": time.time()
                })
                
        except Exception as e:
            err_msg = f"Failed to sync source {source_id}: {e}"
            logger.error(err_msg)
            sync_results["errors"].append(err_msg)

    return sync_results
