"""
Artifacts API endpoints for London Evacuation Planning Tool.
Handles retrieval of run artifacts, images, and decision memos.
"""

from typing import Optional
from pathlib import Path
import json
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
import structlog

from services.storage_service import StorageService
from services.orchestration.multi_city_orchestrator import EvacuationOrchestrator
from models.schemas import AgentType

logger = structlog.get_logger(__name__)
router = APIRouter()

# Initialize storage service
storage_service = StorageService()


@router.get("/runs/{run_id}/memo")
async def get_decision_memo(run_id: str):
    """
    Get the decision memo for a completed run.
    
    Returns:
        JSON decision memo with best scenario, metrics, and justification
    """
    try:
        memo = await storage_service.get_run_artifact(run_id, "memo")
        
        if memo is None:
            raise HTTPException(
                status_code=404,
                detail=f"Decision memo not found for run {run_id}"
            )
        
        return memo
        
    except Exception as e:
        logger.error("Failed to retrieve decision memo", 
                    run_id=run_id, 
                    error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve decision memo: {str(e)}"
        )


@router.get("/artifacts/{run_id}/{artifact_type}")
async def get_run_artifact(run_id: str, artifact_type: str):
    """
    Get a specific artifact for a run.
    
    Args:
        run_id: The run identifier
        artifact_type: Type of artifact (city_simulation, emergency_plan, memo, etc.)
    
    Returns:
        JSON artifact data
    """
    try:
        artifact = await storage_service.get_run_artifact(run_id, artifact_type)
        
        if artifact is None:
            raise HTTPException(
                status_code=404,
                detail=f"Artifact '{artifact_type}' not found for run {run_id}"
            )
        
        return artifact
        
    except Exception as e:
        logger.error("Failed to retrieve artifact", 
                    run_id=run_id, 
                    artifact_type=artifact_type,
                    error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve artifact: {str(e)}"
        )


@router.get("/runs/{run_id}/images/{scenario_id}")
async def get_scenario_heatmap(run_id: str, scenario_id: str):
    """
    Get the heatmap image for a specific scenario.
    
    Returns:
        PNG image file showing the evacuation heatmap
    """
    # TODO: Implement actual image retrieval from storage
    
    # For now, return a 404 since we don't have actual images
    raise HTTPException(
        status_code=404,
        detail="Heatmap images not yet implemented"
    )


@router.get("/runs/{run_id}/scenarios")
async def get_run_scenarios(run_id: str):
    """
    Get all scenarios for a specific run.
    
    Returns:
        List of scenario configurations and results
    """
    try:
        # Get scenarios and results
        scenarios_data = await storage_service.get_run_artifact(run_id, "scenarios")
        results_data = await storage_service.get_run_artifact(run_id, "results")
        
        if scenarios_data is None:
            raise HTTPException(
                status_code=404,
                detail=f"Scenarios not found for run {run_id}"
            )
        
        scenarios = scenarios_data.get("scenarios", [])
        results = results_data.get("results", []) if results_data else []
        
        # Combine scenarios with their results
        combined_scenarios = []
        for scenario in scenarios:
            scenario_id = scenario.get("id")
            result = next(
                (r for r in results if r.get("scenario_id") == scenario_id),
                None
            )
            
            combined_scenarios.append({
                "id": scenario_id,
                "config": scenario,
                "results": result
            })
        
        return {
            "run_id": run_id,
            "scenarios": combined_scenarios,
            "total_count": len(combined_scenarios)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to retrieve scenarios", 
                    run_id=run_id, 
                    error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve scenarios: {str(e)}"
        )


@router.get("/runs/{run_id}/logs")
async def get_run_logs(
    run_id: str,
    agent: Optional[str] = Query(None, description="Filter by agent type"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of log entries")
):
    """
    Get structured logs for a specific run.
    
    Args:
        run_id: Run identifier
        agent: Optional agent type filter (planner, worker, judge, explainer)
        limit: Maximum number of log entries to return
    
    Returns:
        Paginated log entries in JSONL format
    """
    # TODO: Implement actual log retrieval from storage
    
    logs = [
        {
            "ts": "2024-09-20T13:10:02Z",
            "run_id": run_id,
            "agent": "planner",
            "step": "propose",
            "status": "ok",
            "duration_ms": 1234,
            "message": "Generated 2 scenarios within constraints"
        },
        {
            "ts": "2024-09-20T13:10:05Z", 
            "run_id": run_id,
            "scenario_id": "westminster_cordon_v1",
            "agent": "worker",
            "step": "simulate",
            "status": "ok",
            "duration_ms": 2456,
            "metrics": {
                "clearance_time": 84.5,
                "fairness_index": 0.72
            }
        }
    ]
    
    return {
        "run_id": run_id,
        "logs": logs[:limit],
        "total_count": len(logs),
        "filters": {"agent": agent} if agent else {}
    }

@router.get("/{run_id}/visualisation/{city}")
async def get_run_city_visualisation(run_id: str, city: str):
    """Get city-specific visualisation data for a run."""
    try:
        # Check if visualisation data exists
        viz_path = Path(storage_service.settings.LOCAL_STORAGE_PATH) / "runs" / run_id / "visualisations" / f"{city}_visualisation.json"
        
        if viz_path.exists():
            with open(viz_path, 'r') as f:
                viz_data = json.load(f)
            return {
                "run_id": run_id,
                "city": city,
                "visualisation_data": viz_data,
                "cached": True
            }
        
        # If no cached data, generate fresh visualisation
        from services.orchestration.multi_city_orchestrator import EvacuationOrchestrator
        multi_city_service = EvacuationOrchestrator()
        
        visualisation_result = multi_city_service.run_evacuation_simulation(
            city, {"num_simulations": 15, "num_routes": 6}
        )
        
        if 'error' in visualisation_result:
            raise HTTPException(status_code=400, detail=visualisation_result['error'])
        
        # Store the visualisation for future use
        viz_data = {
            "city": city,
            "run_id": run_id,
            "visualisation_result": visualisation_result,
            "timestamp": datetime.now().isoformat()
        }
        await storage_service.store_run_artifact(
            run_id=run_id,
            artifact_type="visualisation", 
            data=viz_data,
            producer_agent=AgentType.SIMULATION
        )
        
        return {
            "run_id": run_id,
            "city": city,
            "visualisation_data": visualisation_result,
            "cached": False
        }
        
    except Exception as e:
        logger.error(f"Failed to get visualisation for run {run_id}, city {city}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get visualisation: {str(e)}")
