import time
import logging
from typing import Dict, Any, List
from backend.ingestion.scrapers.base_scraper import BaseScraper
from backend.ingestion.extractors.html_extractor import extract_html_data

logger = logging.getLogger(__name__)

class MSMEScraper(BaseScraper):
    """
    Scraper for Ministry of MSME (msme.gov.in)
    """
    def __init__(self):
        super().__init__(source_id="msme", source_url="https://msme.gov.in/")

    async def scrape(self, dry_run: bool = False) -> List[Dict[str, Any]]:
        if dry_run:
            logger.info("Dry run requested. Returning mock MSME documents.")
            return self.get_mock_documents()

        logger.info(f"Starting crawl for Ministry of MSME: {self.source_url}")
        
        # Try to crawl the specific schemes page directly
        schemes_url = "https://msme.gov.in/all-schemes"
        html = await self.fetch_url(schemes_url)
        if not html:
            # Fallback to main page crawl
            html = await self.fetch_url(self.source_url)
            
        if not html:
            logger.warning("Failed to fetch MSME portal pages. Falling back to mock documents.")
            return self.get_mock_documents()

        try:
            data = extract_html_data(html, self.source_url)
            scheme_links = []
            
            for link in data.get("links", []):
                # Filter for scheme detail links
                if "scheme" in link.lower() or "champions" in link.lower():
                    if link not in scheme_links and not link.endswith("/all-schemes") and not link.endswith("/schemes"):
                        scheme_links.append(link)

            logger.info(f"Found {len(scheme_links)} potential scheme links on MSME portal. Crawling up to 3 pages...")
            raw_documents = []
            
            for url in scheme_links[:3]:
                try:
                    logger.info(f"Crawling MSME scheme: {url}")
                    sc_html = await self.fetch_url(url)
                    if sc_html:
                        sc_data = extract_html_data(sc_html, url)
                        if len(sc_data.get("raw_text", "")) > 100:
                            raw_documents.append({
                                "source_id": self.source_id,
                                "source_url": url,
                                "title": sc_data.get("title") or "MSME Scheme Detail",
                                "raw_text": sc_data.get("raw_text"),
                                "pdf_url": sc_data["pdf_links"][0] if sc_data["pdf_links"] else None,
                                "content_hash": self.generate_content_hash(sc_data.get("raw_text")),
                                "scraped_at": time.time()
                            })
                except Exception as ex:
                    logger.warning(f"Failed to crawl MSME URL {url}: {ex}")

            if not raw_documents:
                logger.warning("Could not extract any detailed MSME scheme pages. Using fallback mock documents.")
                return self.get_mock_documents()

            return raw_documents
        except Exception as e:
            logger.error(f"Error parsing MSME HTML: {e}. Falling back to mocks.")
            return self.get_mock_documents()
