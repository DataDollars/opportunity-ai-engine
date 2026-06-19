import time
import logging
from typing import Dict, Any, List
from backend.ingestion.scrapers.base_scraper import BaseScraper
from backend.ingestion.extractors.html_extractor import extract_html_data

logger = logging.getLogger(__name__)

class MySchemeScraper(BaseScraper):
    """
    Scraper for myScheme.gov.in
    """
    def __init__(self):
        super().__init__(source_id="myscheme", source_url="https://www.myscheme.gov.in/")

    async def scrape(self, dry_run: bool = False) -> List[Dict[str, Any]]:
        if dry_run:
            logger.info("Dry run requested. Returning mock myScheme documents.")
            return self.get_mock_documents()

        logger.info(f"Starting crawl for myScheme: {self.source_url}")
        
        # Target the Business & Entrepreneurship category page
        category_url = "https://www.myscheme.gov.in/search/category/Business-and-Entrepreneurship"
        category_html = await self.fetch_url(category_url)
        
        if not category_html:
            logger.warning("Failed to fetch myScheme category list page. Falling back to mock documents.")
            return self.get_mock_documents()

        try:
            # Extract links to individual scheme pages
            category_data = extract_html_data(category_html, self.source_url)
            scheme_urls = []
            
            for link in category_data.get("links", []):
                # Filter for scheme detail links (e.g. /schemes/pmegp)
                if "/schemes/" in link and not link.endswith("/schemes"):
                    if link not in scheme_urls:
                        scheme_urls.append(link)

            logger.info(f"Found {len(scheme_urls)} scheme links on myScheme. Crawling up to 5 detail pages...")
            
            raw_documents = []
            # Limit the crawl to 5 pages to avoid getting blocked or exceeding execution time limits
            for url in scheme_urls[:5]:
                try:
                    logger.info(f"Crawling scheme detail: {url}")
                    scheme_html = await self.fetch_url(url)
                    if scheme_html:
                        data = extract_html_data(scheme_html, url)
                        if len(data.get("raw_text", "")) > 100:
                            raw_documents.append({
                                "source_id": self.source_id,
                                "source_url": url,
                                "title": data.get("title") or "myScheme Detail",
                                "raw_text": data.get("raw_text"),
                                "pdf_url": data["pdf_links"][0] if data["pdf_links"] else None,
                                "content_hash": self.generate_content_hash(data.get("raw_text")),
                                "scraped_at": time.time()
                            })
                except Exception as ex:
                    logger.warning(f"Failed to crawl scheme URL {url}: {ex}")

            if not raw_documents:
                logger.warning("Could not extract any detailed scheme pages. Using fallback mock documents.")
                return self.get_mock_documents()

            return raw_documents
        except Exception as e:
            logger.error(f"Error parsing myScheme HTML: {e}. Falling back to mocks.")
            return self.get_mock_documents()
