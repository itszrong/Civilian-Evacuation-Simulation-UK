"""
Mesa Simulation Executor Service.
Integrates Mesa-based simulation with existing service architecture.
"""

from typing import Dict, Any, List
import networkx as nx
import structlog
import random
import numpy as np

from .model import EvacuationModel

logger = structlog.get_logger(__name__)


class MesaSimulationExecutor:
    """
    Service that executes Mesa-based evacuation simulations.
    Integrates with existing graph loading and routing services.
    """
    
    def __init__(self, graph_loader=None, routing_service=None):
        """
        Initialize Mesa executor.
        
        Args:
            graph_loader: Service for loading NetworkX graphs
            routing_service: Service for calculating A* routes
        """
        self.graph_loader = graph_loader
        self.routing_service = routing_service
    
    async def run_simulation(
        self,
        scenario: Dict[str, Any],
        graph: nx.MultiDiGraph,
        duration_minutes: float = 360,
        time_step_min: float = 1.0,
        num_agents: int = 1000
    ) -> Dict[str, Any]:
        """
        Run Mesa-based evacuation simulation.
        
        Args:
            scenario: Scenario configuration dict
            graph: NetworkX graph (already loaded)
            duration_minutes: Simulation duration
            time_step_min: Time step size in minutes
            num_agents: Number of evacuating agents
            
        Returns:
            Simulation results dictionary
        """
        logger.info(
            f"Starting Mesa simulation",
            scenario=scenario.get('name'),
            num_agents=num_agents
        )
        
        try:
            # Generate agent configurations
            agents_config = self._generate_agents(
                graph=graph,
                num_agents=num_agents,
                scenario=scenario
            )
            
            if not agents_config:
                logger.error("No valid agents generated for simulation")
                return {
                    "scenario_name": scenario.get('name'),
                    "metrics": {
                        "clearance_time_p50": None,
                        "clearance_time_p95": None,
                        "max_queue_length": 0,
                        "evacuation_efficiency": 0,
                        "total_evacuated": 0,
                        "simulation_time": 0
                    },
                    "error": "No valid agents generated"
                }
            
            logger.info(f"Generated {len(agents_config)} agents for simulation")
            
            # Store agent configs for visualization
            self._agents_config = agents_config
            
            # Create Mesa model
            model = EvacuationModel(
                graph=graph,
                agents_config=agents_config,
                time_step_min=time_step_min,
                scenario_name=scenario.get('name', 'default')
            )
            
            # Run simulation
            results = model.run(duration_minutes)
            
            logger.info(f"Mesa simulation completed", 
                       clearance_p50=results.get('clearance_time_p50'),
                       total_evacuated=results.get('total_evacuated'))
            
            # Post-process results to match existing schema
            formatted_results = self._format_results(results, scenario)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Mesa simulation failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Return error result
            return {
                "scenario_name": scenario.get('name'),
                "metrics": {
                    "clearance_time_p50": None,
                    "clearance_time_p95": None,
                    "max_queue_length": 0,
                    "evacuation_efficiency": 0,
                    "total_evacuated": 0,
                    "simulation_time": 0
                },
                "error": str(e)
            }
    
    def _generate_agents(
        self,
        graph: nx.MultiDiGraph,
        num_agents: int,
        scenario: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate agent configurations from scenario.
        All agents start from city center and evacuate outward to borough boundaries.
        
        Args:
            graph: Network graph
            num_agents: How many agents to create
            scenario: Scenario configuration
            
        Returns:
            List of agent config dicts
        """
        agents_config = []
        
        # Find city center node (node with highest betweenness centrality)
        logger.info("Finding city center node...")
        all_nodes = list(graph.nodes())
        
        # Use degree centrality as a faster approximation of center
        # (betweenness centrality is expensive for large graphs)
        try:
            centrality = nx.degree_centrality(graph)
            center_node = max(centrality, key=centrality.get)
            logger.info(f"Selected center node: {center_node} with centrality {centrality[center_node]:.4f}")
        except Exception as e:
            logger.warning(f"Could not calculate centrality: {e}, using random center")
            center_node = random.choice(all_nodes)
        
        # Get boundary nodes (nodes with low degree, likely at edges)
        # EXCLUDE the center node from destinations
        node_degrees = dict(graph.degree())
        avg_degree = np.mean(list(node_degrees.values()))
        boundary_nodes = [node for node, degree in node_degrees.items() 
                         if degree < avg_degree * 0.5 and node != center_node]
        
        # If not enough boundary nodes, use random peripheral nodes
        if len(boundary_nodes) < 100:
            # Sort nodes by distance from center
            try:
                lengths = nx.single_source_dijkstra_path_length(graph, center_node, weight='length')
                sorted_nodes = sorted(lengths.items(), key=lambda x: x[1], reverse=True)
                # Take top 20% most distant nodes as destinations, excluding center
                num_destinations = max(100, len(sorted_nodes) // 5)
                destination_nodes = [node for node, dist in sorted_nodes[:num_destinations] 
                                    if node != center_node]
            except Exception:
                # Random sample, excluding center
                available_nodes = [n for n in all_nodes if n != center_node]
                destination_nodes = random.sample(available_nodes, min(200, len(available_nodes)))
        else:
            destination_nodes = boundary_nodes
        
        logger.info(f"Using {len(destination_nodes)} destination nodes around boundary")
        
        # Generate agents
        for i in range(num_agents):
            # All agents start from center
            origin = center_node
            
            # Pick random destination on boundary (must be different from origin)
            destination = random.choice(destination_nodes)
            
            # Skip if destination is same as origin
            if destination == origin:
                logger.debug(f"Destination same as origin for agent {i}, skipping")
                continue
            
            # Calculate route using A* routing
            try:
                route = nx.shortest_path(
                    graph,
                    origin,
                    destination,
                    weight='length'
                )

                # Verify route is valid (has more than just origin)
                if len(route) < 2:
                    logger.debug(f"Route too short for agent {i}, skipping")
                    continue

                # Remove the origin from the route since agent is already there
                # Route should be [next_node, node2, ..., destination]
                route = route[1:]
                    
            except nx.NetworkXNoPath:
                # Skip if no path exists
                logger.debug(f"No path from center to {destination}, skipping agent {i}")
                continue
            except Exception as e:
                logger.warning(f"Error calculating route for agent {i}: {e}")
                continue
            
            # Assign parameters with realistic variation
            # Apply speed_multiplier from scenario variation
            base_speed = np.random.normal(1.2, 0.2)  # m/s, some variation
            speed_multiplier = scenario.get('speed_multiplier', 1.0)
            speed = base_speed * speed_multiplier
            speed = max(0.5, min(2.5, speed))   # Clamp to reasonable range

            # Start times: phased evacuation with exponential distribution
            start_time = np.random.exponential(5.0)  # Minutes
            start_time = max(0.0, min(30.0, start_time))  # Cap at 30 minutes
            
            agents_config.append({
                'unique_id': i,
                'current_node': origin,
                'target_node': destination,
                'route': route,
                'speed': speed,
                'start_time': start_time
            })
        
        logger.info(
            f"Generated {len(agents_config)} agents with valid routes",
            requested=num_agents,
            success_rate=len(agents_config)/num_agents if num_agents > 0 else 0
        )
        
        return agents_config
    
    def _format_results(
        self,
        results: Dict[str, Any],
        scenario: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Format Mesa results to match existing simulation result schema.

        Args:
            results: Raw results from Mesa simulation (includes agent_results)
            scenario: Original scenario config

        Returns:
            Formatted results matching existing schema
        """
        # Use REAL agent results from Mesa simulation (includes evacuation_time!)
        # NOT the initial config - we need actual simulation outcomes
        agent_data = results.get('agent_results', [])

        if not agent_data:
            logger.warning("No agent_results in Mesa output, falling back to initial config")
            agent_data = self._agents_config if hasattr(self, '_agents_config') else []

        logger.info(f"Including {len(agent_data)} agents with REAL evacuation results")

        return {
            "scenario_name": scenario.get('name'),
            "metrics": {
                "clearance_time_p50": results.get('clearance_time_p50'),
                "clearance_time_p95": results.get('clearance_time_p95'),
                "max_queue_length": results.get('max_queue_length'),
                "evacuation_efficiency": results.get('evacuation_rate', 0) * 100,
                "total_evacuated": results.get('total_evacuated'),
                "simulation_time": results.get('simulation_time')
            },
            "confidence": {
                "clearance_time_p50": "MEDIUM",  # Real simulation, not estimate
                "clearance_time_p95": "MEDIUM",
                "max_queue_length": "MEDIUM"
            },
            "model_type": "mesa_agent_based",
            "validation_ready": True,
            "agent_data": agent_data,  # Include full agent configs with routes
            # Note: raw_results removed to avoid DataFrame serialization issues
            "simulation_summary": {
                "total_evacuated": results.get('total_evacuated', 0),
                "simulation_time": results.get('simulation_time', 0),
                "evacuation_rate": results.get('evacuation_rate', 0)
            }
        }
