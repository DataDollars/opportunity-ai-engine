import asyncio
import logging
import sys
import os

# Adjust path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.database.firebase import get_db, MockFirestoreClient
from backend.scheduler.daily_sync import seed_sources_in_db, run_sync_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("db_setup")

async def main():
    logger.info("Starting live Firestore database setup and validation...")
    
    db = get_db()
    
    # Check if we fell back to a mock client
    if isinstance(db, MockFirestoreClient):
        logger.error("Error: Could not connect to live Firestore. Client is in Mock fallback mode.")
        logger.error("Please ensure your key.json exists and .env has the correct path in FIREBASE_CREDENTIALS.")
        sys.exit(1)
        
    try:
        # 1. Test basic write capability
        logger.info("Testing write capability under collection 'system_tests'...")
        test_ref = db.collection("system_tests").document("connection_check")
        test_ref.set({
            "status": "success",
            "message": "Connection test executed successfully.",
            "initiated_by": "Opportunity AI Engine setup utility"
        })
        
        # 2. Test read capability
        logger.info("Testing read capability...")
        snap = test_ref.get()
        if snap.exists:
            logger.info(f"Read successful! Document details: {snap.to_dict()}")
        else:
            logger.error("Read failed: document did not exist after write.")
            sys.exit(1)
            
        # 3. Test delete capability
        logger.info("Cleaning up check document (testing delete)...")
        test_ref.delete()
        logger.info("Cleanup successful!")
        
        # 4. Seed opportunity sources
        logger.info("Seeding opportunity crawler sources index...")
        await seed_sources_in_db()
        logger.info("Sources indexed successfully!")
        
        # 5. Populate initial schemes (running sync pipeline)
        # We run a live sync (dry_run=False) targeting just 'myscheme'
        # to verify that the scrapers, extractors, and Gemini AI parsing all connect end-to-end
        logger.info("Running sync pipeline on 'myscheme' source to verify scraper and Gemini AI parse...")
        
        results = await run_sync_pipeline(dry_run=False, target_source_id="myscheme")
        logger.info(f"Pipeline executed successfully. Ingest details: {results}")
        
        logger.info("======================================================================")
        logger.info("Firestore Database successfully provisioned, verified, and seeded!")
        logger.info("======================================================================")

    except Exception as e:
        logger.error(f"Database setup failed during execution: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
