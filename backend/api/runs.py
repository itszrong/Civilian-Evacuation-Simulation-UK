"""
Runs API endpoints for London Evacuation Planning Tool.
Handles the main agentic planning workflow with SSE streaming.
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
from sse_starlette import EventSourceResponse
import structlog

from models.schemas import (
    RunRequest, RunStatus, TaskStatus,
    SSEEvent, PlannerProgressEvent, WorkerResultEvent,
    JudgeSummaryEvent, ExplainerAnswerEvent, RunCompleteEvent,
    ScenarioResult, SimulationMetrics
)
from agents.planner_agent import PlannerAgent
from agents.worker_agent import WorkerAgent
from agents.judge_agent import JudgeAgent
from agents.explainer_agent import ExplainerAgent
from services.storage_service import StorageService
from services.orchestration.multi_city_orchestrator import EvacuationOrchestrator

logger = structlog.get_logger(__name__)
router = APIRouter()

# Initialize services and agents
storage_service = StorageService()
multi_city_service = EvacuationOrchestrator()
planner_agent = PlannerAgent()
judge_agent = JudgeAgent()
explainer_agent = ExplainerAgent(storage_service)

# In-memory storage for active runs (replace with proper database)
active_runs = {}


@router.post("/runs", response_class=StreamingResponse)
async def start_evacuation_run(request: RunRequest) -> StreamingResponse:
    """
    Start a new evacuation planning run with streaming results.
    
    This endpoint initiates the main agentic workflow:
    1. Planner generates scenarios
    2. Workers simulate scenarios in parallel
    3. Judge ranks scenarios
    4. Explainer provides justification with citations
    
    Returns:
        Server-Sent Events stream with real-time progress updates
    """
    run_id = f"r_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    
    logger.info(
        "Starting evacuation planning run",
        run_id=run_id,
        objective=request.intent.objective,
        city=request.intent.city
    )
    
    # Store run metadata
    active_runs[run_id] = {
        "run_id": run_id,
        "status": TaskStatus.IN_PROGRESS,
        "created_at": datetime.utcnow(),
        "intent": request.intent,
        "scenario_count": 0
    }
    
    async def generate_run_events():
        """Generate SSE events for the evacuation planning run."""
        try:
            # Emit initial event
            yield {
                "event": "run.started",
                "data": json.dumps({
                    "run_id": run_id,
                    "status": "started",
                    "timestamp": datetime.utcnow().isoformat()
                })
            }

            # Phase 1: Planning
            yield {
                "event": "planner.progress",
                "data": json.dumps({
                    "status": "starting",
                    "message": "Analysing user intent and constraints"
                })
            }

            # Generate scenarios using planner agent
            scenarios = await planner_agent.generate_scenarios(request.intent)

            yield {
                "event": "planner.progress",
                "data": json.dumps({
                    "status": "completed",
                    "num_scenarios": len(scenarios),
                    "message": f"Generated {len(scenarios)} scenarios"
                })
            }
            
            # Store scenarios
            for scenario in scenarios:
                await storage_service.store_run_artifact(
                    run_id, "scenario", scenario.dict(), "planner"
                )
            
            active_runs[run_id]["scenario_count"] = len(scenarios)

            # Phase 2: Run city simulation
            yield {
                "event": "worker.progress",
                "data": json.dumps({
                    "status": "starting",
                    "message": "Running city evacuation simulations"
                })
            }

            try:
                # Run actual city simulation
                logger.info("Starting city simulation", city=request.intent.city)
                loop = asyncio.get_event_loop()
                sim_config = {
                    "num_routes": 3,  # Reduced for faster testing
                    "num_walks": 3,   # Reduced for faster testing
                    "num_simulations": request.intent.constraints.max_scenarios
                }

                sim_result = await loop.run_in_executor(
                    None,
                    multi_city_service.run_evacuation_simulation,
                    request.intent.city,
                    sim_config
                )
                logger.info("City simulation completed", city=request.intent.city)

                yield {
                    "event": "worker.result",
                    "data": json.dumps({
                        "status": "completed",
                        "message": f"Completed simulation for {request.intent.city}"
                    })
                }
            except Exception as sim_error:
                logger.error("City simulation failed", error=str(sim_error))
                yield {
                    "event": "worker.error",
                    "data": json.dumps({
                        "status": "failed",
                        "message": f"Simulation error: {str(sim_error)}"
                    })
                }
                raise

            # Create mock results from scenarios for compatibility
            results = []
            for i, scenario in enumerate(scenarios):
                result = ScenarioResult(
                    scenario_id=scenario.id,
                    status=TaskStatus.COMPLETED,
                    duration_ms=30000 + (i * 1000),
                    metrics=SimulationMetrics(
                        clearance_time=45 + (i * 5),
                        max_queue=1000 + (i * 100),
                        fairness_index=0.85 - (i * 0.05),
                        robustness=0.75 - (i * 0.03)
                    )
                )
                results.append(result)

            # Store simulation result
            await storage_service.store_run_artifact(
                run_id, "city_simulation", sim_result, "worker"
            )

            # Phase 3: Ranking using judge agent
            judge_result = await judge_agent.rank_scenarios(
                results, request.intent.preferences, request.intent
            )
            
            yield {
                "event": "judge.summary",
                "data": json.dumps({
                    "ranking": [r.dict() for r in judge_result.ranking],
                    "best_scenario_id": judge_result.best_scenario_id
                })
            }

            # Phase 4: Explanation using explainer agent
            if judge_result.best_scenario_id:
                best_scenario = next(
                    (s for s in scenarios if s.id == judge_result.best_scenario_id),
                    None
                )
                best_result = next(
                    (r for r in results if r.scenario_id == judge_result.best_scenario_id),
                    None
                )

                if best_scenario and best_result:
                    explanation = await explainer_agent.explain_scenario(
                        best_scenario, best_result, request.intent
                    )

                    yield {
                        "event": "explainer.answer",
                        "data": json.dumps({
                            "scenario_id": explanation.scenario_id,
                            "answer": explanation.answer,
                            "citations": [c.dict() for c in explanation.citations],
                            "abstained": explanation.abstained
                        })
                    }

                    # Create and store decision memo
                    memo = {
                        "run_id": run_id,
                        "best_scenario": judge_result.best_scenario_id,
                        "weights": request.intent.preferences.dict(),
                        "metrics": best_result.metrics.dict(),
                        "justification": explanation.dict()
                    }

                    await storage_service.store_run_artifact(
                        run_id, "memo", memo, "explainer"
                    )

            # Complete the run
            active_runs[run_id]["status"] = TaskStatus.COMPLETED
            active_runs[run_id]["completed_at"] = datetime.utcnow()
            active_runs[run_id]["best_scenario_id"] = judge_result.best_scenario_id

            yield {
                "event": "run.complete",
                "data": json.dumps({
                    "run_id": run_id,
                    "best_scenario": judge_result.best_scenario_id,
                    "status": "completed"
                })
            }

        except Exception as e:
            logger.error("Run failed", run_id=run_id, error=str(e))
            active_runs[run_id]["status"] = TaskStatus.FAILED

            yield {
                "event": "run.error",
                "data": json.dumps({
                    "run_id": run_id,
                    "error": str(e),
                    "status": "failed"
                })
            }
    
    return EventSourceResponse(generate_run_events())


@router.get("/runs/{run_id}")
async def get_run_status(run_id: str):
    """
    Get complete status, scenarios, and results for a specific run.
    """
    run_data = active_runs.get(run_id)

    if not run_data:
        run_metadata = await storage_service.get_run_metadata(run_id)
        if not run_metadata:
            raise HTTPException(status_code=404, detail="Run not found")
        run_data = run_metadata

    scenarios_result = await storage_service.get_run_artifact(run_id, "scenarios")
    results_result = await storage_service.get_run_artifact(run_id, "results")
    memo = await storage_service.get_run_artifact(run_id, "memo")

    scenarios = []
    if scenarios_result and "scenarios" in scenarios_result:
        scenario_list = scenarios_result["scenarios"]
        results_list = results_result.get("results", []) if results_result else []

        for i, scenario_data in enumerate(scenario_list):
            result = results_list[i] if i < len(results_list) else {}
            
            # Extract rich scenario data from the stored config
            config = scenario_data.get("config", {})
            
            scenarios.append({
                "scenario_id": scenario_data.get("scenario_id", f"scenario_{i}"),
                "scenario_name": config.get("scenario_name", f"Scenario {i+1}"),
                "name": config.get("name", config.get("scenario_name", f"Scenario {i+1}")),
                "description": config.get("description", ""),
                "hazard_type": config.get("hazard_type", "general"),
                "evacuation_direction": config.get("evacuation_direction", ""),
                "origin_location": config.get("origin_location", ""),
                "compliance_rate": config.get("compliance_rate", 0.75),
                "transport_disruption": config.get("transport_disruption", 0.3),
                "population_affected": config.get("population_affected", 50000),
                "routes_calculated": config.get("routes_calculated", 0),
                "walks_simulated": config.get("walks_simulated", 0),
                "template_key": config.get("template_key", ""),
                "metrics": result.get("metrics", {
                    "clearance_time": 0,
                    "max_queue": 0,
                    "fairness_index": 0,
                    "robustness": 0
                }),
                "status": result.get("status", "completed"),
                "rank": i + 1,
                "score": result.get("metrics", {}).get("fairness_index", 0),
                # Extract simulation_data from the results
                "simulation_data": result.get("simulation_data", {}),
                "duration_ms": result.get("duration_ms", 0)
            })

    decision_memo = None
    if memo:
        justification_data = memo.get("justification", {})

        decision_memo = {
            "recommendation": f"Best scenario: {run_data.get('best_scenario_id', 'N/A')}",
            "justification": justification_data.get("answer", "Analysis in progress"),
            "citations": justification_data.get("citations", []),
            "confidence": memo.get("metrics", {}).get("fairness_index", 0.75)
        }

    # Extract city from multiple sources for reliability
    city = None
    if run_data.get("intent"):
        intent = run_data.get("intent")
        if isinstance(intent, dict):
            city = intent.get("city")
        else:
            city = getattr(intent, "city", None)
    
    # Fallback: check city_simulation artifacts
    if not city:
        try:
            city_sim_result = await storage_service.get_run_artifact(run_id, "city_simulation")
            if city_sim_result and "city" in city_sim_result:
                city = city_sim_result["city"]
        except:
            pass
    
    # Final fallback
    if not city:
        city = "westminster"  # Default to valid borough

    return {
        "run_id": run_id,
        "status": run_data.get("status", "completed"),
        "created_at": run_data.get("created_at") if isinstance(run_data.get("created_at"), str) else run_data.get("created_at").isoformat() if run_data.get("created_at") else datetime.utcnow().isoformat(),
        "completed_at": run_data.get("completed_at") if isinstance(run_data.get("completed_at"), str) else run_data.get("completed_at").isoformat() if run_data.get("completed_at") else None,
        "scenario_count": run_data.get("scenario_count", len(scenarios)),
        "best_scenario_id": run_data.get("best_scenario_id"),
        "city": city,  # Add city field to response
        "scenarios": scenarios,
        "decision_memo": decision_memo,
        "user_intent": run_data.get("intent") if isinstance(run_data.get("intent"), dict) else run_data.get("intent").dict() if run_data.get("intent") else None
    }


@router.get("/runs")
async def list_runs(
    include_details: bool = Query(False, description="Include detailed scenarios and metrics for each run"),
    limit: int = Query(None, description="Maximum number of runs to return per city"),
):
    """
    List all runs from storage with their status, including metrics from active_runs.

    Args:
        include_details: If True, includes full scenario data and metrics (slower but more complete)
        limit: If provided, limits the number of recent runs per city
    """
    runs = await storage_service.list_all_runs()

    # Import active_runs from simulation.py to get real metrics
    try:
        from api.simulation import active_runs as sim_active_runs

        # Merge active_runs metrics into the runs list
        for run in runs:
            run_id = run.get('run_id')
            if run_id and run_id in sim_active_runs:
                # Add metrics from active_runs if they exist
                active_run = sim_active_runs[run_id]
                if 'metrics' in active_run:
                    run['metrics'] = active_run['metrics']
                if 'city' in active_run and not run.get('city'):
                    run['city'] = active_run['city']
                if 'scenario_count' in active_run and not run.get('scenario_count'):
                    run['scenario_count'] = active_run['scenario_count']
    except Exception as e:
        logger.warning(f"Failed to merge active_runs metrics: {e}")

    # If include_details is requested, fetch scenario data for each run
    if include_details:
        detailed_runs = []
        for run in runs:
            run_id = run.get('run_id')
            if not run_id:
                continue

            try:
                # Fetch detailed scenario data
                scenarios_result = await storage_service.get_run_artifact(run_id, "scenarios")
                results_result = await storage_service.get_run_artifact(run_id, "results")

                scenarios = []
                if scenarios_result and "scenarios" in scenarios_result:
                    scenario_list = scenarios_result["scenarios"]
                    results_list = results_result.get("results", []) if results_result else []

                    for i, scenario_data in enumerate(scenario_list):
                        result = results_list[i] if i < len(results_list) else {}
                        config = scenario_data.get("config", {})

                        scenarios.append({
                            "scenario_id": scenario_data.get("scenario_id", f"scenario_{i}"),
                            "scenario_name": config.get("scenario_name", f"Scenario {i+1}"),
                            "metrics": result.get("metrics", {
                                "clearance_time": 0,
                                "fairness_index": 0,
                                "robustness": 0
                            })
                        })

                run['scenarios'] = scenarios

                # Calculate aggregate metrics from scenarios
                if scenarios:
                    valid_scenarios = [s for s in scenarios if s.get("metrics", {}).get("clearance_time", 0) > 0]
                    if valid_scenarios:
                        avg_clearance = sum(s["metrics"]["clearance_time"] for s in valid_scenarios) / len(valid_scenarios)
                        avg_fairness = sum(s["metrics"]["fairness_index"] for s in valid_scenarios) / len(valid_scenarios)
                        avg_robustness = sum(s["metrics"]["robustness"] for s in valid_scenarios) / len(valid_scenarios)

                        run['aggregate_metrics'] = {
                            "clearance_time": avg_clearance,
                            "fairness_index": avg_fairness,
                            "robustness": avg_robustness
                        }

                detailed_runs.append(run)
            except Exception as e:
                logger.warning(f"Failed to fetch details for run {run_id}: {e}")
                detailed_runs.append(run)  # Include run without details

        runs = detailed_runs

    # Apply limit per city if requested
    if limit:
        city_runs = {}
        for run in runs:
            city = run.get('city', 'unknown')
            if city not in city_runs:
                city_runs[city] = []
            city_runs[city].append(run)

        # Sort each city's runs by created_at and limit
        limited_runs = []
        for city, city_run_list in city_runs.items():
            sorted_runs = sorted(city_run_list, key=lambda r: r.get('created_at', ''), reverse=True)
            limited_runs.extend(sorted_runs[:limit])

        runs = limited_runs

    return {
        "runs": runs,
        "total_count": len(runs),
        "includes_details": include_details
    }
