import abc
import hashlib
import time
import logging
import random
from typing import Dict, Any, List, Optional
import httpx

logger = logging.getLogger(__name__)

class BaseScraper(abc.ABC):
    """
    Abstract Base Class for all crawlers/scrapers.
    """
    def __init__(self, source_id: str, source_url: str):
        self.source_id = source_id
        self.source_url = source_url
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5"
        }

    @abc.abstractmethod
    async def scrape(self, dry_run: bool = False) -> List[Dict[str, Any]]:
        """
        Executes the scraping process.
        Returns a list of raw documents:
        [
          {
            "source_id": str,
            "source_url": str,
            "title": str,
            "raw_text": str,
            "pdf_url": Optional[str],
            "content_hash": str,
            "scraped_at": float
          }
        ]
        """
        pass

    async def fetch_url(self, url: str, retries: int = 3, delay: float = 1.0) -> Optional[str]:
        """
        Helper method to fetch raw HTML content with retries and simple rate-limiting delay.
        """
        # Simple polite delay
        time.sleep(0.5 + random.random() * 0.5)
        
        for attempt in range(retries):
            try:
                async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
                    response = await client.get(url, headers=self.headers)
                    if response.status_code == 200:
                        return response.text
                    logger.warning(f"Fetch {url} returned status {response.status_code} (Attempt {attempt+1}/{retries})")
            except Exception as e:
                logger.warning(f"Error fetching {url} on attempt {attempt+1}/{retries}: {e}")
            
            if attempt < retries - 1:
                time.sleep(delay * (attempt + 1))
        
        return None

    def generate_content_hash(self, text: str) -> str:
        """
        Generates a SHA-256 hash for deduplication.
        """
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def get_mock_documents(self) -> List[Dict[str, Any]]:
        """
        Generates structured mock documents for local sandbox execution when live sites are offline or block requests.
        """
        # Seed mock datasets
        mocks = {
            "myscheme": [
                {
                    "title": "Prime Minister Employment Generation Programme (PMEGP)",
                    "raw_text": """The Prime Minister Employment Generation Programme (PMEGP) is a credit-linked subsidy program administered by the Ministry of MSME, Government of India. 
                    Objective: To generate employment opportunities in rural and urban areas of India through self-employment ventures.
                    Eligibility: Any individual above 18 years of age. For setting up project cost above Rs.10 lakh in manufacturing sector and above Rs. 5 lakh in business/service sector, the beneficiary should possess at least VIII standard pass educational qualification.
                    Benefits: Margin Money subsidy ranges from 15% to 35% of the project cost depending on area (urban/rural) and category (general/special). Max project cost allowed: Rs. 50 Lakhs for manufacturing, Rs. 20 Lakhs for service sector.
                    Documents Required: Aadhaar Card, PAN Card, VIII Standard Certificate, Project Report, Community Certificate (for special category).
                    Deadline: Applications are accepted year-round.
                    Official Website: https://www.kviconline.gov.in/pmegpeportal/pmegphome/index.jsp""",
                    "pdf_url": "https://www.myscheme.gov.in/schemes/pmegp.pdf"
                },
                {
                    "title": "Subsidies for Food Processing Units under PMKSY",
                    "raw_text": """Pradhan Mantri Kisan SAMPADA Yojana (PMKSY) is a comprehensive package implemented by Ministry of Food Processing Industries (MoFPI).
                    Eligibility: Maharashtra, Karnataka, Gujarat, and all other states. Micro, Small and Medium Enterprises (MSMEs), joint ventures, cooperatives, and private firms.
                    Benefits: Financial assistance in the form of grants-in-aid/subsidies. General areas: 35% of eligible project cost, max Rs. 5 Crore. Difficult areas (Hilly/Himalayan/North East): 50% of project cost.
                    Documents Required: Detailed Project Report (DPR), Land Document, CA Certificate for financial structure, Bank appraisal report.
                    Deadline: Open until August 31, 2026.
                    Official Website: https://mofpi.gov.in/pmksy""",
                    "pdf_url": None
                }
            ],
            "data_gov": [
                {
                    "title": "Technology Upgradation Fund Scheme (TUFS)",
                    "raw_text": """Ministry of Textiles offers Technology Upgradation Fund Scheme for Indian textile enterprises.
                    Eligibility: Powerlooms, handlooms, and textile processing units. Must be a registered business in India.
                    Benefits: Interest reimbursement of 5% or 10% Capital Investment Subsidy (CIS) up to a limit of Rs 5 Crore depending on the sub-sector.
                    Documents required: Machinery invoice, bank loan approval letter, MSME registration certificate.
                    Deadline: Open until December 31, 2026.""",
                    "pdf_url": None
                }
            ],
            "msme": [
                {
                    "title": "MSME Champions Scheme - Credit Linked Capital Subsidy Component",
                    "raw_text": """Ministry of MSME provides technology upgradation subsidy for micro and small enterprises.
                    Eligibility: Registered Micro and Small Enterprises in manufacturing or service sectors.
                    Benefits: 15% upfront capital subsidy for institutional finance up to Rs. 1 Crore (max subsidy Rs. 15 Lakhs) for induction of well-established and improved technologies.
                    Documents required: Udyam Registration, Loan Document, Machine Purchase Proof.
                    Deadline: Financial Year end 2026.""",
                    "pdf_url": "https://msme.gov.in/champions_clcss.pdf"
                }
            ],
            "startup_india": [
                {
                    "title": "Startup India Seed Fund Scheme (SISFS)",
                    "raw_text": """Startup India Seed Fund Scheme (SISFS) provides financial assistance to startups for proof of concept, prototype development, product trials, market entry, and commercialization.
                    Eligibility: Startup must be recognized by DPIIT. Incorporated not more than 2 years ago. Must have a business idea with commercial viability.
                    Benefits: Up to Rs. 20 Lakhs for prototype validation or trials. Up to Rs. 50 Lakhs for market entry, commercialization, or scaling through debt-linked instruments.
                    Documents required: DPIIT recognition certificate, Pitch Deck, GST registration (if applicable), Bank statement.
                    Deadline: Running active program (applications evaluated quarterly).""",
                    "pdf_url": "https://www.startupindia.gov.in/sisfs_guidelines.pdf"
                }
            ],
            "sidbi": [
                {
                    "title": "SIDBI Make in India Soft Loan Fund for Micro Small & Medium Enterprises (SMILE)",
                    "raw_text": """SMILE provides soft loans in the nature of quasi-equity and term loans on relatively soft terms to MSMEs.
                    Eligibility: Existing and new MSMEs in manufacturing and specified service sectors. High focus on 25 sectors of Make in India.
                    Benefits: Soft loans up to 10% to 15% of project cost (max Rs. 20-30 Lakhs). Term loans with attractive interest rates and longer repayment periods.
                    Documents required: Udyam Registration, past 3 years audited balance sheet, project report.
                    Deadline: Rolling submissions.""",
                    "pdf_url": None
                }
            ],
            "dgft": [
                {
                    "title": "Export Promotion Capital Goods (EPCG) Scheme",
                    "raw_text": """DGFT offers zero-duty import of capital goods for pre-production, production, and post-production.
                    Eligibility: Manufacturer exporters with or without supporting manufacturer(s), merchant exporters tied to supporting manufacturer(s), and service providers.
                    Benefits: Allows import of capital goods for pre-production, production and post-production at zero Customs duty, subject to an export obligation equivalent to 6 times of duty saved, to be fulfilled in 6 years.
                    Documents required: IEC (Import Export Code), Digital Signature, RCMC (Registration Cum Membership Certificate).
                    Deadline: Ongoing under Foreign Trade Policy 2023.""",
                    "pdf_url": "https://www.dgft.gov.in/epcg_handbook.pdf"
                }
            ]
        }

        selected_mocks = mocks.get(self.source_id, mocks["myscheme"])
        results = []
        for item in selected_mocks:
            results.append({
                "source_id": self.source_id,
                "source_url": item.get("official_link") or self.source_url,
                "title": item["title"],
                "raw_text": item["raw_text"],
                "pdf_url": item["pdf_url"],
                "content_hash": self.generate_content_hash(item["raw_text"]),
                "scraped_at": time.time()
            })
        return results
