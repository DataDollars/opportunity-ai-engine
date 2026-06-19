import time
import logging
from typing import Dict, Any, List
from backend.ingestion.scrapers.base_scraper import BaseScraper
from backend.ingestion.extractors.html_extractor import extract_html_data

logger = logging.getLogger(__name__)

class StartupIndiaScraper(BaseScraper):
    """
    Scraper for Startup India (startupindia.gov.in)
    """
    def __init__(self):
        super().__init__(source_id="startup_india", source_url="https://www.startupindia.gov.in/")

    async def scrape(self, dry_run: bool = False) -> List[Dict[str, Any]]:
        if dry_run:
            logger.info("Dry run requested. Returning mock Startup India documents.")
            return self.get_mock_documents()

        logger.info(f"Starting crawl for Startup India: {self.source_url}")
        
        # Target the schemes page directly
        schemes_url = "https://www.startupindia.gov.in/content/sih/en/government-schemes.html"
        html = await self.fetch_url(schemes_url)
        if not html:
            # Fallback to main page crawl
            html = await self.fetch_url(self.source_url)
            
        if not html:
            logger.warning("Failed to fetch Startup India pages. Falling back to mock documents.")
            return self.get_mock_documents()

        try:
            data = extract_html_data(html, self.source_url)
            scheme_links = []
            
            for link in data.get("links", []):
                # Filter for scheme detail links
                if "scheme" in link.lower() or "sisfs" in link.lower():
                    if link not in scheme_links and not link.endswith("/government-schemes.html"):
                        scheme_links.append(link)

            logger.info(f"Found {len(scheme_links)} potential scheme links on Startup India. Crawling up to 3 pages...")
            raw_documents = []
            
            for url in scheme_links[:3]:
                try:
                    logger.info(f"Crawling Startup India scheme: {url}")
                    sc_html = await self.fetch_url(url)
                    if sc_html:
                        sc_data = extract_html_data(sc_html, url)
                        if len(sc_data.get("raw_text", "")) > 100:
                            raw_documents.append({
                                "source_id": self.source_id,
                                "source_url": url,
                                "title": sc_data.get("title") or "Startup India Scheme Detail",
                                "raw_text": sc_data.get("raw_text"),
                                "pdf_url": sc_data["pdf_links"][0] if sc_data["pdf_links"] else None,
                                "content_hash": self.generate_content_hash(sc_data.get("raw_text")),
                                "scraped_at": time.time()
                            })
                except Exception as ex:
                    logger.warning(f"Failed to crawl Startup India URL {url}: {ex}")

            if not raw_documents:
                logger.warning("Could not extract any detailed Startup India scheme pages. Using fallback mock documents.")
                return self.get_mock_documents()

            return raw_documents
        except Exception as e:
            logger.error(f"Error parsing Startup India HTML: {e}. Falling back to mocks.")
            return self.get_mock_documents()
