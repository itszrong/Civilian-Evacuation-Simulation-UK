"""
Evacuation Agent for Mesa-based simulation.
Each agent represents one person evacuating.
"""

from mesa import Agent
from typing import List, Tuple, Optional
import structlog

logger = structlog.get_logger(__name__)


class EvacuationAgent(Agent):
    """
    Mesa Agent representing one evacuating person.
    
    Attributes:
        unique_id: Agent ID
        model: Reference to EvacuationModel
        current_node: Current location (NetworkX node ID)
        target_node: Evacuation destination
        route: List of nodes to traverse (from A* algorithm)
        speed: Walking speed (m/s)
        start_time: When evacuation starts (minutes)
        status: 'waiting' | 'moving' | 'queued' | 'evacuated'
        progress_on_edge: 0.0-1.0, progress along current edge
        current_edge: (node1, node2) tuple or None
    """
    
    def __init__(
        self,
        unique_id: int,
        model,
        current_node: int,
        target_node: int,
        route: List[int],
        speed: float = 1.2,
        start_time: float = 0.0
    ):
        """
        Initialize evacuation agent.
        
        Args:
            unique_id: Unique agent identifier
            model: EvacuationModel instance
            current_node: Starting node in network
            target_node: Destination node
            route: Pre-calculated route (list of node IDs)
            speed: Walking speed in m/s (default 1.2 m/s)
            start_time: When to start evacuating (minutes)
        """
        super().__init__(model)
        self.unique_id = unique_id
        self.current_node = current_node
        self.target_node = target_node
        self._route_list = list(route)  # Keep as list for popping
        self.speed = speed
        self.start_time = start_time
        self.status = "waiting"
        self.progress_on_edge = 0.0
        self.current_edge: Optional[Tuple[int, int]] = None
        self.wait_start_time: Optional[float] = None
        self.evacuation_time: Optional[float] = None  # Track when evacuated
    
    @property
    def route(self):
        """Get current route as list."""
        return self._route_list
        
    def step(self):
        """
        Called each time step by Mesa scheduler.
        Implements agent movement logic.
        """
        # Check if it's time to start
        if self.status == "waiting":
            if self.model.current_time >= self.start_time:
                self.status = "moving"
                logger.debug(
                    f"Agent {self.unique_id} starting evacuation",
                    time=self.model.current_time
                )
            else:
                return  # Not time yet
        
        # Already evacuated
        if self.status == "evacuated":
            return
        
        # No route left - reached destination
        if not self.route:
            if self.status != "evacuated":
                self.status = "evacuated"
                self.evacuation_time = self.model.current_time
                # Changed to debug to avoid 50k log messages
                logger.debug(
                    f"Agent {self.unique_id} evacuated",
                    time=self.model.current_time
                )
            return
        
        # Try to move
        if self.status in ["moving", "queued"]:
            self._attempt_movement()
    
    def _attempt_movement(self):
        """Attempt to move along route, handling capacity constraints."""
        next_node = self.route[0]
        edge = (self.current_node, next_node)
        
        # Check capacity constraints
        if self.model.is_capacity_blocked(edge, self):
            if self.status != "queued":
                self.status = "queued"
                self.wait_start_time = self.model.current_time
                logger.debug(
                    f"Agent {self.unique_id} queued at node {self.current_node}",
                    time=self.model.current_time
                )
            return  # Must wait
        
        # Capacity available - move
        if self.status == "queued":
            self.status = "moving"
            logger.debug(
                f"Agent {self.unique_id} resumed moving",
                wait_time=self.model.current_time - self.wait_start_time
            )
        
        # Calculate movement this time step
        speed_m_per_min = self.speed * 60.0  # Convert m/s to m/min
        distance_can_travel = speed_m_per_min * self.model.time_step_min
        
        # Get edge length - check if edge exists
        if next_node not in self.model.graph[self.current_node]:
            # Reached edge of borough - successfully evacuated!
            logger.debug(
                f"Agent {self.unique_id} reached boundary (no edge from {self.current_node} to {next_node}) - evacuated!",
                time=self.model.current_time
            )
            self.status = "evacuated"
            self.evacuation_time = self.model.current_time
            return
        
        edge_data = self.model.graph[self.current_node][next_node]
        # Handle both single edge and multi-edge cases
        if isinstance(edge_data, dict):
            edge_length = edge_data.get("length", 100.0)  # Default if missing
        else:
            edge_length = edge_data[0].get("length", 100.0)  # Multi-edge, use first
        
        distance_remaining = (1.0 - self.progress_on_edge) * edge_length
        
        if distance_can_travel >= distance_remaining:
            # Can reach next node this step
            self.current_node = next_node
            self.route.pop(0)
            self.progress_on_edge = 0.0
            self.current_edge = None
            
            # Check if finished
            if not self.route:
                self.status = "evacuated"
                self.evacuation_time = self.model.current_time
        else:
            # Partial progress along edge
            self.progress_on_edge += distance_can_travel / edge_length
            self.current_edge = edge
    
    def advance(self):
        """
        Called after all agents have stepped (if using SimultaneousActivation).
        Use for any post-step bookkeeping.
        """
        pass
