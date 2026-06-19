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
            dataset_links = []
            for link in data.get("links", []):
                # Filter for dataset catalogs or resource details
                if "/dataset/" in link or "/resource/" in link:
                    if link not in dataset_links:
                        dataset_links.append(link)

            logger.info(f"Found {len(dataset_links)} dataset links on data.gov.in. Crawling up to 3 pages...")
            raw_documents = []
            
            for url in dataset_links[:3]:
                try:
                    logger.info(f"Crawling dataset details: {url}")
                    ds_html = await self.fetch_url(url)
                    if ds_html:
                        ds_data = extract_html_data(ds_html, url)
                        if len(ds_data.get("raw_text", "")) > 100:
                            raw_documents.append({
                                "source_id": self.source_id,
                                "source_url": url,
                                "title": ds_data.get("title") or "Open Data Catalog",
                                "raw_text": ds_data.get("raw_text"),
                                "pdf_url": None,
                                "content_hash": self.generate_content_hash(ds_data.get("raw_text")),
                                "scraped_at": time.time()
                            })
                except Exception as ex:
                    logger.warning(f"Failed to crawl dataset URL {url}: {ex}")

            if not raw_documents:
                logger.warning("Could not extract any detailed dataset pages. Using fallback mock documents.")
                return self.get_mock_documents()

            return raw_documents
        except Exception as e:
            logger.error(f"Error parsing data.gov.in HTML: {e}. Falling back to mocks.")
            return self.get_mock_documents()
