"""
Evacuation Model for Mesa-based simulation.
Coordinates all agents and manages simulation state.
"""

from mesa import Model
from mesa import DataCollector
from typing import Dict, List, Any, Tuple
import networkx as nx
import structlog
import logging

from .agents import EvacuationAgent
from .capacity import NetworkCapacity

logger = structlog.get_logger(__name__)

# Suppress Mesa's verbose timestep logging - only show warnings/errors
logging.getLogger('mesa.model').setLevel(logging.WARNING)
logging.getLogger('MESA.mesa.model').setLevel(logging.WARNING)


class EvacuationModel(Model):
    """
    Mesa Model for evacuation simulation.
    
    Manages agents, time-stepping, capacity constraints, and data collection.
    """
    
    def __init__(
        self,
        graph: nx.MultiDiGraph,
        agents_config: List[Dict[str, Any]],
        time_step_min: float = 1.0,
        scenario_name: str = "default"
    ):
        """
        Initialize evacuation model.
        
        Args:
            graph: NetworkX graph (from existing graph_loader_service)
            agents_config: List of dicts with agent parameters
                [{
                    'unique_id': int,
                    'current_node': int,
                    'target_node': int,
                    'route': List[int],
                    'speed': float,
                    'start_time': float
                }, ...]
            time_step_min: Time step duration in minutes
            scenario_name: Scenario identifier for logging
        """
        super().__init__()
        
        self.graph = graph
        self.time_step_min = time_step_min
        self.scenario_name = scenario_name
        self.current_time = 0.0
        
        # Initialize capacity constraints
        self.capacity = NetworkCapacity(graph)
        
        # Initialize agents list for evacuation (Mesa 3.x uses 'agents' internally)
        self.evacuation_agents = []
        
        # Create agents from config
        for config in agents_config:
            agent = EvacuationAgent(
                unique_id=config['unique_id'],
                model=self,
                current_node=config['current_node'],
                target_node=config['target_node'],
                route=config['route'],
                speed=config.get('speed', 1.2),
                start_time=config.get('start_time', 0.0)
            )
            self.evacuation_agents.append(agent)
        
        logger.info(
            f"Initialized evacuation model",
            scenario=scenario_name,
            num_agents=len(agents_config),
            time_step=time_step_min
        )
        
        # Setup data collection
        self.datacollector = DataCollector(
            model_reporters={
                "evacuated_count": self._count_evacuated,
                "moving_count": self._count_moving,
                "queued_count": self._count_queued,
                "max_queue_length": self._max_queue_length,
                "current_time": lambda m: m.current_time
            },
            agent_reporters={
                "status": "status",
                "current_node": "current_node",
                "wait_time": lambda a: (
                    a.model.current_time - a.wait_start_time
                    if a.status == "queued" and a.wait_start_time else 0
                )
            }
        )
    
    def is_capacity_blocked(
        self,
        edge: Tuple[int, int],
        agent: EvacuationAgent
    ) -> bool:
        """
        Check if edge/node is over capacity.
        
        Args:
            edge: (source_node, target_node) tuple
            agent: Agent attempting to move
            
        Returns:
            True if blocked by capacity constraints
        """
        return self.capacity.is_blocked(edge, self.evacuation_agents, agent)
    
    def step(self):
        """Run one time step of the simulation."""
        # Collect data before step
        self.datacollector.collect(self)
        
        # Step all agents manually
        for agent in self.evacuation_agents:
            agent.step()
        
        # Increment time
        self.current_time += self.time_step_min

        # Log progress periodically (reduced frequency for cleaner logs)
        if int(self.current_time) % 30 == 0:  # Every 30 minutes
            logger.info(
                f"Simulation progress",
                scenario=self.scenario_name,
                time=self.current_time,
                evacuated=self._count_evacuated(),
                queued=self._count_queued()
            )
    
    def run(self, duration_minutes: float) -> Dict[str, Any]:
        """
        Run simulation for specified duration.
        
        Args:
            duration_minutes: How long to simulate
            
        Returns:
            Dictionary with simulation results and metrics
        """
        logger.info(
            f"Starting evacuation simulation",
            scenario=self.scenario_name,
            duration=duration_minutes,
            num_agents=len(self.evacuation_agents)
        )
        
        while self.current_time < duration_minutes:
            self.step()
            
            # Early termination if all evacuated
            if self._count_evacuated() == len(self.evacuation_agents):
                logger.info(
                    f"All agents evacuated",
                    time=self.current_time
                )
                break
        
        # Extract results
        results = self._compile_results()
        
        logger.info(
            f"Simulation complete",
            scenario=self.scenario_name,
            final_time=self.current_time,
            total_evacuated=results.get('total_evacuated'),
            clearance_p50=results.get('clearance_time_p50'),
            max_queue=results.get('max_queue_length')
        )
        
        return results
    
    def _compile_results(self) -> Dict[str, Any]:
        """Compile simulation results into metrics dictionary."""
        model_data = self.datacollector.get_model_vars_dataframe()
        agent_data = self.datacollector.get_agent_vars_dataframe()

        # Calculate clearance times from actual agent evacuation times
        evacuated_times = []
        for agent in self.evacuation_agents:
            if agent.status == "evacuated" and hasattr(agent, 'evacuation_time') and agent.evacuation_time is not None:
                evacuated_times.append(agent.evacuation_time)

        # Calculate percentiles
        import numpy as np
        if evacuated_times:
            clearance_p50 = float(np.percentile(evacuated_times, 50))
            clearance_p95 = float(np.percentile(evacuated_times, 95))

            # Calculate REAL fairness - Coefficient of Variation (lower is more fair)
            # CV = std_dev / mean, then convert to 0-1 scale where 1 is most fair
            mean_time = float(np.mean(evacuated_times))
            std_time = float(np.std(evacuated_times))
            cv = std_time / mean_time if mean_time > 0 else 1.0
            # Convert to fairness score: 0-1 where 1 is perfectly fair (no variation)
            fairness_index = max(0.0, min(1.0, 1.0 / (1.0 + cv)))

            # Calculate REAL robustness - Success rate × Consistency
            # High robustness = many agents evacuated + low variance in times
            evacuation_rate = self._count_evacuated() / len(self.evacuation_agents)
            time_consistency = 1.0 - min(1.0, cv)  # Lower CV = higher consistency
            robustness = float(evacuation_rate * time_consistency)
        else:
            # If no agents evacuated, use simulation time as fallback
            logger.warning(f"No agents evacuated in simulation {self.scenario_name}")
            clearance_p50 = self.current_time if self.current_time > 0 else 60.0  # Default fallback
            clearance_p95 = self.current_time * 1.5 if self.current_time > 0 else 90.0
            fairness_index = 0.0  # No fairness if nobody evacuated
            robustness = 0.0  # No robustness if nobody evacuated
        
        # Extract queue metrics with error handling
        if not model_data.empty and "max_queue_length" in model_data.columns:
            max_queue = int(model_data["max_queue_length"].max())
            avg_queue = float(model_data["max_queue_length"].mean())
        else:
            max_queue = 0
            avg_queue = 0.0
        
        # Extract per-agent results for comprehensive analytics
        agent_results = []
        for agent in self.evacuation_agents:
            agent_results.append({
                'unique_id': agent.unique_id,
                'current_node': agent.current_node,
                'target_node': agent.target_node,
                'route': agent.route,  # Full route for density analysis
                'speed': agent.speed,
                'start_time': agent.start_time,
                'evacuation_time': agent.evacuation_time,  # CRITICAL: Actual completion time
                'status': agent.status,  # evacuated, moving, queued, waiting
            })

        return {
            "clearance_time_p50": clearance_p50,
            "clearance_time_p95": clearance_p95,
            "max_queue_length": max_queue,
            "avg_queue_length": avg_queue,
            "total_evacuated": self._count_evacuated(),
            "total_agents": len(self.evacuation_agents),
            "evacuation_rate": self._count_evacuated() / len(self.evacuation_agents),
            "simulation_time": self.current_time,
            "fairness_index": fairness_index,  # Real Mesa calculation
            "robustness": robustness,  # Real Mesa calculation
            # Convert DataFrames to JSON-serializable format
            "model_data_summary": {
                "final_evacuated": int(model_data["evacuated_count"].iloc[-1]) if not model_data.empty else 0,
                "final_queued": int(model_data["queued_count"].iloc[-1]) if not model_data.empty else 0,
                "peak_queue": int(model_data["max_queue_length"].max()) if not model_data.empty else 0
            },
            "agent_summary": {
                "total_agents": len(self.evacuation_agents),
                "evacuated_count": self._count_evacuated(),
                "moving_count": self._count_moving(),
                "queued_count": self._count_queued()
            },
            # REAL per-agent results for comprehensive analytics
            "agent_results": agent_results
        }
    
    # Helper methods for data collection
    def _count_evacuated(self) -> int:
        return sum(1 for a in self.evacuation_agents if a.status == "evacuated")
    
    def _count_moving(self) -> int:
        return sum(1 for a in self.evacuation_agents if a.status == "moving")
    
    def _count_queued(self) -> int:
        return sum(1 for a in self.evacuation_agents if a.status == "queued")
    
    def _max_queue_length(self) -> int:
        # Count agents queued at each node
        from collections import Counter
        queued_at_nodes = Counter(
            a.current_node for a in self.evacuation_agents if a.status == "queued"
        )
        return max(queued_at_nodes.values()) if queued_at_nodes else 0
