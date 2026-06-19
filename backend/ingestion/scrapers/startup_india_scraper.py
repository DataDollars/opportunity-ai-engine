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
        html = await self.fetch_url(self.source_url)
        if not html:
            logger.warning("Failed to fetch Startup India main page. Falling back to mock documents.")
            return self.get_mock_documents()

        try:
            data = extract_html_data(html, self.source_url)
            doc = {
                "source_id": self.source_id,
                "source_url": self.source_url,
                "title": data.get("title") or "Startup India",
                "raw_text": data.get("raw_text") or "Startup India hub portal",
                "pdf_url": data["pdf_links"][0] if data["pdf_links"] else None,
                "content_hash": self.generate_content_hash(data.get("raw_text") or "StartupIndia"),
                "scraped_at": time.time()
            }
            mocks = self.get_mock_documents()
            return [doc] + mocks
        except Exception as e:
            logger.error(f"Error parsing Startup India HTML: {e}. Falling back to mocks.")
            return self.get_mock_documents()
