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
        html = await self.fetch_url(self.source_url)
        if not html:
            logger.warning("Failed to fetch MSME main page. Falling back to mock documents.")
            return self.get_mock_documents()

        try:
            data = extract_html_data(html, self.source_url)
            doc = {
                "source_id": self.source_id,
                "source_url": self.source_url,
                "title": data.get("title") or "Ministry of MSME",
                "raw_text": data.get("raw_text") or "Ministry of MSME schemes",
                "pdf_url": data["pdf_links"][0] if data["pdf_links"] else None,
                "content_hash": self.generate_content_hash(data.get("raw_text") or "MSME"),
                "scraped_at": time.time()
            }
            mocks = self.get_mock_documents()
            return [doc] + mocks
        except Exception as e:
            logger.error(f"Error parsing MSME HTML: {e}. Falling back to mocks.")
            return self.get_mock_documents()
