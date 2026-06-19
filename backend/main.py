import logging
from fastapi import FastAPI, Query, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

from backend.config import settings
from backend.api import opportunities, sources, matching
from backend.scheduler.daily_sync import run_sync_pipeline

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("backend")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI-driven Opportunity Intelligence Engine Backend for tracking grants, subsidies, and schemes.",
    version="1.0.0"
)

# CORS middleware for future frontend connectivity
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Endpoint Routers
app.include_router(opportunities.router)
app.include_router(sources.router)
app.include_router(matching.router)

@app.get("/")
async def root():
    return {
        "status": "online",
        "app_name": settings.PROJECT_NAME,
        "config": {
            "firebase_project": settings.FIREBASE_PROJECT_ID,
            "gemini_model": settings.GEMINI_MODEL,
        }
    }

@app.post("/sync", tags=["Sync Pipeline"])
async def trigger_sync(
    background_tasks: BackgroundTasks,
    source_id: Optional[str] = Query(None, description="Specify source ID to sync only one source"),
    dry_run: bool = Query(False, description="Run crawlers and parse data without updating Firestore or using live Gemini quota"),
    background: bool = Query(False, description="If True, executes sync as background task immediately returning accepted status")
):
    """
    Manually triggers the ingestion and extraction sync pipeline.
    """
    logger.info(f"Manual sync triggered. source_id={source_id}, dry_run={dry_run}, background={background}")
    
    if background:
        # Run in background
        background_tasks.add_task(run_sync_pipeline, dry_run=dry_run, target_source_id=source_id)
        return {
            "status": "accepted",
            "message": "Synchronization task started in background."
        }
    else:
        # Run synchronously
        try:
            results = await run_sync_pipeline(dry_run=dry_run, target_source_id=source_id)
            return {
                "status": "completed",
                "results": results
            }
        except Exception as e:
            logger.error(f"Sync execution failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )
