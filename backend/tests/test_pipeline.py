import unittest
import asyncio
from fastapi.testclient import TestClient

from backend.main import app
from backend.ingestion.extractors.html_extractor import extract_html_data
from backend.ingestion.extractors.pdf_extractor import extract_pdf_text_from_bytes
from backend.ai.scheme_parser import generate_opportunity_hash
from backend.ai.matcher import CompanyProfile, run_local_match_heuristics
from backend.scheduler.daily_sync import run_sync_pipeline

class TestOpportunityAiEngine(unittest.TestCase):
    
    def setUp(self):
        self.client = TestClient(app)
        import backend.ai.scheme_parser
        self._original_get_gemini_client = backend.ai.scheme_parser.get_gemini_client
        backend.ai.scheme_parser.get_gemini_client = lambda: None

    def tearDown(self):
        import backend.ai.scheme_parser
        backend.ai.scheme_parser.get_gemini_client = self._original_get_gemini_client

    def test_root_endpoint(self):
        """Test that the entry root returns online status."""
        from backend.config import settings
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "online")
        self.assertEqual(data["config"]["firebase_project"], settings.FIREBASE_PROJECT_ID)

    def test_html_extractor(self):
        """Verify HTML parser strips tags and pulls links correctly."""
        html = """
        <html>
            <head><title>Test MSME Scheme</title></head>
            <body>
                <script>alert("test");</script>
                <h1>Welcome to MSME India</h1>
                <p>We support small business with 25% subsidies.</p>
                <a href="/guidelines.pdf">Download Guidelines</a>
                <a href="https://example.com/apply">Apply Here</a>
            </body>
        </html>
        """
        extracted = extract_html_data(html, base_url="https://msme.gov.in/")
        self.assertEqual(extracted["title"], "Test MSME Scheme")
        self.assertIn("subsidies", extracted["raw_text"])
        self.assertNotIn("alert", extracted["raw_text"])
        self.assertIn("https://msme.gov.in/guidelines.pdf", extracted["pdf_links"])
        self.assertIn("https://example.com/apply", extracted["links"])

    def test_pdf_extractor(self):
        """Test PDF bytes extractor (mocking PDF format is hard, but we verify empty handling)."""
        text = extract_pdf_text_from_bytes(b"invalid-pdf-bytes")
        self.assertEqual(text, "")

    def test_opportunity_hash(self):
        """Ensure duplicate detection hash remains stable."""
        h1 = generate_opportunity_hash("SAMPADA", "myscheme", "Ministry of Food")
        h2 = generate_opportunity_hash("SAMPADA", "myscheme", "Ministry of Food")
        h3 = generate_opportunity_hash("SAMPADA ", "myscheme", "Ministry of Food")  # extra space
        
        self.assertEqual(h1, h2)
        self.assertEqual(h1, h3)

    def test_matching_heuristics(self):
        """Test rule-based matching engine logic."""
        company = CompanyProfile(
            company_name="Alpha Agro Foods",
            industry="Food Processing",
            state="Maharashtra",
            employees=25,
            turnover=30000000.0,
            business_type="MSME"
        )
        
        # Perfect matching scheme
        opp = {
            "name": "Food Subsidy Scheme",
            "state": "Maharashtra",
            "industries": ["Food Processing", "Agriculture"],
            "target_users": ["MSME"],
            "eligibility": "Located in Maharashtra"
        }
        
        match_result = run_local_match_heuristics(company, opp)
        self.assertGreaterEqual(match_result.score, 80)
        self.assertIn("Industry matches company's sector", match_result.reason)
        
        # Non-matching state scheme
        opp_other_state = {
            "name": "Gujarat Textiles Grant",
            "state": "Gujarat",
            "industries": ["Textiles"],
            "target_users": ["MSME"]
        }
        
        match_result_mismatch = run_local_match_heuristics(company, opp_other_state)
        self.assertLess(match_result_mismatch.score, 50)
        self.assertIn("Scheme is specific to Gujarat", match_result_mismatch.reason)

    def test_sync_dry_run(self):
        """Test that the sync pipeline runs without crashing in dry_run mode."""
        results = asyncio.run(run_sync_pipeline(dry_run=True))
        
        self.assertGreater(results["sources_scraped"], 0)
        self.assertGreater(results["raw_docs_scraped"], 0)
        self.assertEqual(results["new_raw_docs_saved"], results["raw_docs_scraped"])

    def test_api_routes(self):
        """Test API endpoints behavior."""
        # 1. Get Sources
        response_sources = self.client.get("/sources")
        self.assertEqual(response_sources.status_code, 200)
        self.assertGreater(len(response_sources.json()), 0)
        
        # 2. POST Match endpoint
        company_payload = {
            "company_name": "Tech Innovators",
            "industry": "Technology",
            "state": "Karnataka",
            "employees": 15,
            "turnover": 5000000,
            "business_type": "Startup"
        }
        response_match = self.client.post("/match", json=company_payload)
        self.assertEqual(response_match.status_code, 200)
        match_data = response_match.json()
        self.assertIn("total_candidates_found", match_data)
        self.assertIn("matches", match_data)

        # 3. POST Sync (dry run)
        response_sync = self.client.post("/sync?dry_run=true")
        self.assertEqual(response_sync.status_code, 200)
        sync_data = response_sync.json()
        self.assertEqual(sync_data["status"], "completed")
        self.assertIn("results", sync_data)

if __name__ == "__main__":
    unittest.main()
