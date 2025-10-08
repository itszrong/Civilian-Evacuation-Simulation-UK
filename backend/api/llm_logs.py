"""
LLM Logs API

Provides endpoints for viewing and analyzing LLM API call logs.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import structlog
from services.llm_service import get_llm_service

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/logs")
async def get_llm_logs(
    date: Optional[str] = Query(None, description="Date in YYYYMMDD format, defaults to today")
):
    """
    Get LLM call logs for a specific date.
    
    Returns detailed logs of all LLM API calls including prompts, responses, 
    timing, token usage, and metadata.
    """
    try:
        llm_service = get_llm_service()
        logs = llm_service.get_logs(date)
        
        return {
            "date": date or "today",
            "total_calls": len(logs),
            "logs": logs
        }
    except Exception as e:
        logger.error(f"Failed to retrieve LLM logs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_llm_stats(
    date: Optional[str] = Query(None, description="Date in YYYYMMDD format, defaults to today")
):
    """
    Get statistics for LLM API calls on a specific date.
    
    Returns aggregated statistics including total calls, duration, token usage,
    error rates, and success metrics.
    """
    try:
        llm_service = get_llm_service()
        stats = llm_service.get_stats(date)
        
        return {
            "date": date or "today",
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Failed to retrieve LLM stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs/search")
async def search_llm_logs(
    date: Optional[str] = Query(None, description="Date in YYYYMMDD format"),
    model: Optional[str] = Query(None, description="Filter by model name"),
    min_duration: Optional[float] = Query(None, description="Minimum duration in ms"),
    has_error: Optional[bool] = Query(None, description="Filter by error status")
):
    """
    Search and filter LLM call logs.
    
    Allows filtering logs by various criteria for debugging and analysis.
    """
    try:
        llm_service = get_llm_service()
        logs = llm_service.get_logs(date)
        
        # Apply filters
        if model:
            logs = [log for log in logs if log.get('model') == model]
        
        if min_duration is not None:
            logs = [log for log in logs if log.get('duration_ms', 0) >= min_duration]
        
        if has_error is not None:
            if has_error:
                logs = [log for log in logs if log.get('error') is not None]
            else:
                logs = [log for log in logs if log.get('error') is None]
        
        return {
            "date": date or "today",
            "filters": {
                "model": model,
                "min_duration": min_duration,
                "has_error": has_error
            },
            "total_results": len(logs),
            "logs": logs
        }
    except Exception as e:
        logger.error(f"Failed to search LLM logs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs/{call_id}")
async def get_llm_log_by_id(call_id: str):
    """
    Get detailed information for a specific LLM call by ID.
    """
    try:
        llm_service = get_llm_service()
        logs = llm_service.get_logs()
        
        # Find the specific log entry
        log = next((log for log in logs if log.get('call_id') == call_id), None)
        
        if not log:
            raise HTTPException(status_code=404, detail=f"Log entry {call_id} not found")
        
        return log
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve LLM log: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
