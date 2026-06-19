import time
import logging
from typing import Dict, Any, List
from backend.ingestion.scrapers.base_scraper import BaseScraper
from backend.ingestion.extractors.html_extractor import extract_html_data

logger = logging.getLogger(__name__)

class DataGovScraper(BaseScraper):
    """
    Scraper for Open Government Data India (data.gov.in)
    """
    def __init__(self):
        super().__init__(source_id="data_gov", source_url="https://www.data.gov.in/apis")

    async def scrape(self, dry_run: bool = False) -> List[Dict[str, Any]]:
        if dry_run:
            logger.info("Dry run requested. Returning mock open-data documents.")
            return self.get_mock_documents()

        logger.info(f"Starting API scrape for data.gov.in: {self.source_url}")
        html = await self.fetch_url(self.source_url)
        if not html:
            logger.warning("Failed to fetch data.gov.in main page. Falling back to mock documents.")
            return self.get_mock_documents()

        try:
            data = extract_html_data(html, self.source_url)
            doc = {
                "source_id": self.source_id,
                "source_url": self.source_url,
                "title": data.get("title") or "Open Government Data APIS",
                "raw_text": data.get("raw_text") or "Data.gov.in APIs list",
                "pdf_url": None,
                "content_hash": self.generate_content_hash(data.get("raw_text") or "DataGov"),
                "scraped_at": time.time()
            }
            mocks = self.get_mock_documents()
            return [doc] + mocks
        except Exception as e:
            logger.error(f"Error parsing data.gov.in HTML: {e}. Falling back to mocks.")
            return self.get_mock_documents()
