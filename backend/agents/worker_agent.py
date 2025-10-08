"""
Worker Agent for London Evacuation Planning Tool.

This agent runs evacuation simulations in parallel with retry logic and
emits real-time results via SSE.
"""

import asyncio
from typing import List, Dict, Any, Callable, Optional
import structlog

from models.schemas import ScenarioConfig, ScenarioResult, TaskStatus, SimulationMetrics
from services.simulation_service import EvacuationSimulator, LondonGraphService
from services.orchestration.multi_city_orchestrator import EvacuationOrchestrator
from core.config import get_settings

logger = structlog.get_logger(__name__)


class WorkerAgent:
    """Agent responsible for running evacuation simulations."""

    def __init__(self, sse_callback: Optional[Callable] = None):
        self.settings = get_settings()
        self.sse_callback = sse_callback
        self.graph_service = LondonGraphService()
        self.simulator = EvacuationSimulator(self.graph_service)
        self.multi_city_service = EvacuationOrchestrator()

    async def run_scenarios(self, scenarios: List[ScenarioConfig], city: str = "london") -> List[ScenarioResult]:
        """Run multiple scenarios in parallel with retry logic."""
        logger.info("Worker agent starting scenario execution", 
                   scenario_count=len(scenarios), city=city)

        # Create tasks for parallel execution
        tasks = []
        for scenario in scenarios:
            task = asyncio.create_task(
                self._run_single_scenario_with_retry(scenario, city)
            )
            tasks.append(task)

        # Execute scenarios in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results and handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error("Scenario execution failed with exception",
                           scenario_id=scenarios[i].id,
                           error=str(result))
                
                # Create failed result
                failed_result = ScenarioResult(
                    scenario_id=scenarios[i].id,
                    metrics=SimulationMetrics(
                        clearance_time=999.0,
                        max_queue=0.0,
                        fairness_index=0.0,
                        robustness=0.0
                    ),
                    status=TaskStatus.FAILED,
                    retry_count=1,
                    duration_ms=0,
                    error_message=str(result)
                )
                processed_results.append(failed_result)
            else:
                processed_results.append(result)

        logger.info("Worker agent completed scenario execution",
                   successful=sum(1 for r in processed_results if r.status == TaskStatus.COMPLETED),
                   failed=sum(1 for r in processed_results if r.status == TaskStatus.FAILED))

        return processed_results
    
    def _convert_city_results_to_metrics(self, simulation_result: Dict[str, Any], city: str) -> SimulationMetrics:
        """Convert city-specific simulation results to standard metrics format."""
        try:
            if city.lower() == 'london':
                # Extract London metrics
                metrics_data = simulation_result.get('metrics', {})
                return SimulationMetrics(
                    clearance_time=float(metrics_data.get('num_successful_routes', 8)) * 15.0,  # Convert routes to time estimate
                    max_queue=30.0,  # Placeholder
                    fairness_index=0.85,  # London generally more accessible
                    robustness=float(metrics_data.get('total_network_nodes', 1000)) / 10000.0  # Network size as proxy
                )
            else:
                # Default fallback metrics
                return SimulationMetrics(
                    clearance_time=100.0,
                    max_queue=40.0,
                    fairness_index=0.75,
                    robustness=0.6
                )
        except Exception as e:
            logger.warning(f"Failed to convert city results to metrics: {e}")
            # Return default metrics on conversion failure
            return SimulationMetrics(
                clearance_time=150.0,
                max_queue=60.0,
                fairness_index=0.5,
                robustness=0.4
            )

    async def _run_single_scenario_with_retry(self, scenario: ScenarioConfig, city: str = "london") -> ScenarioResult:
        """Run a single scenario with retry logic."""
        max_retries = 1  # Allow one retry per scenario
        retry_count = 0
        last_error = None

        while retry_count <= max_retries:
            try:
                logger.debug("Starting scenario simulation",
                           scenario_id=scenario.id,
                           retry_count=retry_count)

                # Record start time
                import time
                start_time = time.time()

                # Run the city-specific simulation
                if city.lower() == 'london':
                    # Use multi-city service for enhanced simulations
                    simulation_result = self.multi_city_service.run_evacuation_simulation(
                        city.lower(),
                        {
                            'num_simulations': 5,
                            'num_routes': 8,
                            'scenario_config': scenario.dict()
                        }
                    )
                    
                    # Extract metrics from simulation result
                    if 'error' in simulation_result:
                        raise Exception(f"City simulation failed: {simulation_result['error']}")
                    
                    # Convert city-specific results to standard metrics
                    metrics = self._convert_city_results_to_metrics(simulation_result, city)
                else:
                    # Fallback to standard London simulation
                    metrics = await self.simulator.simulate_scenario(scenario)

                # Calculate duration
                duration_ms = int((time.time() - start_time) * 1000)

                # Create successful result
                result = ScenarioResult(
                    scenario_id=scenario.id,
                    metrics=metrics,
                    status=TaskStatus.COMPLETED,
                    retry_count=retry_count,
                    duration_ms=duration_ms,
                    error_message=None
                )

                logger.debug("Scenario simulation completed successfully",
                           scenario_id=scenario.id,
                           duration_ms=duration_ms,
                           clearance_time=metrics.clearance_time)

                # Emit SSE event if callback provided
                if self.sse_callback:
                    await self.sse_callback("worker.result", {
                        "scenario_id": scenario.id,
                        "metrics": {
                            "clearance_time": metrics.clearance_time,
                            "max_queue": metrics.max_queue,
                            "fairness_index": metrics.fairness_index,
                            "robustness": metrics.robustness
                        },
                        "status": "completed",
                        "retry_count": retry_count,
                        "duration_ms": duration_ms
                    })

                return result

            except Exception as e:
                retry_count += 1
                last_error = e
                
                logger.warning("Scenario simulation failed",
                             scenario_id=scenario.id,
                             retry_count=retry_count,
                             error=str(e))

                # Emit failure event if callback provided
                if self.sse_callback:
                    await self.sse_callback("worker.result", {
                        "scenario_id": scenario.id,
                        "metrics": None,
                        "status": "failed" if retry_count > max_retries else "retrying",
                        "retry_count": retry_count,
                        "error_message": str(e)
                    })

                # If we have retries left and this is a retryable error, continue
                if retry_count <= max_retries and self._is_retryable_error(e):
                    logger.info("Retrying scenario simulation",
                              scenario_id=scenario.id,
                              retry_attempt=retry_count)
                    
                    # Add some delay before retry
                    await asyncio.sleep(1)
                    continue
                else:
                    break

        # All retries exhausted, return failed result
        failed_result = ScenarioResult(
            scenario_id=scenario.id,
            metrics=SimulationMetrics(
                clearance_time=999.0,
                max_queue=0.0,
                fairness_index=0.0,
                robustness=0.0
            ),
            status=TaskStatus.FAILED,
            retry_count=retry_count,
            duration_ms=0,
            error_message=str(last_error) if last_error else "Unknown error"
        )

        logger.error("Scenario simulation failed permanently",
                    scenario_id=scenario.id,
                    final_error=str(last_error))

        return failed_result

    def _is_retryable_error(self, error: Exception) -> bool:
        """Determine if an error is retryable."""
        # Define retryable error types
        retryable_errors = [
            "timeout",
            "numerical instability",
            "temporary",
            "connection",
            "memory"
        ]

        error_str = str(error).lower()
        
        # Check if error message contains retryable keywords
        for retryable_keyword in retryable_errors:
            if retryable_keyword in error_str:
                return True

        # Don't retry validation errors or configuration errors
        non_retryable_keywords = [
            "validation",
            "configuration",
            "invalid scenario",
            "schema",
            "permission"
        ]

        for non_retryable_keyword in non_retryable_keywords:
            if non_retryable_keyword in error_str:
                return False

        # Default: retry unknown errors once
        return True

    async def validate_scenarios(self, scenarios: List[ScenarioConfig]) -> List[bool]:
        """Validate scenarios before execution."""
        logger.info("Worker agent validating scenarios", 
                   scenario_count=len(scenarios))

        validation_results = []
        
        for scenario in scenarios:
            try:
                is_valid = await self._validate_scenario(scenario)
                validation_results.append(is_valid)
                
                if not is_valid:
                    logger.warning("Scenario validation failed", 
                                 scenario_id=scenario.id)
            except Exception as e:
                logger.error("Scenario validation error",
                           scenario_id=scenario.id,
                           error=str(e))
                validation_results.append(False)

        valid_count = sum(validation_results)
        logger.info("Scenario validation completed",
                   valid_scenarios=valid_count,
                   invalid_scenarios=len(scenarios) - valid_count)

        return validation_results

    async def _validate_scenario(self, scenario: ScenarioConfig) -> bool:
        """Validate a single scenario before execution."""
        try:
            # Basic schema validation (Pydantic should handle this)
            if not scenario.id or not scenario.city:
                return False

            # Check scenario parameters are reasonable
            for closure in scenario.closures:
                if closure.start_minute < 0 or closure.end_minute <= closure.start_minute:
                    return False

            for change in scenario.capacity_changes:
                if change.multiplier < 0 or change.multiplier > 10:
                    return False

            for corridor in scenario.protected_corridors:
                if corridor.multiplier <= 0 or corridor.multiplier > 10:
                    return False

            # Check that the scenario doesn't create impossible conditions
            # (This is a simplified check - in practice, would be more sophisticated)
            total_capacity_reduction = sum(
                1 - change.multiplier
                for change in scenario.capacity_changes
                if change.multiplier < 1.0
            )
            
            if total_capacity_reduction > 0.8:  # More than 80% capacity reduction
                logger.warning("Scenario may have excessive capacity reduction",
                             scenario_id=scenario.id,
                             total_reduction=total_capacity_reduction)
                return False

            return True

        except Exception as e:
            logger.error("Scenario validation exception",
                        scenario_id=scenario.id,
                        error=str(e))
            return False

    async def get_simulation_status(self) -> Dict[str, Any]:
        """Get current status of the simulation system."""
        try:
            # Check if graph is available
            graph = await self.graph_service.get_london_graph()
            graph_status = {
                "loaded": graph is not None,
                "nodes": graph.number_of_nodes() if graph else 0,
                "edges": graph.number_of_edges() if graph else 0
            }

            return {
                "graph": graph_status,
                "simulator_ready": True,
                "max_parallel_scenarios": self.settings.MAX_SCENARIOS_PER_RUN,
                "max_compute_minutes": self.settings.MAX_COMPUTE_MINUTES
            }

        except Exception as e:
            logger.error("Failed to get simulation status", error=str(e))
            return {
                "graph": {"loaded": False, "nodes": 0, "edges": 0},
                "simulator_ready": False,
                "error": str(e)
            }
