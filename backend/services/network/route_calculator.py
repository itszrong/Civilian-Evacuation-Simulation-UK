"""
Stateless Route Calculator Service

Calculates optimal evacuation routes using various algorithms.
All operations are stateless - graph and parameters passed as arguments.
"""

from typing import List, Tuple, Optional, Any, Callable, Dict
import structlog

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    nx = None

logger = structlog.get_logger(__name__)


class RouteCalculatorService:
    """
    Stateless service for calculating evacuation routes.

    All methods are pure functions that take graph as parameter.
    """

    @staticmethod
    def calculate_shortest_path(
        graph: Any,
        start_node: Any,
        end_node: Any,
        weight: str = 'length'
    ) -> Optional[List[Any]]:
        """
        Calculate shortest path between two nodes. Pure function.

        Args:
            graph: NetworkX graph
            start_node: Starting node ID
            end_node: Target node ID
            weight: Edge attribute to use as weight

        Returns:
            List of node IDs forming the path, or None if no path exists
        """
        if not NETWORKX_AVAILABLE or graph is None:
            return None

        try:
            route = nx.shortest_path(graph, start_node, end_node, weight=weight)
            return route
        except nx.NetworkXNoPath:
            logger.warning(f"No path found between {start_node} and {end_node}")
            return None
        except Exception as e:
            logger.error(f"Route calculation failed: {e}")
            return None

    @staticmethod
    def calculate_evacuation_route(
        graph: Any,
        start_node: Any,
        end_node: Any,
        cost_function: Optional[Callable] = None
    ) -> Optional[List[Any]]:
        """
        Calculate optimal evacuation route with custom cost function. Pure function.

        Args:
            graph: NetworkX graph
            start_node: Starting node ID
            end_node: Target node ID
            cost_function: Optional custom cost function(u, v, edge_data) -> float

        Returns:
            List of node IDs forming the route, or None if no path exists
        """
        if not NETWORKX_AVAILABLE or graph is None:
            return None

        try:
            if cost_function:
                # Use custom cost function
                route = nx.shortest_path(
                    graph,
                    start_node,
                    end_node,
                    weight=lambda u, v, d: cost_function(u, v, d, graph)
                )
            else:
                # Use default length-based routing
                route = nx.shortest_path(graph, start_node, end_node, weight='length')

            return route
        except nx.NetworkXNoPath:
            logger.warning(f"No evacuation route found between {start_node} and {end_node}")
            return None
        except Exception as e:
            logger.error(f"Evacuation route calculation failed: {e}")
            return None

    @staticmethod
    def calculate_distance(
        graph: Any,
        start_node: Any,
        end_node: Any,
        weight: str = 'length'
    ) -> float:
        """
        Calculate shortest path distance between nodes. Pure function.

        Args:
            graph: NetworkX graph
            start_node: Starting node ID
            end_node: Target node ID
            weight: Edge attribute to use as weight

        Returns:
            Distance in meters (or specified units), or infinity if no path
        """
        if not NETWORKX_AVAILABLE or graph is None:
            return float('inf')

        try:
            distance = nx.shortest_path_length(graph, start_node, end_node, weight=weight)
            return distance
        except (nx.NetworkXNoPath, Exception):
            return float('inf')

    @staticmethod
    def calculate_route_length(graph: Any, route: List[Any]) -> float:
        """
        Calculate total length of a route. Pure function.

        Args:
            graph: NetworkX graph
            route: List of node IDs

        Returns:
            Total route length in meters
        """
        if not NETWORKX_AVAILABLE or graph is None or len(route) < 2:
            return 0.0

        total_length = 0.0
        for i in range(len(route) - 1):
            u, v = route[i], route[i + 1]
            if graph.has_edge(u, v):
                edge_data = graph.get_edge_data(u, v)
                if isinstance(edge_data, dict):
                    # Single edge
                    total_length += edge_data.get('length', 0.0)
                else:
                    # MultiDiGraph - take first edge
                    total_length += list(edge_data.values())[0].get('length', 0.0)

        return total_length

    @staticmethod
    def calculate_route_capacity(graph: Any, route: List[Any]) -> float:
        """
        Calculate pedestrian flow capacity of a route (people per minute). Pure function.

        Finds the bottleneck (minimum capacity) along the route.

        Args:
            graph: NetworkX graph
            route: List of node IDs

        Returns:
            Minimum flow capacity in people per minute
        """
        if not NETWORKX_AVAILABLE or graph is None or len(route) < 2:
            return 0.0

        min_capacity = float('inf')

        for i in range(len(route) - 1):
            u, v = route[i], route[i + 1]
            if graph.has_edge(u, v):
                edge_data = graph.get_edge_data(u, v)

                if isinstance(edge_data, dict):
                    capacity = RouteCalculatorService._calculate_edge_capacity(edge_data)
                else:
                    # MultiDiGraph - take first edge
                    capacity = RouteCalculatorService._calculate_edge_capacity(list(edge_data.values())[0])

                min_capacity = min(min_capacity, capacity)

        return min_capacity if min_capacity != float('inf') else 0.0

    @staticmethod
    def _calculate_edge_capacity(edge_data: Dict) -> float:
        """
        Calculate pedestrian capacity for an edge. Pure function.

        Uses Fruin's Level of Service standards.

        Args:
            edge_data: Edge attributes dictionary

        Returns:
            Flow capacity in people per minute
        """
        # Extract edge attributes
        width = edge_data.get('width', 4.0)  # Default 4m width
        length = edge_data.get('length', 100.0)

        # Effective width accounting for obstacles (Fruin's standard)
        effective_width = max(width - 0.6, 1.0)

        # Flow capacity (people per meter width per minute)
        # Conservative estimate: 1.3 people/m/s = 78 people/m/min
        flow_per_meter_per_minute = 78.0

        # Total capacity = effective width * flow rate
        capacity = effective_width * flow_per_meter_per_minute

        return capacity

    @staticmethod
    def evacuation_cost_function(u: Any, v: Any, edge_data: Dict, graph: Any) -> float:
        """
        Calculate evacuation cost for A* routing. Pure function.

        Considers pedestrian flow, gradient, and congestion.

        Args:
            u: Start node
            v: End node
            edge_data: Edge attributes
            graph: NetworkX graph (for context)

        Returns:
            Evacuation cost (time in seconds)
        """
        # Base distance
        base_distance = edge_data.get('length', 100.0)

        # Street width affects capacity
        street_width = edge_data.get('width', 4.0)

        # Gradient affects walking speed
        gradient = abs(edge_data.get('gradient', 0.0))

        # Effective width for pedestrians
        effective_width = max(street_width - 0.6, 1.0)

        # Flow capacity (people per meter per second)
        flow_capacity = effective_width * 1.3

        # Walking speed (m/s) affected by gradient
        base_walking_speed = 1.2  # Normal walking speed
        gradient_penalty = gradient * 0.1
        walking_speed = max(base_walking_speed - gradient_penalty, 0.5)

        # Congestion factor (higher capacity = less congestion)
        congestion_factor = 1.0 + (10.0 / max(flow_capacity, 1.0))

        # Total evacuation time = distance / speed * congestion
        evacuation_time = (base_distance / walking_speed) * congestion_factor

        return evacuation_time

    @staticmethod
    def find_multiple_routes(
        graph: Any,
        start_nodes: List[Any],
        end_nodes: List[Any],
        cost_function: Optional[Callable] = None,
        max_routes: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find multiple evacuation routes from starts to ends. Pure function.

        Args:
            graph: NetworkX graph
            start_nodes: List of starting node IDs
            end_nodes: List of target node IDs (safe zones)
            cost_function: Optional custom cost function
            max_routes: Maximum number of routes to calculate

        Returns:
            List of route dictionaries with route, length, capacity
        """
        if not NETWORKX_AVAILABLE or graph is None:
            return []

        routes = []

        for i, start in enumerate(start_nodes[:max_routes]):
            # Find nearest suitable safe zone
            best_end = None
            min_distance = float('inf')

            for end in end_nodes:
                try:
                    distance = RouteCalculatorService.calculate_distance(graph, start, end)
                    if 500 < distance < min_distance:  # At least 500m for meaningful route
                        min_distance = distance
                        best_end = end
                except Exception:
                    continue

            if best_end is None and end_nodes:
                # Fallback: use any safe zone
                best_end = end_nodes[i % len(end_nodes)]

            if best_end:
                try:
                    route = RouteCalculatorService.calculate_evacuation_route(
                        graph, start, best_end, cost_function
                    )

                    if route:
                        length = RouteCalculatorService.calculate_route_length(graph, route)
                        capacity = RouteCalculatorService.calculate_route_capacity(graph, route)

                        routes.append({
                            'route': route,
                            'start': start,
                            'end': best_end,
                            'length': length,
                            'capacity': capacity,
                            'num_nodes': len(route)
                        })
                except Exception as e:
                    logger.warning(f"Failed to calculate route {i}: {e}")

        return routes

    @staticmethod
    def calculate_euclidean_distance(
        graph: Any,
        node1: Any,
        node2: Any
    ) -> float:
        """
        Calculate Euclidean distance between two nodes. Pure function.

        Args:
            graph: NetworkX graph
            node1: First node ID
            node2: Second node ID

        Returns:
            Euclidean distance in coordinate units
        """
        if graph is None or node1 not in graph.nodes or node2 not in graph.nodes:
            return float('inf')

        x1 = graph.nodes[node1].get('x', 0.0)
        y1 = graph.nodes[node1].get('y', 0.0)
        x2 = graph.nodes[node2].get('x', 0.0)
        y2 = graph.nodes[node2].get('y', 0.0)

        return ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5
