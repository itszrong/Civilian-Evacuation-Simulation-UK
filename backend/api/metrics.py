"""
Simple Metrics API

FastAPI endpoints for calculating metrics on simulation data.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import pandas as pd

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from services.metrics.metrics_builder_service import MetricsBuilderService
from core.config import get_settings


class MetricRequest(BaseModel):
    """Request model for calculating a single metric."""
    run_id: str
    source: str = "timeseries"  # "timeseries" or "events"
    metric_key: Optional[str] = None  # For timeseries data
    operation: str
    args: Dict[str, Any] = {}
    filters: Dict[str, Any] = {}
    group_by: Optional[str] = None
    post_process: Dict[str, Any] = {}


class MetricsRequest(BaseModel):
    """Request model for calculating multiple metrics."""
    run_id: str
    metrics: Dict[str, Dict[str, Any]]


class MetricResponse(BaseModel):
    """Response model for metric calculation."""
    metric_name: str
    value: Any
    error: Optional[str] = None


class MetricsResponse(BaseModel):
    """Response model for multiple metrics calculation."""
    run_id: str
    results: Dict[str, Any]


def get_metrics_builder() -> MetricsBuilderService:
    """Dependency to get metrics builder instance."""
    settings = get_settings()
    # Use absolute path to ensure we find the data
    base_path = Path(__file__).parent.parent
    data_path = getattr(settings, 'METRICS_DATA_PATH', str(base_path / 'local_s3' / 'runs'))
    return MetricsBuilderService(data_path)


router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/runs/{run_id}/info")
async def get_run_info(
    run_id: str,
    builder: MetricsBuilderService = Depends(get_metrics_builder)
) -> Dict[str, Any]:
    """Get information about available data for a run."""
    try:
        return builder.get_available_metrics(run_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calculate")
async def calculate_metric(
    request: MetricRequest,
    builder: MetricsBuilderService = Depends(get_metrics_builder)
) -> MetricResponse:
    """Calculate a single metric."""
    try:
        metric_config = {
            'source': request.source,
            'metric_key': request.metric_key,
            'operation': request.operation,
            'args': request.args,
            'filters': request.filters,
            'group_by': request.group_by,
            'post_process': request.post_process,
        }
        
        result = builder.calculate_metric(request.run_id, metric_config)
        
        # Convert pandas Series to dict for JSON serialization
        if isinstance(result, pd.Series):
            result = result.to_dict()
        
        return MetricResponse(
            metric_name=f"{request.operation}_{request.metric_key or 'events'}",
            value=result
        )
        
    except Exception as e:
        return MetricResponse(
            metric_name=f"{request.operation}_{request.metric_key or 'events'}",
            value=None,
            error=str(e)
        )


@router.post("/calculate-multiple")
async def calculate_metrics(
    request: MetricsRequest,
    builder: MetricsBuilderService = Depends(get_metrics_builder)
) -> MetricsResponse:
    """Calculate multiple metrics."""
    try:
        results = builder.calculate_metrics(request.run_id, {'metrics': request.metrics})
        
        # Convert pandas Series to dict for JSON serialization
        for key, value in results.items():
            if isinstance(value, pd.Series):
                results[key] = value.to_dict()
        
        return MetricsResponse(
            run_id=request.run_id,
            results=results
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/examples")
async def get_metric_examples() -> Dict[str, Any]:
    """Get example metric configurations."""
    return {
        "clearance_p95": {
            "description": "Time to 95% evacuation completion",
            "config": {
                "source": "timeseries",
                "metric_key": "clearance_pct",
                "operation": "percentile_time_to_threshold",
                "args": {"threshold_pct": 95},
                "filters": {"scope": "city"},
                "post_process": {"divide_by": 60, "round_to": 1}  # Convert to minutes
            }
        },
        "max_queue_by_edge": {
            "description": "Maximum queue length by edge",
            "config": {
                "source": "timeseries",
                "metric_key": "queue_len",
                "operation": "max_value",
                "group_by": "scope",
                "filters": {"scope_contains": "edge:"}
            }
        },
        "platform_overcrowding": {
            "description": "Time spent above density threshold at stations",
            "config": {
                "source": "timeseries",
                "metric_key": "density",
                "operation": "time_above_threshold",
                "args": {"threshold": 4.0},
                "filters": {"scope_contains": "station"},
                "post_process": {"divide_by": 60, "round_to": 1}  # Convert to minutes
            }
        },
        "evacuation_rate": {
            "description": "Average evacuation rate (people per minute)",
            "config": {
                "source": "timeseries",
                "metric_key": "clearance_pct",
                "operation": "area_under_curve",
                "filters": {"scope": "city"},
                "post_process": {"divide_by": 60}  # Per minute
            }
        }
    }


@router.delete("/cache")
async def clear_cache(
    builder: MetricsBuilderService = Depends(get_metrics_builder)
) -> Dict[str, str]:
    """Clear the metrics cache."""
    builder.clear_cache()
    return {"message": "Cache cleared successfully"}


@router.get("")
async def get_dashboard_metrics(
    builder: MetricsBuilderService = Depends(get_metrics_builder)
) -> Dict[str, Any]:
    """
    Get dashboard metrics for the frontend.
    This endpoint provides system-wide metrics for the dashboard.
    """
    try:
        # Get list of available runs to calculate system metrics
        from services.storage_service import StorageService
        storage = StorageService()
        runs = await storage.list_all_runs()
        
        # Calculate system-wide metrics
        total_runs = len(runs)
        completed_runs = len([r for r in runs if r.get('status') == 'completed'])
        failed_runs = len([r for r in runs if r.get('status') == 'failed'])
        
        # Try to get metrics from the most recent completed run
        recent_run_metrics = {}
        if runs:
            # Find most recent completed run with simulation data
            for run in runs:
                try:
                    run_id = run.get('run_id')
                    if not run_id:
                        continue
                        
                    # Check if we have metrics data for this run
                    info = builder.get_available_metrics(run_id)
                    if info['timeseries']['available']:
                        # Calculate some key metrics for the dashboard
                        metrics_config = {
                            'metrics': {
                                'clearance_p95': {
                                    'source': 'timeseries',
                                    'metric_key': 'clearance_pct',
                                    'operation': 'percentile_time_to_threshold',
                                    'args': {'threshold_pct': 95},
                                    'filters': {'scope': 'city'},
                                    'post_process': {'divide_by': 60, 'round_to': 1}
                                },
                                'max_queue': {
                                    'source': 'timeseries',
                                    'metric_key': 'queue_len',
                                    'operation': 'max_value',
                                    'filters': {'scope_contains': 'edge:'}
                                },
                                'total_events': {
                                    'source': 'events',
                                    'operation': 'count_events'
                                }
                            }
                        }
                        
                        recent_run_metrics = builder.calculate_metrics(run_id, metrics_config)
                        recent_run_metrics['run_id'] = run_id
                        break
                        
                except Exception as e:
                    # Skip this run if metrics calculation fails
                    continue
        
        return {
            "metrics": {
                "total_runs": total_runs,
                "completed_runs": completed_runs,
                "failed_runs": failed_runs,
                "success_rate": (completed_runs / total_runs * 100) if total_runs > 0 else 0,
                "recent_metrics": recent_run_metrics,
                "feeds_last_updated": None  # Placeholder for RSS feed timestamp
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard metrics: {str(e)}")
