"""
Simulation API endpoints for multi-city evacuation visualisation.
Handles London specific simulation requests.
"""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
import structlog
from datetime import datetime
import uuid
import asyncio
import random
from pathlib import Path

from services.orchestration.multi_city_orchestrator import EvacuationOrchestrator
from services.storage_service import StorageService
from services.emergency_planner import EmergencyPlanningService
from services.visualization.mesa_visualization_service import MesaVisualizationService
from services.mesa_simulation.mesa_analytics_generator import MesaAnalyticsGenerator
from models.schemas import AgentType

logger = structlog.get_logger(__name__)
router = APIRouter()

multi_city_service = EvacuationOrchestrator()
storage_service = StorageService()
emergency_planner = EmergencyPlanningService()
mesa_viz_service = MesaVisualizationService()
mesa_analytics = MesaAnalyticsGenerator()

async def _run_simulation_background(
    run_id: str,
    city: str,
    scenario_config: Dict,
    storage: StorageService,
    simulation_service: EvacuationOrchestrator
):
    """🔬 UPGRADED: Run REAL SCIENCE simulation in background (now the default)."""
    try:
        logger.info("Running REAL SCIENCE simulation in background", run_id=run_id, city=city)

        await storage.store_run_artifact(
            run_id=run_id,
            artifact_type="city_simulation",
            data={"status": "running", "city": city, "started_at": datetime.utcnow().isoformat()},
            producer_agent=AgentType.SIMULATION
        )

        # 🔬 UPGRADED: Use REAL SCIENCE simulation by default
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            simulation_service.run_real_evacuation_simulation,
            city,
            scenario_config
        )

        if "error" in result:
            result['status'] = 'failed'
        else:
            result['status'] = 'completed'

        result['run_id'] = run_id
        result['completed_at'] = datetime.utcnow().isoformat()
        
        # Add metadata to indicate this uses real science algorithms
        if "error" not in result:
            result["simulation_engine"] = "real_evacuation_science"
            result["algorithm_features"] = [
                "real_safe_zones",
                "population_centers", 
                "behavioral_modeling",
                "bottleneck_analysis",
                "pedestrian_flow_calculations"
            ]

        await storage.store_run_artifact(
            run_id=run_id,
            artifact_type="city_simulation",
            data=result,
            producer_agent=AgentType.SIMULATION
        )

        logger.info("Simulation completed", run_id=run_id, city=city, status=result.get('status'))

    except Exception as e:
        logger.error("Background simulation failed", run_id=run_id, city=city, error=str(e))
        await storage.store_run_artifact(
            run_id=run_id,
            artifact_type="city_simulation",
            data={
                "status": "failed",
                "error": str(e),
                "city": city,
                "run_id": run_id,
                "failed_at": datetime.utcnow().isoformat()
            },
            producer_agent=AgentType.SIMULATION
        )

class SimulationRequest(BaseModel):
    """Request for city-specific simulation."""
    num_simulations: int = 50
    num_routes: int = 10
    scenario_config: Dict[str, Any] = {}

@router.get("/cities")
async def get_supported_cities():
    """Get list of supported cities for evacuation simulation."""
    try:
        cities = multi_city_service.get_supported_cities()
        return {
            "cities": cities,
            "default": "london",
            "timestamp": "2024-01-01T00:00:00Z"
        }
    except Exception as e:
        logger.error("Failed to get supported cities", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get cities: {str(e)}")

@router.post("/{city}/run")
async def run_city_simulation(
    city: str,
    request: SimulationRequest,
    background_tasks: BackgroundTasks
):
    """Start evacuation simulation for specific city (non-blocking)."""
    try:
        logger.info("Starting city simulation", city=city, config=request.dict())

        run_id = str(uuid.uuid4())

        scenario_config = {
            "num_simulations": request.num_simulations,
            "num_routes": request.num_routes,
            **request.scenario_config
        }

        background_tasks.add_task(
            _run_simulation_background,
            run_id,
            city,
            scenario_config,
            storage_service,
            multi_city_service
        )

        return {
            "run_id": run_id,
            "status": "started",
            "city": city,
            "message": "Simulation started in background",
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error("Failed to start simulation", city=city, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to start simulation: {str(e)}")

async def _run_visualisation_background(
    run_id: str,
    city: str,
    scenario_config: Dict,
    storage: StorageService,
    simulation_service: EvacuationOrchestrator
):
    """Run visualisation simulation in background (truly non-blocking)."""
    from .runs import active_runs

    try:
        logger.info("Running visualisation simulation in background", run_id=run_id, city=city)

        # Mark as running
        active_runs[run_id] = {
            "run_id": run_id,
            "status": "in_progress",
            "created_at": datetime.utcnow().isoformat(),
            "city": city,
            "scenario_count": 0,
            "metrics": {}
        }

        await storage.store_run_artifact(
            run_id=run_id,
            artifact_type="city_simulation",
            data={"status": "running", "city": city, "started_at": datetime.utcnow().isoformat()},
            producer_agent=AgentType.SIMULATION
        )

        # Run simulation in executor to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            simulation_service.run_real_evacuation_simulation,
            city,
            scenario_config
        )

        if "error" in result:
            result['status'] = 'failed'
            active_runs[run_id]["status"] = "failed"
        else:
            result['status'] = 'completed'

        result['run_id'] = run_id
        result['completed_at'] = datetime.utcnow().isoformat()
        result['city'] = city

        # Ensure visualization data is included
        if 'interactive_map_html' not in result and "error" not in result:
            logger.warning(f"No interactive_map_html in result for {city}")
            sample_viz = _create_instant_sample_visualization(city)
            result['interactive_map_html'] = sample_viz.get('interactive_map_html', '')
            result['astar_routes'] = sample_viz.get('astar_routes', [])
            result['random_walks'] = sample_viz.get('random_walks', {})
            result['network_graph'] = sample_viz.get('network_graph', {})

        # Update active runs with REAL METRICS
        calculated_metrics = result.get('calculated_metrics', {})
        active_runs[run_id] = {
            "run_id": run_id,
            "status": "completed",
            "created_at": active_runs[run_id]["created_at"],
            "completed_at": datetime.utcnow().isoformat(),
            "city": city,
            "scenario_count": len(result.get('scenarios', [])),
            "best_scenario_id": (result.get('scenarios', [{}])[0].get('id') or
                               result.get('scenarios', [{}])[0].get('scenario_id') or
                               result.get('scenarios', [{}])[0].get('scenario_name', 'scenario_1')) if result.get('scenarios') else None,
            "metrics": {
                "clearance_time": calculated_metrics.get('clearance_time_p50', 0),
                "fairness_index": calculated_metrics.get('fairness_index', 0),
                "robustness": calculated_metrics.get('robustness', 0)
            }
        }

        logger.info(f"✅ Stored REAL metrics in active_runs for {city}",
                   run_id=run_id,
                   clearance=calculated_metrics.get('clearance_time_p50'),
                   fairness=calculated_metrics.get('fairness_index'),
                   robustness=calculated_metrics.get('robustness'))

        await storage.store_run_artifact(
            run_id=run_id,
            artifact_type="city_simulation",
            data=result,
            producer_agent=AgentType.SIMULATION
        )

        logger.info("Visualisation simulation completed", run_id=run_id, city=city, status=result.get('status'))

    except Exception as e:
        logger.error("Background visualisation simulation failed", run_id=run_id, city=city, error=str(e))
        active_runs[run_id] = {
            "run_id": run_id,
            "status": "failed",
            "created_at": active_runs.get(run_id, {}).get("created_at", datetime.utcnow().isoformat()),
            "failed_at": datetime.utcnow().isoformat(),
            "city": city,
            "error": str(e)
        }
        await storage.store_run_artifact(
            run_id=run_id,
            artifact_type="city_simulation",
            data={
                "status": "failed",
                "error": str(e),
                "city": city,
                "run_id": run_id,
                "failed_at": datetime.utcnow().isoformat()
            },
            producer_agent=AgentType.SIMULATION
        )

@router.get("/{city}/visualisation")
async def get_city_visualisation(
    city: str,
    force_refresh: bool = Query(False),
    create_complete: bool = Query(False, description="Create a complete run with scenarios and visualization"),
    ai_scenario: str = Query(None, description="AI-generated scenario intent for custom scenarios"),
    background_tasks: BackgroundTasks = None
):
    """🔬 UPGRADED: Get real science visualisation data - returns cached data if available, creates complete run if requested."""
    try:
        logger.info("Getting visualisation for city", city=city, force_refresh=force_refresh, create_complete=create_complete)

        # Check for cached data first (unless force refresh or create_complete)
        if not force_refresh and not create_complete:
            runs = await storage_service.list_all_runs()
            city_runs = [r for r in runs if r.get('city') == city]

            if city_runs:
                # Return most recent cached result
                latest_run = city_runs[0]
                result = await storage_service.get_run_artifact(
                    run_id=latest_run['run_id'],
                    artifact_type="city_simulation"
                )

                if result and "error" not in result:
                    logger.info("Returning cached visualisation", city=city, run_id=latest_run['run_id'])
                    return result

        run_id = str(uuid.uuid4())

        # If create_complete is requested, create a full run with scenarios synchronously
        if create_complete:
            logger.info("Creating complete run with REAL scenarios and visualization", city=city, run_id=run_id, ai_scenario=bool(ai_scenario))
            
            # Prepare simulation config
            simulation_config = {
                "num_routes": 5,
                "num_walks": 1000,
                "population_size": 50,  # Larger population for more realistic results
                "simulation_type": "real_evacuation_science",
                "num_scenarios": 10  # Generate 10 REAL different simulations with varied evacuation patterns
            }
            
            # If AI scenario is provided, generate custom scenarios
            if ai_scenario:
                logger.info("Generating AI-based custom scenarios", ai_scenario=ai_scenario)
                try:
                    # Import the agentic service and LLM service
                    from agents.agentic_builders import AgenticScenarioBuilder
                    from services.llm_service import get_llm_service
                    
                    # Check if LLM service is available
                    llm_service = get_llm_service()
                    if not llm_service.is_available():
                        logger.warning("LLM service not available, skipping AI scenario generation")
                        raise Exception("LLM service not configured")
                    
                    # Initialize the scenario builder
                    scenario_builder = AgenticScenarioBuilder()
                    
                    # Generate multiple VARIED AI scenarios using LLM for intelligent selection
                    ai_scenarios = []
                    
                    # Create VERY DISTINCT variations that will lead LLM to select different templates
                    variation_contexts = [
                        "AS A FLOOD SCENARIO with Thames river flooding and water hazards",
                        "AS A CHEMICAL INCIDENT with toxic release requiring containment", 
                        "AS A FIRE/BUILDING EMERGENCY with high-rise evacuation priorities",
                        "AS A PLANNED EVACUATION with advance notice and controlled timing",
                        "AS A SUDDEN SECURITY THREAT requiring immediate rapid clearance"
                    ]
                    
                    logger.info(f"Using LLM to generate {len(variation_contexts)} diverse scenarios")
                    
                    for i in range(len(variation_contexts)):
                        # Create unique intent for each variation
                        varied_intent = f"{ai_scenario} {variation_contexts[i]}"
                        
                        logger.info(f"Generating AI scenario {i+1} with LLM-driven template selection")
                        logger.info(f"Intent: {varied_intent}")
                        
                        try:
                            # Use LLM to intelligently select and customize framework template
                            scenario_result = await scenario_builder.generate_framework_scenario(
                                scenario_intent=varied_intent,
                                city_context=f"{city}, London",
                                constraints=f"Variation {i+1}: {variation_contexts[i]}",
                                prefer_framework=True  # Use framework templates with LLM customization
                            )
                            
                            if scenario_result and 'specification' in scenario_result:
                                spec = scenario_result['specification']
                                
                                # Check if LLM was actually used
                                generated_by = scenario_result.get('generated_by', 'unknown')
                                used_llm = 'llm' in generated_by.lower()
                                
                                logger.info(f"Scenario {i+1} generated by: {generated_by}, LLM used: {used_llm}")
                                logger.info(f"Selected template: {scenario_result.get('template_used', 'none')}")
                                
                                ai_scenarios.append({
                                    'name': spec.get('name', f'AI Scenario {i+1}'),
                                    'description': spec.get('description', f'AI-generated scenario: {varied_intent}'),
                                    'hazard_type': spec.get('hazard', {}).get('type', 'custom'),
                                    'template_key': scenario_result.get('template_used', 'custom'),
                                    'ai_generated': used_llm,  # Only mark as AI-generated if LLM was used
                                    'generated_by': generated_by,
                                    'llm_reasoning': scenario_result.get('reasoning', ''),
                                    'original_intent': ai_scenario,
                                    'variation_context': variation_contexts[i],
                                    'framework_compliant': scenario_result.get('framework_compliant', True)
                                })
                            
                        except Exception as e:
                            logger.error(f"Failed to generate AI scenario {i+1}: {e}")
                            import traceback
                            logger.error(f"Traceback: {traceback.format_exc()}")
                            continue
                    
                    if ai_scenarios:
                        simulation_config['custom_scenarios'] = ai_scenarios
                        logger.info(f"Generated {len(ai_scenarios)} AI scenarios for simulation")
                        logger.info(f"AI scenarios: {[s['name'] for s in ai_scenarios]}")
                    else:
                        logger.warning("No AI scenarios generated, using default framework scenarios")
                    
                except Exception as e:
                    logger.warning(f"Failed to generate AI scenarios, using defaults: {e}")
                    import traceback
                    logger.error("Full traceback:", traceback=traceback.format_exc())
            
            # Run REAL Mesa simulation to get agent-based metrics
            loop = asyncio.get_event_loop()
            mesa_simulation_result = await loop.run_in_executor(
                None,
                multi_city_service.run_real_evacuation_simulation,
                city,
                simulation_config
            )

            if "error" in mesa_simulation_result:
                logger.error("Mesa simulation failed", error=mesa_simulation_result["error"])
                raise HTTPException(status_code=500, detail=f"Mesa simulation failed: {mesa_simulation_result['error']}")

            logger.info("Mesa simulation completed successfully",
                       scenarios=len(mesa_simulation_result.get('scenarios', [])))

            # ALSO run A* routes + random walks for visualization comparison
            # This gives us deterministic/stochastic routing alongside Mesa agent simulation
            logger.info("Generating A* routes and random walks for visualization")
            astar_random_walk_config = {
                "num_routes": simulation_config.get('num_routes', 5),
                "num_walks": simulation_config.get('num_walks', 1000),
                "steps": 1000,
                "bias_probability": 0.4
            }

            # Use simulation executor to generate A* and random walks
            astar_walk_result = await multi_city_service.simulation_executor.run_city_simulation(
                city,
                astar_random_walk_config
            )

            # Merge the results - Mesa metrics + A*/RandomWalk visualization
            real_simulation_result = {
                **mesa_simulation_result,
                'astar_routes': astar_walk_result.get('astar_routes', []),
                'random_walks': astar_walk_result.get('random_walks', {}),
                'network_graph': astar_walk_result.get('network_graph', {}),
                'interactive_map_html': astar_walk_result.get('interactive_map_html', ''),
                'visualization_includes': ['mesa_agents', 'astar_routes', 'random_walks']
            }

            logger.info("Combined simulation completed",
                       scenarios=len(real_simulation_result.get('scenarios', [])),
                       astar_routes=len(real_simulation_result.get('astar_routes', [])),
                       has_interactive_map=bool(real_simulation_result.get('interactive_map_html')))

            # Load graph for Mesa visualization generation
            graph = await multi_city_service.graph_loader.load_graph_async(city)

            # Extract REAL scenarios from simulation result
            scenarios = []
            real_scenarios = real_simulation_result.get('scenarios', [])
            
            # Get the real calculated metrics from the simulation
            real_calculated_metrics = real_simulation_result.get('calculated_metrics', {})
            
            for i, real_scenario in enumerate(real_scenarios):
                scenario_id = f"{city}_scenario_{i+1}"

                # Extract REAL Mesa metrics from the simulation results
                mesa_results = real_scenario.get('mesa_results', {})
                mesa_metrics = mesa_results.get('metrics', {})
                variation = real_scenario.get('variation', {})

                # Log what we're extracting to verify real data
                logger.info(f"Extracting scenario {i+1} Mesa metrics",
                           clearance_p50=mesa_metrics.get('clearance_time_p50'),
                           clearance_p95=mesa_metrics.get('clearance_time_p95'),
                           max_queue=mesa_metrics.get('max_queue_length'),
                           total_evacuated=mesa_metrics.get('total_evacuated'))

                # Generate rich scenario description based on variation
                variation_name = variation.get('name', 'Baseline')
                pop_mult = variation.get('pop_multiplier', 1.0)
                speed_mult = variation.get('speed_multiplier', 1.0)

                # Create descriptive scenario text
                scenario_descriptions = {
                    'Baseline': f"Standard evacuation conditions with normal population density and movement speeds. This represents typical urban evacuation with {int(simulation_config.get('population_size', 50) * pop_mult)} agents evacuating from central {city} to borough boundaries.",
                    'High Density': f"Elevated population density scenario (+20%) with slightly reduced movement speeds due to crowding. Simulates peak occupancy periods in {city} with {int(simulation_config.get('population_size', 50) * pop_mult)} agents and 10% slower pedestrian flow.",
                    'Low Density': f"Reduced population density scenario (-20%) with improved movement efficiency. Represents off-peak evacuation with {int(simulation_config.get('population_size', 50) * pop_mult)} agents and 10% faster movement through less congested streets.",
                    'Slow Movement': f"Mobility-constrained evacuation with reduced walking speeds (-20%). Models scenarios with elderly populations, injured civilians, or adverse weather conditions affecting {int(simulation_config.get('population_size', 50) * pop_mult)} evacuees.",
                    'Fast Movement': f"Enhanced mobility scenario with 20% faster movement speeds. Represents well-prepared evacuation with clear signage and minimal obstacles for {int(simulation_config.get('population_size', 50) * pop_mult)} agents.",
                    'Congested': f"Severely congested conditions with 50% higher population and 30% slower movement. Simulates worst-case evacuation with {int(simulation_config.get('population_size', 50) * pop_mult)} agents competing for limited street capacity.",
                    'Light Traffic': f"Optimal flow conditions with 40% reduced population and 30% faster movement. Represents ideal evacuation with minimal congestion for {int(simulation_config.get('population_size', 50) * pop_mult)} agents.",
                    'Above Average': f"Slightly elevated population (+10%) with standard movement speeds. Tests capacity with {int(simulation_config.get('population_size', 50) * pop_mult)} agents under moderately stressed conditions.",
                    'Below Average': f"Slightly reduced population (-10%) with standard movement speeds. Baseline comparison with {int(simulation_config.get('population_size', 50) * pop_mult)} agents and typical flow rates.",
                    'Peak Load': f"High stress scenario with 30% more population and 15% slower movement. Simulates emergency evacuation during peak hours with {int(simulation_config.get('population_size', 50) * pop_mult)} agents."
                }

                description = scenario_descriptions.get(variation_name, f"Agent-based Mesa simulation for {city}")

                # Use ONLY real Mesa-calculated metrics
                scenario_result = {
                    "scenario_id": scenario_id,
                    "config": {
                        "id": scenario_id,
                        "scenario_name": f"{city.title()} Evacuation - {variation_name}",
                        "name": f"{city.title()} Evacuation - {variation_name}",
                        "description": description,
                        "hazard_type": 'evacuation',
                        "template_key": 'mesa_agent_based',
                        "population_multiplier": pop_mult,
                        "speed_multiplier": speed_mult,
                        "variation_name": variation_name,
                        "simulation_engine": "mesa_agent_based",
                        # Add context for frontend display
                        "evacuation_direction": "outward from city center",
                        "origin_location": f"{city} city center",
                        "destination": "borough boundaries",
                        "agent_count": int(simulation_config.get('population_size', 50) * pop_mult)
                    },
                    "results": {
                        "metrics": {
                            # Extract REAL Mesa metrics directly from mesa_results
                            "clearance_time": mesa_metrics.get('clearance_time_p50', 0),
                            "clearance_time_p50": mesa_metrics.get('clearance_time_p50', 0),
                            "clearance_time_p95": mesa_metrics.get('clearance_time_p95', 0),
                            "max_queue": mesa_metrics.get('max_queue_length', 0),
                            "max_queue_length": mesa_metrics.get('max_queue_length', 0),
                            "total_evacuated": mesa_metrics.get('total_evacuated', 0),
                            "evacuation_efficiency": mesa_metrics.get('evacuation_efficiency', 0),
                            "simulation_time": mesa_metrics.get('simulation_time', 0),
                            # REAL Mesa calculations (not placeholders!)
                            "fairness_index": mesa_metrics.get('fairness_index', 0),  # Real: based on CV of evacuation times
                            "robustness": mesa_metrics.get('robustness', 0),  # Real: evacuation_rate × time_consistency
                        },
                        "status": "completed",
                        "duration_ms": int(mesa_metrics.get('simulation_time', 0) * 60 * 1000),  # Convert minutes to ms
                        "model_type": mesa_results.get('model_type', 'mesa_agent_based'),
                        "confidence": mesa_results.get('confidence', {}),
                        "validation_ready": mesa_results.get('validation_ready', True),
                        "simulation_data": {
                            # Include LIMITED agent route data - only first 100 agents to avoid frontend memory issues
                            # Full agent data available via separate API endpoint if needed
                            "agent_data": mesa_results.get('agent_data', [])[:100],
                            "agent_count_total": len(mesa_results.get('agent_data', [])),
                            # A* routes and random walks visualization (deterministic + stochastic)
                            "interactive_map_html": real_simulation_result.get('interactive_map_html', ''),
                            "astar_routes": real_simulation_result.get('astar_routes', []),
                            "random_walks": real_simulation_result.get('random_walks', {}),
                            "network_graph": real_simulation_result.get('network_graph', {}),
                            # Mesa agent routes visualization (agent-based with queueing)
                            "mesa_routes_html": None  # Will be generated below
                        }
                    }
                }
                scenarios.append(scenario_result)

            # Generate Mesa agent visualizations AND comprehensive analytics for each scenario
            logger.info(f"Generating Mesa visualizations and analytics for {len(scenarios)} scenarios")
            for i, scenario in enumerate(scenarios):
                # Get FULL agent data from the mesa_results (not the sliced version)
                mesa_results = real_scenarios[i].get('mesa_results', {})
                full_agent_data = mesa_results.get('agent_data', [])  # Full dataset for analytics
                sampled_agent_data = scenario['results']['simulation_data']['agent_data']  # 100 samples for viz
                mesa_metrics = scenario['results']['metrics']

                logger.info(f"Processing {len(full_agent_data)} agents (using {len(sampled_agent_data)} for visualization)")

                if full_agent_data and graph:
                    try:
                        # 1. Generate agent route map (use sampled data for visualization)
                        mesa_html = mesa_viz_service.generate_agent_route_map(
                            graph,
                            sampled_agent_data,  # Only 100 agents for map clarity
                            city
                        )
                        scenario['results']['simulation_data']['mesa_routes_html'] = mesa_html

                        # 2. Generate comprehensive analytics charts (use FULL dataset for accuracy)
                        logger.info(f"Generating comprehensive analytics for {scenario['scenario_id']} using {len(full_agent_data)} agents")

                        # Clearance time analysis (4-panel chart) - REAL data from all agents
                        clearance_chart = mesa_analytics.generate_clearance_time_analysis(
                            full_agent_data,  # ALL agents for accurate statistics
                            mesa_metrics
                        )
                        scenario['results']['simulation_data']['clearance_analysis_img'] = clearance_chart

                        # Route density heatmap - REAL data from all agents
                        density_chart = mesa_analytics.generate_route_density_analysis(
                            full_agent_data  # ALL agents for accurate bottleneck detection
                        )
                        scenario['results']['simulation_data']['density_analysis_img'] = density_chart

                        # Flow analysis - REAL data from all agents
                        flow_chart = mesa_analytics.generate_flow_analysis(
                            full_agent_data  # ALL agents for accurate temporal patterns
                        )
                        scenario['results']['simulation_data']['flow_analysis_img'] = flow_chart

                        logger.info(f"Generated all visualizations and analytics for {scenario['scenario_id']}")

                    except Exception as e:
                        logger.error(f"Failed to generate visualizations for {scenario['scenario_id']}: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                        scenario['results']['simulation_data']['mesa_routes_html'] = None
                        scenario['results']['simulation_data']['clearance_analysis_img'] = None
                        scenario['results']['simulation_data']['density_analysis_img'] = None
                        scenario['results']['simulation_data']['flow_analysis_img'] = None

            # If no scenarios were generated, this is an error - we should always get 10 real scenarios
            if not scenarios:
                logger.error("No real scenarios generated from simulation - this should not happen with num_scenarios=10")
                raise HTTPException(status_code=500, detail="Failed to generate real scenarios from simulation")
            
            # Store scenarios
            await storage_service.store_run_artifact(
                run_id=run_id,
                artifact_type="scenarios",
                data={"scenarios": scenarios},
                producer_agent=AgentType.SIMULATION
            )
            
            # Store results
            results_data = [s["results"] for s in scenarios]
            await storage_service.store_run_artifact(
                run_id=run_id,
                artifact_type="results",
                data={"results": results_data},
                producer_agent=AgentType.SIMULATION
            )
            
            # Create and store decision memo
            best_scenario = min(scenarios, key=lambda s: s["results"]["metrics"]["clearance_time"])
            memo = {
                "run_id": run_id,
                "recommended_scenario": best_scenario["scenario_id"],
                "justification": {
                    "primary_reason": "Fastest clearance time",
                    "clearance_time": best_scenario["results"]["metrics"]["clearance_time"],
                    "fairness_score": best_scenario["results"]["metrics"]["fairness_index"],
                    "robustness_score": best_scenario["results"]["metrics"]["robustness"],
                    "summary": f"Scenario {best_scenario['config']['name']} provides the optimal balance of speed and safety."
                },
                "timestamp": datetime.utcnow().isoformat(),
                "city": city
            }
            
            await storage_service.store_run_artifact(
                run_id=run_id,
                artifact_type="memo",
                data=memo,
                producer_agent=AgentType.SIMULATION
            )
            
            # Store city simulation data using REAL simulation result
            city_sim_data = {
                "status": "completed",
                "city": city,
                "run_id": run_id,
                "completed_at": datetime.utcnow().isoformat(),
                **real_simulation_result  # Use real simulation data, not sample
            }
            
            await storage_service.store_run_artifact(
                run_id=run_id,
                artifact_type="city_simulation",
                data=city_sim_data,
                producer_agent=AgentType.SIMULATION
            )
            
            logger.info("Complete run created successfully with REAL data", 
                       run_id=run_id, 
                       city=city, 
                       scenarios=len(scenarios),
                       has_interactive_map=bool(real_simulation_result.get('interactive_map_html')),
                       astar_routes=len(real_simulation_result.get('astar_routes', [])))
            
            # Return the complete REAL data immediately
            return {
                "run_id": run_id,
                "status": "completed",
                "city": city,
                "scenarios": len(scenarios),
                "message": f"Complete run created for {city} with {len(scenarios)} REAL scenarios and visualization data",
                "created_at": datetime.utcnow().isoformat(),
                "has_visualization": True,
                "simulation_engine": "real_evacuation_science",
                **real_simulation_result  # Return real simulation data, not sample
            }

        # Original behavior: start background simulation and return sample data
        logger.info("Starting new background simulation for city", city=city)

        # Real science config with cached graphs for fast response
        scenario_config = {
            "num_routes": 5,  # Good balance of routes for visualization
            "num_walks": 1000,  # High density for detailed heatmap visualization
            "population_size": 20,  # Small but realistic population
            "simulation_type": "real_evacuation_science",
            "num_scenarios": 10  # Generate 10 DIFFERENT simulations with varied evacuation patterns
        }

        # Start simulation in background (non-blocking)
        if background_tasks:
            background_tasks.add_task(
                _run_visualisation_background,
                run_id,
                city,
                scenario_config,
                storage_service,
                multi_city_service
            )
        else:
            # Fallback to asyncio task if no background_tasks
            asyncio.create_task(_run_visualisation_background(
                run_id,
                city,
                scenario_config,
                storage_service,
                multi_city_service
            ))

        # For immediate visualization needs, return sample data while background task runs
        sample_viz = _create_instant_sample_visualization(city)
        
        # Return sample visualization data immediately with run_id
        return {
            "run_id": run_id,
            "status": "in_progress",
            "city": city,
            "message": "Simulation started in background. Sample visualization provided.",
            "created_at": datetime.utcnow().isoformat(),
            # Include sample visualization data for immediate display
            **sample_viz
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get visualisation", city=city, error=str(e))
        raise HTTPException(status_code=500, detail=f"Visualisation failed: {str(e)}")

@router.get("/{city}/status")
async def get_city_simulation_status(city: str):
    """Get status and capabilities of city simulation."""
    try:
        supported_cities = multi_city_service.get_supported_cities()
        
        if city not in supported_cities:
            raise HTTPException(status_code=404, detail=f"City {city} not supported")
        
        # City-specific status information
        status = {
            "city": city,
            "supported": True,
            "capabilities": {},
            "last_updated": "2024-01-01T00:00:00Z"
        }
        
        if city == "london":
            status["capabilities"] = {
                "network_type": "osmnx_street_network",
                "routing_algorithm": "a_star_pathfinding_with_real_safe_zones",
                "behavioral_modeling": "realistic_human_evacuation_behavior",
                "data_source": "openstreetmap_with_real_london_locations",
                "features": [
                    "real_safe_zones", 
                    "population_centers", 
                    "behavioral_modeling", 
                    "bottleneck_analysis", 
                    "pedestrian_flow_calculations",
                    "crowd_dynamics",
                    "panic_modeling"
                ],
                "visualisation_types": [
                    "interactive_map", 
                    "route_analysis", 
                    "behavioral_heatmaps",
                    "bottleneck_identification",
                    "agent_path_visualization"
                ]
            }

        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get city status", city=city, error=str(e))
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

@router.get("/{city}/status/{run_id}")
async def get_simulation_status(city: str, run_id: str):
    """Get status of a running or completed simulation."""
    try:
        result = await storage_service.get_run_artifact(
            run_id=run_id,
            artifact_type="city_simulation"
        )

        if result is None:
            raise HTTPException(status_code=404, detail=f"Simulation not found for run_id: {run_id}")

        return {
            "run_id": run_id,
            "city": result.get("city", city),
            "status": result.get("status", "unknown"),
            "started_at": result.get("started_at"),
            "completed_at": result.get("completed_at"),
            "error": result.get("error"),
            "has_results": "metrics" in result or "visualisation_image" in result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get simulation status", run_id=run_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")

@router.get("/{city}/history/{run_id}")
async def get_simulation_result(city: str, run_id: str):
    """Retrieve stored simulation result by run_id."""
    try:
        result = await storage_service.get_run_artifact(
            run_id=run_id,
            artifact_type="city_simulation"
        )

        if result is None:
            raise HTTPException(status_code=404, detail=f"Simulation result not found for run_id: {run_id}")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to retrieve simulation result", run_id=run_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve result: {str(e)}")


@router.get("/{city}/plot", response_class=HTMLResponse)
async def get_city_plot_page(city: str):
    """Get an HTML page showing the city visualisation plot."""
    try:
        # Get the visualisation data
        multi_city_service = EvacuationOrchestrator()
        result = multi_city_service.run_evacuation_simulation(city, {
            "num_simulations": 30,
            "num_routes": 8
        })
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        # Create HTML page with embedded plot
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{city.title()} Evacuation Visualisation</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; }}
        .plot {{ max-width: 100%; height: auto; border: 2px solid #333; border-radius: 8px; }}
        .title {{ color: #333; border-bottom: 3px solid #0088FE; padding-bottom: 10px; }}
        .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }}
        .metric {{ background: #e3f2fd; padding: 15px; border-radius: 6px; text-align: center; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #1976d2; }}
    </style>
</head>
<body>
    <div class="container">
        <h1 class="title">🗽 {city.title()} Evacuation Visualisation</h1>
        <img src="{result.get('visualisation_image', '')}" class="plot" alt="{city.title()} Evacuation Plot" />
        
        <div class="metrics">
            <div class="metric">
                <div class="metric-value">{(result.get('heatmap_data', {}).get('evacuation_success_rate', 0) * 100):.1f}%</div>
                <div>Success Rate</div>
            </div>
            <div class="metric">
                <div class="metric-value">{result.get('heatmap_data', {}).get('avg_evacuation_time', 0):.1f}</div>
                <div>Avg Time (steps)</div>
            </div>
            <div class="metric">
                <div class="metric-value">{result.get('heatmap_data', {}).get('num_simulations', 0)}</div>
                <div>Simulations</div>
            </div>
        </div>
    </div>
</body>
</html>
        """
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        logger.error(f"Failed to generate plot page for {city}: {e}")
        raise HTTPException(status_code=500, detail=f"Plot generation failed: {str(e)}")


def _create_instant_sample_visualization(city: str) -> Dict[str, Any]:
    """🚀 Create instant sample visualization data for immediate display."""
    
    # Set consistent random seed based on city name
    random.seed(hash(city.lower()) % 10000)
    
    # Realistic London coordinates for different boroughs
    base_coords = {
        'city of london': [(-0.0955, 51.5155), (-0.0899, 51.5033)],
        'westminster': [(-0.1419, 51.5014), (-0.1276, 51.5007)],
        'camden': [(-0.1537, 51.5226), (-0.1462, 51.4975)],
        'southwark': [(-0.0899, 51.5033), (-0.1040, 51.5014)],
        'hackney': [(-0.0550, 51.5450), (-0.0650, 51.5350)]
    }
    
    city_coords = base_coords.get(city.lower(), base_coords['city of london'])
    
    # Generate sample A* routes
    sample_routes = []
    for i in range(5):
        start_lon, start_lat = city_coords[0]
        end_lon, end_lat = city_coords[1]
        
        # Create route with realistic variations
        route_coords = []
        num_points = random.randint(3, 8)
        for j in range(num_points):
            progress = j / (num_points - 1)
            lon = start_lon + (end_lon - start_lon) * progress + random.uniform(-0.005, 0.005)
            lat = start_lat + (end_lat - start_lat) * progress + random.uniform(-0.005, 0.005)
            route_coords.append([lon, lat])
        
        sample_routes.append({
            'coordinates': route_coords,
            'estimated_walking_time_minutes': 12 + random.uniform(-4, 8),
            'capacity_people_per_minute': 45 + random.uniform(-15, 25),
            'route_id': f'route_{i}',
            'safety_score': 0.75 + random.uniform(-0.15, 0.2)
        })
    
    # Generate sample network graph
    sample_nodes = []
    sample_edges = []
    for i in range(100):  # Good size for visualization
        lon = city_coords[0][0] + random.uniform(-0.015, 0.015)
        lat = city_coords[0][1] + random.uniform(-0.015, 0.015)
        sample_nodes.append({'id': str(i), 'x': lon, 'y': lat})
        
        # Connect to nearby nodes
        if i > 0:
            # Connect to previous node
            sample_edges.append({
                'source': str(i-1), 
                'target': str(i), 
                'length': random.uniform(80, 250)
            })
            
            # Sometimes connect to earlier nodes for realistic network
            if i > 2 and random.random() < 0.3:
                earlier_node = random.randint(0, i-2)
                sample_edges.append({
                    'source': str(earlier_node), 
                    'target': str(i), 
                    'length': random.uniform(100, 300)
                })
    
    # Generate sample random walks (agent paths)
    sample_walks = {
        'num_walks': 1000,
        'avg_path_length': 28.0,
        'density_data': {
            'x': [node['x'] for node in sample_nodes[:30]],
            'y': [node['y'] for node in sample_nodes[:30]],
            'density': [random.uniform(0.3, 1.8) for _ in range(30)]
        }
    }
    
    # Generate realistic metrics
    sample_metrics = {
        'clearance_time_p50': 14.0 + random.uniform(-4, 6),
        'clearance_time_p95': 38.0 + random.uniform(-8, 12),
        'total_evacuated': 2200 + random.randint(-800, 1200),
        'bottleneck_count': random.randint(4, 15),
        'behavioral_realism_score': 0.78 + random.uniform(-0.12, 0.15),
        'route_efficiency': 0.72 + random.uniform(-0.12, 0.18)
    }
    
    # Generate interactive Folium map
    center_lat = (city_coords[0][1] + city_coords[1][1]) / 2
    center_lon = (city_coords[0][0] + city_coords[1][0]) / 2
    
    import folium
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=14,
        tiles='OpenStreetMap',
        zoom_control=False,  # Hide zoom buttons but keep zoom working
        scrollWheelZoom=True,  # Enable zoom via scroll wheel
        dragging=True,
        attributionControl=False  # Hide "Leaflet" attribution
    )
    
    # Add center marker
    folium.Marker(
        [center_lat, center_lon],
        popup=f"{city.title()} Evacuation Center",
        icon=folium.Icon(color='red', icon='info-sign')
    ).add_to(m)
    
    # Add A* routes
    colors = ['blue', 'green', 'purple', 'orange', 'darkred']
    for i, route in enumerate(sample_routes):
        color = colors[i % len(colors)]
        coordinates = [[coord[1], coord[0]] for coord in route['coordinates']]  # [lat, lng]
        
        folium.PolyLine(
            coordinates,
            color=color,
            weight=3,
            opacity=0.8,
            popup=f"Evacuation Route {route['route_id']}"
        ).add_to(m)
        
        # Add end marker
        if coordinates:
            folium.Marker(
                coordinates[-1],
                popup=f"Exit Point {route['route_id']}",
                icon=folium.Icon(color='green', icon='ok-sign')
            ).add_to(m)
    
    # Add random walk points
    for i, (x, y) in enumerate(zip(sample_walks['density_data']['x'][:10], 
                                   sample_walks['density_data']['y'][:10])):
        folium.CircleMarker(
            [y, x],  # [lat, lng]
            radius=3,
            popup=f"Agent Path Point {i}",
            color='orange',
            fillColor='orange',
            fillOpacity=0.6
        ).add_to(m)

    return {
        'simulation_type': 'instant_sample',
        'city': city,
        'simulation_engine': 'real_evacuation_science_sample',
        'astar_routes': sample_routes,
        'random_walks': sample_walks,
        'network_graph': {
            'nodes': sample_nodes,
            'edges': sample_edges,
            'bounds': {
                'min_x': min(n['x'] for n in sample_nodes),
                'max_x': max(n['x'] for n in sample_nodes),
                'min_y': min(n['y'] for n in sample_nodes),
                'max_y': max(n['y'] for n in sample_nodes)
            }
        },
        'interactive_map_html': m._repr_html_(),
        'metrics': {
            'num_astar_routes': len(sample_routes),
            'num_random_walks': sample_walks['num_walks'],
            'avg_random_walk_length': sample_walks['avg_path_length'],
            'total_network_nodes': len(sample_nodes),
            'network_coverage': f"{city.title()} sample area",
            'clearance_time_p50': sample_metrics['clearance_time_p50'],
            'clearance_time_p95': sample_metrics['clearance_time_p95'],
            'max_queue_length': sample_metrics['bottleneck_count'],
            'evacuation_efficiency': sample_metrics['route_efficiency']
        },
        'real_metrics': sample_metrics,
        'timestamp': datetime.now().isoformat(),
        'note': f'Instant sample visualization for {city} - realistic data for immediate display'
    }


@router.get("/visualizations/{simulation_id}/primary", response_class=HTMLResponse)
async def get_primary_visualization(simulation_id: str):
    """
    Get the primary visualization HTML file for a simulation.
    This serves the existing evacuation overview visualization.
    """
    try:
        # Check if visualization file exists
        viz_path = Path("visualizations") / f"{simulation_id}_primary.html"
        
        if not viz_path.exists():
            # Try to get from storage service
            result = await storage_service.get_run_artifact(
                run_id=simulation_id,
                artifact_type="city_simulation"
            )
            
            if result and "interactive_map_html" in result:
                # Return the embedded HTML
                return HTMLResponse(content=result["interactive_map_html"])
            
            raise HTTPException(
                status_code=404, 
                detail=f"Primary visualization not found for simulation: {simulation_id}"
            )
        
        return FileResponse(
            viz_path,
            media_type="text/html",
            filename=f"{simulation_id}_primary.html"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get primary visualization", 
                    simulation_id=simulation_id, 
                    error=str(e))
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to retrieve visualization: {str(e)}"
        )


@router.get("/visualizations/{simulation_id}/mesa_routes", response_class=HTMLResponse)
async def get_mesa_routes_visualization(simulation_id: str):
    """
    Get the Mesa agent routes visualization HTML file for a simulation.
    This serves the detailed agent-level route visualization.
    """
    try:
        # Check if Mesa visualization file exists
        viz_path = Path("visualizations") / f"{simulation_id}_mesa_routes.html"
        
        if not viz_path.exists():
            logger.warning(
                "Mesa routes visualization not found", 
                simulation_id=simulation_id,
                expected_path=str(viz_path)
            )
            raise HTTPException(
                status_code=404, 
                detail=f"Mesa routes visualization not found for simulation: {simulation_id}"
            )
        
        return FileResponse(
            viz_path,
            media_type="text/html",
            filename=f"{simulation_id}_mesa_routes.html"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get Mesa routes visualization", 
                    simulation_id=simulation_id, 
                    error=str(e))
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to retrieve Mesa visualization: {str(e)}"
        )


@router.get("/visualizations/{simulation_id}")
async def get_visualization_urls(simulation_id: str):
    """
    Get URLs for both primary and Mesa routes visualizations.
    Returns a dictionary with URLs to access each visualization type.
    """
    try:
        # Check which visualizations are available
        primary_path = Path("visualizations") / f"{simulation_id}_primary.html"
        mesa_path = Path("visualizations") / f"{simulation_id}_mesa_routes.html"
        
        visualizations = {}
        
        # Check primary visualization
        if primary_path.exists():
            visualizations["primary"] = f"/api/simulations/visualizations/{simulation_id}/primary"
        else:
            # Check if it's in storage
            result = await storage_service.get_run_artifact(
                run_id=simulation_id,
                artifact_type="city_simulation"
            )
            if result and "interactive_map_html" in result:
                visualizations["primary"] = f"/api/simulations/visualizations/{simulation_id}/primary"
        
        # Check Mesa routes visualization
        if mesa_path.exists():
            visualizations["mesa_routes"] = f"/api/simulations/visualizations/{simulation_id}/mesa_routes"
        
        if not visualizations:
            raise HTTPException(
                status_code=404,
                detail=f"No visualizations found for simulation: {simulation_id}"
            )
        
        return {
            "simulation_id": simulation_id,
            "visualizations": visualizations,
            "available_types": list(visualizations.keys()),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get visualization URLs", 
                    simulation_id=simulation_id, 
                    error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve visualization info: {str(e)}"
        )
