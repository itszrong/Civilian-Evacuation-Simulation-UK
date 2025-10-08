"""
Network capacity management with FIFO queues and bottleneck throughput.
Handles edge occupancy limits and node service rates for realistic congestion.
"""

import networkx as nx
from typing import Dict, Tuple, List
from collections import defaultdict, deque
import structlog

logger = structlog.get_logger(__name__)


class NetworkCapacity:
    """
    Manages capacity constraints, FIFO queues, and bottleneck throughput.
    
    Attributes:
        edge_cap: Max concurrent people on each edge (occupancy limit)
        node_service: Service rate (people/minute) for each (node, next_node) pair
        edge_load: Current number of people on each edge
        queues: FIFO queues at each node per outgoing edge
    """
    
    def __init__(self, graph: nx.MultiDiGraph, dt_min: float = 1.0):
        """
        Initialize capacity model with queueing.
        
        Args:
            graph: NetworkX graph with road network
            dt_min: Time step duration in minutes (for service rate calculation)
        """
        self.graph = graph
        self.dt_min = dt_min
        
        # Capacity constraints
        self.edge_cap: Dict[Tuple[int, int], int] = {}
        self.node_service: Dict[Tuple[int, int], float] = {}
        
        # Current state
        self.edge_load = defaultdict(int)
        self.queues = defaultdict(lambda: defaultdict(deque))  # queues[node][next_node]
        
        self._calculate_capacities()
    
    def _calculate_capacities(self):
        """
        Calculate edge capacity and node service rates.
        
        Edge capacity = spatial constraint (how many fit on the edge)
        Service rate = throughput constraint (how many per minute can enter)
        """
        # Edge capacities based on road type and geometry
        for u, v, data in self.graph.edges(data=True):
            highway = data.get('highway', 'residential')
            # Handle highway as list or string
            road_type = highway[0] if isinstance(highway, list) else highway
            width = self._get_road_width(road_type)
            length = data.get('length', 10.0)  # meters
            
            # Capacity = area * people_per_sqm
            # Using 0.5 people/sqm (loose crowd, evacuation typical)
            area = width * length
            capacity = max(1, int(area * 0.5))
            
            self.edge_cap[(u, v)] = capacity
        
        # Node service rates (bottleneck throughput)
        for u in self.graph.nodes():
            for v in self.graph.neighbors(u):
                highway = list(self.graph[u][v].values())[0].get('highway', 'residential')
                # Handle highway as list or string
                road_type = highway[0] if isinstance(highway, list) else highway
                
                # Service rate (people/minute) by road type
                # Represents "door width" or junction throughput
                service_rates = {
                    'footway': 6,      # Narrow door/path
                    'residential': 12,  # Local street
                    'secondary': 20,    # Larger road
                    'primary': 25,      # Major road
                    'motorway': 40      # Highway
                }
                
                self.node_service[(u, v)] = service_rates.get(road_type, 10)
        
        logger.info(
            f"Calculated capacities and service rates",
            num_edges=len(self.edge_cap),
            num_service_rates=len(self.node_service)
        )
    
    def _get_road_width(self, road_type: str) -> float:
        """
        Get typical road width in meters based on OSM highway type.
        
        Args:
            road_type: OSM highway tag value
            
        Returns:
            Width in meters
        """
        widths = {
            'motorway': 7.0,
            'trunk': 7.0,
            'primary': 6.0,
            'secondary': 5.0,
            'tertiary': 4.5,
            'residential': 4.0,
            'service': 3.0,
            'footway': 2.0,
            'path': 1.5
        }
        return widths.get(road_type, 4.0)
    
    def is_blocked(self, edge: Tuple[int, int], agents: List, agent) -> bool:
        """
        Check if edge is blocked by capacity.
        Simplified version for basic checking.
        
        Args:
            edge: (source, target) tuple
            agents: List of all agents
            agent: Agent attempting to move
            
        Returns:
            True if blocked
        """
        # Count agents currently on this edge
        on_edge = sum(1 for a in agents if hasattr(a, 'current_edge') and a.current_edge == edge)
        
        # Check if at capacity
        capacity = self.edge_cap.get(edge, 10)
        return on_edge >= capacity
    
    def request_admission(self, agent, u: int, v: int):
        """
        Agent at node u requests to enter edge (u,v).
        Places agent in FIFO queue for this edge.
        
        Args:
            agent: Agent requesting admission
            u: Source node
            v: Target node
        """
        q = self.queues[u][v]
        if agent.status != "queued" and agent not in q:
            q.append(agent)
            agent.status = "queued"
            logger.debug(
                f"Agent {agent.unique_id} queued at node {u} for edge ({u},{v})",
                queue_length=len(q)
            )
    
    def admit_queued(self) -> int:
        """
        Admit agents from queues onto edges (called once per time step).
        Respects both edge capacity and node service rate (bottleneck throughput).
        
        Returns:
            Number of agents admitted this time step
        """
        admitted = 0
        
        for (u, v), service_rate in self.node_service.items():
            q = self.queues[u][v]
            if not q:
                continue
            
            # How many slots remain on the edge?
            space = max(0, self.edge_cap[(u, v)] - self.edge_load[(u, v)])
            if space <= 0:
                continue
            
            # Number we can admit this tick: limited by BOTH service rate AND space
            can_admit = min(
                int(service_rate * self.dt_min),  # Bottleneck throughput
                space,                             # Physical space
                len(q)                             # Queue size
            )
            
            # Admit from front of queue (FIFO)
            for _ in range(can_admit):
                agent = q.popleft()
                
                # Place agent on edge
                agent.current_edge = (u, v)
                agent.progress_on_edge = 0.0
                agent.status = "moving"
                self.edge_load[(u, v)] += 1
                admitted += 1
                
                logger.debug(
                    f"Agent {agent.unique_id} admitted to edge ({u},{v})",
                    edge_load=self.edge_load[(u, v)],
                    edge_capacity=self.edge_cap[(u, v)]
                )
        
        return admitted
    
    def release_edge(self, edge: Tuple[int, int]):
        """
        Release occupancy when agent completes an edge.
        
        Args:
            edge: (source, target) tuple
        """
        if edge:
            self.edge_load[edge] = max(0, self.edge_load[edge] - 1)
    
    def get_queue_length(self, u: int, v: int) -> int:
        """Get current queue length at node u for edge (u,v)."""
        return len(self.queues[u][v])
    
    def get_max_queue_length(self) -> int:
        """Get maximum queue length across all queues."""
        max_len = 0
        for node_queues in self.queues.values():
            for q in node_queues.values():
                max_len = max(max_len, len(q))
        return max_len
    
    def get_total_queued(self) -> int:
        """Get total number of agents in all queues."""
        total = 0
        for node_queues in self.queues.values():
            for q in node_queues.values():
                total += len(q)
        return total
