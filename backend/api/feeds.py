"""
Data feeds API endpoints for London Evacuation Planning Tool.
"""

from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, BackgroundTasks
import structlog

from services.feed_ingestion import FeedIngestorService
from services.storage_service import StorageService

logger = structlog.get_logger(__name__)
router = APIRouter()

# Initialize services
storage_service = StorageService()
feed_service = FeedIngestorService(storage_service)


@router.post("/feeds/refresh")
async def refresh_feeds(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """
    Trigger incremental fetch of all configured data feeds.
    Uses ETag/If-Modified-Since for efficient updates.
    
    Returns:
        Summary of fetch operation with counts of fetched, updated, and error items.
    """
    logger.info("Manual feed refresh triggered")
    
    # Add background task to perform the actual refresh
    background_tasks.add_task(perform_feed_refresh)
    
    # Return immediate response while background task runs
    return {
        "status": "refresh_started",
        "timestamp": datetime.utcnow().isoformat(),
        "message": "Feed refresh initiated in background",
        "estimated_duration_minutes": 5
    }


async def perform_feed_refresh() -> Dict[str, int]:
    """
    Perform the actual feed refresh operation.
    """
    try:
        logger.info("Starting background feed refresh")
        
        # Perform the actual ingestion
        result = await feed_service.fetch_all_sources()
        
        # Update last refresh time
        await storage_service.set_last_refresh_time(datetime.utcnow())
        
        logger.info("Background feed refresh completed", 
                   fetched=result.get('fetched', 0),
                   updated=result.get('updated', 0),
                   errors=result.get('errors', 0))
        
        return {
            "fetched": result.get('fetched', 0),
            "updated": result.get('updated', 0),
            "errors": result.get('errors', 0)
        }
        
    except Exception as e:
        logger.error("Background feed refresh failed", error=str(e))
        return {
            "fetched": 0,
            "updated": 0,
            "errors": 1
        }


@router.get("/feeds/status")
async def get_feeds_status() -> Dict[str, Any]:
    """
    Get status of all configured data feeds.
    
    Returns:
        Status information for each feed including last update times and error counts.
    """
    try:
        status = await feed_service.get_ingestion_status()
        return status
    except Exception as e:
        logger.error("Failed to get feeds status", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve feeds status: {str(e)}"
        )
