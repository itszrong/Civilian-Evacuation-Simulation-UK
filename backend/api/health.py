"""
Health check endpoints for London Evacuation Planning Tool.
"""

from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
import structlog

from core.config import get_settings, Settings
from services.storage_service import StorageService
from services.feed_ingestion import FeedIngestorService

logger = structlog.get_logger(__name__)
router = APIRouter()

# Initialize services for health checks
storage_service = StorageService()
feed_service = FeedIngestorService(storage_service)


@router.get("/health")
async def health_check(settings: Settings = Depends(get_settings)) -> Dict[str, Any]:
    """
    Health check endpoint (liveness probe).
    Returns basic service health status.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "London Evacuation Planning Tool",
        "version": "1.0.0"
    }


@router.get("/ready")
async def readiness_check(settings: Settings = Depends(get_settings)) -> Dict[str, Any]:
    """
    Readiness check endpoint.
    Verifies that all required services are available.
    """
    checks = {}
    overall_ready = True
    
    # Check storage system
    try:
        # Test basic storage operations
        import tempfile
        import os
        test_path = os.path.join(settings.LOCAL_STORAGE_PATH, "test_file.txt")
        os.makedirs(os.path.dirname(test_path), exist_ok=True)
        
        with open(test_path, 'w') as f:
            f.write("test")
        
        if os.path.exists(test_path):
            os.remove(test_path)
            checks["storage"] = {"status": "ready", "details": "Local storage accessible"}
        else:
            raise Exception("Cannot write to storage")
            
    except Exception as e:
        checks["storage"] = {"status": "not_ready", "error": str(e)}
        overall_ready = False
    
    # Check sources configuration
    try:
        sources_config = feed_service.config
        source_count = sum(len(tier.sources) for tier in sources_config.tiers)
        checks["sources_config"] = {
            "status": "ready", 
            "details": f"{source_count} sources configured across {len(sources_config.tiers)} tiers"
        }
    except Exception as e:
        checks["sources_config"] = {"status": "not_ready", "error": str(e)}
        overall_ready = False
    
    # Check AI service availability
    ai_services_available = []
    if settings.OPENAI_API_KEY:
        ai_services_available.append("OpenAI")
    if settings.ANTHROPIC_API_KEY:
        ai_services_available.append("Anthropic")
    
    if ai_services_available:
        checks["ai_services"] = {
            "status": "ready", 
            "details": f"AI services available: {', '.join(ai_services_available)}"
        }
    else:
        checks["ai_services"] = {
            "status": "not_ready", 
            "error": "No AI API keys configured - explainer will use template responses"
        }
        # Don't mark as not ready since template responses work
    
    # Check simulation system
    try:
        from services.simulation_service import LondonGraphService
        graph_service = LondonGraphService()
        checks["simulation"] = {
            "status": "ready", 
            "details": "Simulation engine available"
        }
    except Exception as e:
        checks["simulation"] = {"status": "not_ready", "error": str(e)}
        overall_ready = False
    
    status_code = 200 if overall_ready else 503
    
    response_data = {
        "status": "ready" if overall_ready else "not_ready",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks
    }
    
    return JSONResponse(
        content=response_data,
        status_code=status_code
    )


@router.get("/system-metrics")
async def system_metrics_endpoint() -> Dict[str, Any]:
    """
    Prometheus-compatible metrics endpoint.
    Returns service metrics in JSON format.
    """
    try:
        # Get feeds status for metrics
        feeds_status = await feed_service.get_ingestion_status()
        
        # Get storage metrics
        storage_path = storage_service.settings.LOCAL_STORAGE_PATH
        runs_path = f"{storage_path}/runs"
        
        # Count runs
        import os
        import glob
        
        runs_total = 0
        runs_successful = 0 
        runs_failed = 0
        scenarios_simulated_total = 0
        abstain_count = 0
        total_explanations = 0
        
        if os.path.exists(runs_path):
            run_dirs = [d for d in os.listdir(runs_path) if os.path.isdir(os.path.join(runs_path, d))]
            runs_total = len(run_dirs)
            
            for run_dir in run_dirs:
                run_path = os.path.join(runs_path, run_dir)
                
                # Check for memo to determine if run succeeded
                memo_path = os.path.join(run_path, "memo.json")
                if os.path.exists(memo_path):
                    runs_successful += 1
                    
                    # Count abstains
                    try:
                        import json
                        with open(memo_path, 'r') as f:
                            memo = json.load(f)
                        total_explanations += 1
                        if memo.get("justification", {}).get("abstained", False):
                            abstain_count += 1
                    except Exception:
                        pass
                else:
                    runs_failed += 1
                
                # Count scenarios
                scenarios_path = os.path.join(run_path, "scenarios")
                if os.path.exists(scenarios_path):
                    scenario_files = glob.glob(os.path.join(scenarios_path, "*.yml"))
                    scenarios_simulated_total += len(scenario_files)
        
        # Calculate rates
        abstain_rate = abstain_count / total_explanations if total_explanations > 0 else 0.0
        success_rate = runs_successful / runs_total if runs_total > 0 else 0.0
        
        metrics = {
            "runs_total": runs_total,
            "runs_successful": runs_successful,
            "runs_failed": runs_failed,
            "scenarios_simulated_total": scenarios_simulated_total,
            "avg_run_duration_seconds": 0.0,  # Would need to track this in practice
            "abstain_rate": abstain_rate,
            "success_rate": success_rate,
            "feeds_last_updated": feeds_status.get("last_global_refresh"),
            "feeds_total_documents": feeds_status.get("total_documents", 0),
            "feeds_error_count": 0  # Would track this in feed service
        }
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": metrics
        }
        
    except Exception as e:
        logger.error("Failed to collect metrics", error=str(e))
        
        # Return minimal metrics on error
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": {
                "runs_total": 0,
                "runs_successful": 0,
                "runs_failed": 0,
                "error": str(e)
            }
        }
