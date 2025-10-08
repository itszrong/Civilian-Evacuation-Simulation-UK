"""
Simulation Queue API
Manages simulation requests triggered by civil unrest detection
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid
import json
from pathlib import Path

from scenarios.builder import ScenarioBuilder
from services.metrics.metrics_builder_service import MetricsBuilderService

router = APIRouter(prefix="/api/simulation-queue", tags=["simulation-queue"])


class SimulationRequest(BaseModel):
    """A simulation request from civil unrest detection."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    article_id: str
    article_title: str
    article_summary: str
    civil_unrest_score: float
    suggested_regions: List[str]
    status: str = "pending"  # pending, approved, rejected, running, completed
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    rejection_reason: Optional[str] = None
    
    # Simulation parameters
    scenario_id: Optional[str] = None
    metrics_config: Optional[Dict[str, Any]] = None
    simulation_results: Optional[Dict[str, Any]] = None


class ApprovalRequest(BaseModel):
    """Request to approve/reject a simulation."""
    action: str  # "approve" or "reject"
    approved_by: str
    rejection_reason: Optional[str] = None
    custom_regions: Optional[List[str]] = None
    custom_parameters: Optional[Dict[str, Any]] = None


class SimulationQueueService:
    """Service for managing simulation queue."""
    
    def __init__(self):
        self.queue_path = Path("local_s3/simulation_queue")
        self.queue_path.mkdir(parents=True, exist_ok=True)
        self.scenario_builder = ScenarioBuilder()
        self.metrics_builder = MetricsBuilderService()
        self._load_queue()
    
    def _load_queue(self):
        """Load existing queue from storage."""
        queue_file = self.queue_path / "queue.json"
        if queue_file.exists():
            with open(queue_file, 'r') as f:
                data = json.load(f)
                self.requests = [SimulationRequest(**req) for req in data.get('requests', [])]
        else:
            self.requests = []
    
    def _save_queue(self):
        """Save queue to storage."""
        queue_file = self.queue_path / "queue.json"
        data = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "requests": [req.model_dump(mode='json') for req in self.requests]
        }
        with open(queue_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def add_request(self, request: SimulationRequest) -> SimulationRequest:
        """Add a new simulation request to the queue."""
        # Check if similar request already exists
        existing = self.find_similar_request(request)
        if existing:
            # Update existing request with higher score if applicable
            if request.civil_unrest_score > existing.civil_unrest_score:
                existing.civil_unrest_score = request.civil_unrest_score
                existing.article_id = request.article_id
                existing.article_title = request.article_title
                existing.article_summary = request.article_summary
                self._save_queue()
                return existing
            return existing
        
        self.requests.append(request)
        self._save_queue()
        return request
    
    def find_similar_request(self, request: SimulationRequest) -> Optional[SimulationRequest]:
        """Find similar pending/approved/running requests."""
        for existing in self.requests:
            # Check if same article or same region with recent timestamp
            same_article = existing.article_id == request.article_id
            same_region_recent = (
                existing.suggested_regions == request.suggested_regions and
                existing.status in ["pending", "approved", "running"] and
                abs((existing.created_at - request.created_at).total_seconds()) < 3600
            )
            
            if same_article or same_region_recent:
                return existing
        return None
    
    def cleanup_duplicates(self) -> int:
        """Remove duplicate requests keeping only the most recent of each unique simulation."""
        seen = {}
        unique_requests = []
        
        # Sort by created_at descending (newest first)
        sorted_requests = sorted(self.requests, key=lambda r: r.created_at, reverse=True)
        
        for req in sorted_requests:
            # Create a key based on article_title and suggested_regions
            key = (req.article_title, tuple(req.suggested_regions))
            
            if key not in seen:
                seen[key] = True
                unique_requests.append(req)
        
        # Keep original order (oldest first)
        self.requests = sorted(unique_requests, key=lambda r: r.created_at)
        self._save_queue()
        
        return len(sorted_requests) - len(unique_requests)  # Number of duplicates removed
    
    def get_pending_requests(self) -> List[SimulationRequest]:
        """Get all pending requests."""
        return [req for req in self.requests if req.status == "pending"]
    
    def get_request(self, request_id: str) -> Optional[SimulationRequest]:
        """Get a specific request by ID."""
        for req in self.requests:
            if req.id == request_id:
                return req
        return None
    
    def approve_request(self, request_id: str, approval: ApprovalRequest) -> SimulationRequest:
        """Approve a simulation request or start an already-approved one."""
        request = self.get_request(request_id)
        if not request:
            raise ValueError(f"Request {request_id} not found")
        
        # Allow re-approval of pending, approved, or failed requests
        if request.status not in ["pending", "approved", "failed"]:
            raise ValueError(f"Request {request_id} has status '{request.status}' and cannot be started")
        
        if approval.action == "approve":
            request.status = "approved"
            request.approved_at = datetime.now(timezone.utc)
            request.approved_by = approval.approved_by
            
            # Use custom regions if provided
            regions = approval.custom_regions or request.suggested_regions
            
            # Create scenario using scenario builder
            scenario_params = {
                "name": f"Civil Unrest Response - {request.article_title[:50]}",
                "description": f"Emergency evacuation scenario based on: {request.article_summary[:200]}",
                "hazard_type": "civil_unrest",
                "affected_areas": regions,
                "severity": self._determine_severity(request.civil_unrest_score),
                "population_affected": self._estimate_population(regions),
                "parameters": {
                    "compliance_rate": 0.6,  # Lower compliance during unrest
                    "car_availability": 0.3,  # Reduced due to traffic/safety
                    "walking_speed_reduction": 0.4,  # Slower due to crowds/obstacles
                    "transport_disruption": 0.8,  # High disruption expected
                    **(approval.custom_parameters or {})
                }
            }
            
            scenario = self.scenario_builder.create_scenario(
                custom_params=scenario_params,
                scenario_name=scenario_params["name"]
            )
            
            request.scenario_id = scenario["scenario_id"]
            
            # Create metrics configuration
            request.metrics_config = {
                "clearance_p50": {
                    "source": "timeseries",
                    "metric_key": "clearance_pct",
                    "operation": "percentile_time_to_threshold",
                    "args": {"threshold_pct": 50}
                },
                "clearance_p95": {
                    "source": "timeseries", 
                    "metric_key": "clearance_pct",
                    "operation": "percentile_time_to_threshold",
                    "args": {"threshold_pct": 95}
                },
                "max_queue_length": {
                    "source": "timeseries",
                    "metric_key": "queue_len",
                    "operation": "max_value"
                }
            }
            
            # Save scenario
            self.scenario_builder.save_scenario(scenario)
            
        elif approval.action == "reject":
            request.status = "rejected"
            request.rejection_reason = approval.rejection_reason
        
        self._save_queue()
        return request
    
    def _determine_severity(self, unrest_score: float) -> str:
        """Determine scenario severity based on unrest score."""
        if unrest_score >= 8.0:
            return "critical"
        elif unrest_score >= 6.0:
            return "high"
        elif unrest_score >= 4.0:
            return "medium"
        else:
            return "low"
    
    def _estimate_population(self, regions: List[str]) -> int:
        """Estimate affected population based on regions."""
        # Rough population estimates for London regions
        population_estimates = {
            "central london": 200000,
            "city of london": 10000,
            "westminster": 250000,
            "camden": 270000,
            "islington": 240000,
            "hackney": 280000,
            "tower hamlets": 320000,
            # Add more as needed
        }
        
        total_pop = 0
        for region in regions:
            region_lower = region.lower()
            if region_lower in population_estimates:
                total_pop += population_estimates[region_lower]
            else:
                total_pop += 150000  # Default estimate
        
        return total_pop


# Global service instance
queue_service = SimulationQueueService()


@router.get("/requests", response_model=List[SimulationRequest])
async def get_simulation_requests(status: Optional[str] = None):
    """Get simulation requests, optionally filtered by status."""
    if status:
        return [req for req in queue_service.requests if req.status == status]
    return queue_service.requests


@router.get("/requests/pending", response_model=List[SimulationRequest])
async def get_pending_requests():
    """Get pending simulation requests."""
    return queue_service.get_pending_requests()


@router.get("/requests/{request_id}", response_model=SimulationRequest)
async def get_simulation_request(request_id: str):
    """Get a specific simulation request."""
    request = queue_service.get_request(request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    return request


@router.post("/requests", response_model=SimulationRequest)
async def create_simulation_request(request: SimulationRequest):
    """Create a new simulation request."""
    return queue_service.add_request(request)


@router.post("/requests/{request_id}/approve", response_model=SimulationRequest)
async def approve_simulation_request(request_id: str, approval: ApprovalRequest):
    """Approve or reject a simulation request and start simulation if approved."""
    try:
        request = queue_service.approve_request(request_id, approval)
        
        # If approved, automatically trigger the simulation
        if request.status == "approved" and request.scenario_id:
            # Import here to avoid circular imports
            from agents.planner_agent import PlannerAgent
            import asyncio
            
            # Mark as running
            request.status = "running"
            queue_service._save_queue()
            
            # Start simulation in background
            async def run_simulation():
                import traceback
                try:
                    from structlog import get_logger
                    logger = get_logger(__name__)
                    logger.info(f"Starting simulation for {request.id}")
                    
                    planner = PlannerAgent()
                    city = request.suggested_regions[0] if request.suggested_regions else "westminster"
                    
                    logger.info(f"Running evacuation plan for {city} with scenario {request.scenario_id}")
                    
                    # Run the agentic planning simulation
                    result = await planner.plan_evacuation(
                        city=city.lower(),
                        objective="minimize_casualties",
                        scenario_id=request.scenario_id
                    )
                    
                    # Update request with results
                    request.status = "completed"
                    request.simulation_results = result
                    queue_service._save_queue()
                    
                    logger.info(f"Simulation {request.id} completed successfully")
                    
                except Exception as e:
                    from structlog import get_logger
                    logger = get_logger(__name__)
                    error_details = {
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "traceback": traceback.format_exc()
                    }
                    logger.error(f"Simulation {request.id} failed", error=error_details)
                    
                    request.status = "failed"
                    request.simulation_results = error_details
                    queue_service._save_queue()
            
            # Run simulation asynchronously without blocking
            try:
                asyncio.create_task(run_simulation())
            except Exception as e:
                import traceback
                from structlog import get_logger
                logger = get_logger(__name__)
                logger.error(f"Failed to create simulation task", error=str(e), traceback=traceback.format_exc())
                request.status = "failed"
                request.simulation_results = {"error": f"Failed to start simulation: {str(e)}"}
                queue_service._save_queue()
        
        return request
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cleanup")
async def cleanup_duplicate_requests():
    """Remove duplicate simulation requests from the queue."""
    duplicates_removed = queue_service.cleanup_duplicates()
    return {
        "message": f"Cleanup complete. Removed {duplicates_removed} duplicate requests.",
        "duplicates_removed": duplicates_removed,
        "remaining_requests": len(queue_service.requests)
    }


@router.delete("/requests/{request_id}")
async def delete_simulation_request(request_id: str):
    """Delete a simulation request."""
    request = queue_service.get_request(request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    queue_service.requests = [req for req in queue_service.requests if req.id != request_id]
    queue_service._save_queue()
    
    return {"message": "Request deleted successfully"}


@router.get("/stats")
async def get_queue_stats():
    """Get simulation queue statistics."""
    requests = queue_service.requests
    
    stats = {
        "total_requests": len(requests),
        "pending": len([r for r in requests if r.status == "pending"]),
        "approved": len([r for r in requests if r.status == "approved"]),
        "rejected": len([r for r in requests if r.status == "rejected"]),
        "running": len([r for r in requests if r.status == "running"]),
        "completed": len([r for r in requests if r.status == "completed"]),
        "last_updated": datetime.now(timezone.utc).isoformat()
    }
    
    return stats


def get_queue_status() -> Dict[str, Any]:
    """
    Get queue status synchronously for use by tools.
    Returns dictionary with pending, processing, and completed requests.
    """
    requests = queue_service.requests
    
    return {
        "pending": [
            {
                "run_id": req.id,
                "city": req.suggested_regions[0] if req.suggested_regions else "Unknown",
                "hazard_type": "civil_unrest",
                "status": req.status
            }
            for req in requests if req.status == "pending"
        ],
        "processing": [
            {
                "run_id": req.id,
                "city": req.suggested_regions[0] if req.suggested_regions else "Unknown",
                "hazard_type": "civil_unrest",
                "status": req.status
            }
            for req in requests if req.status == "running"
        ],
        "completed": [
            {
                "run_id": req.id,
                "city": req.suggested_regions[0] if req.suggested_regions else "Unknown",
                "hazard_type": "civil_unrest",
                "status": req.status
            }
            for req in requests if req.status == "completed"
        ]
    }


class AddToQueueRequest(BaseModel):
    """Simplified request to add article to queue."""
    article_id: str
    article_title: str
    article_url: str
    priority: str = "high"
    civil_unrest_score: Optional[float] = None
    suggested_regions: Optional[List[str]] = None


@router.post("/add")
async def add_to_queue(request: AddToQueueRequest):
    """
    Add an article to the simulation queue and start processing immediately.
    Simplified endpoint for frontend use.
    """
    # Create a full SimulationRequest
    sim_request = SimulationRequest(
        article_id=request.article_id,
        article_title=request.article_title,
        article_summary=request.article_url,  # Use URL as summary for now
        civil_unrest_score=request.civil_unrest_score or 7.0,  # Default high score
        suggested_regions=request.suggested_regions or ["Central London"],
        status="approved"  # Auto-approve high priority items
    )
    
    # Add to queue
    added_request = queue_service.add_request(sim_request)
    
    # Auto-approve and create scenario if priority is high
    if request.priority == "high" and added_request.status != "approved":
        approval = ApprovalRequest(
            action="approve",
            approved_by="System Auto-Approval",
            custom_regions=request.suggested_regions
        )
        added_request = queue_service.approve_request(added_request.id, approval)
    
    return {
        "success": True,
        "message": "Article added to simulation queue",
        "request_id": added_request.id,
        "scenario_id": added_request.scenario_id,
        "status": added_request.status
    }
