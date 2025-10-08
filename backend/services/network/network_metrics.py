"""
Stateless Network Metrics Service

Calculates network-level metrics for evacuation analysis.
All operations are stateless - graph passed as parameter.
"""

from typing import Any, Dict, List, Optional
import structlog

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    nx = None

logger = structlog.get_logger(__name__)


class NetworkMetricsService:
    """
    Stateless service for calculating network-level metrics.

    All methods are pure functions that take graph as parameter.
    """

    @staticmethod
    def calculate_basic_metrics(graph: Any) -> Dict[str, Any]:
        """
        Calculate basic network metrics. Pure function.

        Args:
            graph: NetworkX graph

        Returns:
            Dictionary of basic metrics
        """
        if not NETWORKX_AVAILABLE or graph is None:
            return {}

        return {
            'num_nodes': graph.number_of_nodes(),
            'num_edges': graph.number_of_edges(),
            'is_directed': graph.is_directed(),
            'is_multigraph': graph.is_multigraph()
        }

    @staticmethod
    def calculate_connectivity_metrics(graph: Any) -> Dict[str, Any]:
        """
        Calculate connectivity metrics. Pure function.

        Args:
            graph: NetworkX graph

        Returns:
            Dictionary of connectivity metrics
        """
        if not NETWORKX_AVAILABLE or graph is None:
            return {}

        metrics = {}

        try:
            # For directed graphs
            if graph.is_directed():
                metrics['is_strongly_connected'] = nx.is_strongly_connected(graph)
                metrics['is_weakly_connected'] = nx.is_weakly_connected(graph)
                metrics['num_strongly_connected_components'] = nx.number_strongly_connected_components(graph)
                metrics['num_weakly_connected_components'] = nx.number_weakly_connected_components(graph)
            else:
                # For undirected graphs
                metrics['is_connected'] = nx.is_connected(graph)
                metrics['num_connected_components'] = nx.number_connected_components(graph)

            # Average degree
            degrees = [d for n, d in graph.degree()]
            metrics['average_degree'] = sum(degrees) / len(degrees) if degrees else 0.0

        except Exception as e:
            logger.warning(f"Failed to calculate connectivity metrics: {e}")

        return metrics

    @staticmethod
    def calculate_robustness_score(graph: Any, critical_nodes: Optional[List] = None) -> float:
        """
        Calculate network robustness score. Pure function.

        Measures how well the network maintains connectivity after node removals.

        Args:
            graph: NetworkX graph
            critical_nodes: Optional list of critical nodes to test

        Returns:
            Robustness score (0-1, higher is better)
        """
        if not NETWORKX_AVAILABLE or graph is None or graph.number_of_nodes() == 0:
            return 0.0

        try:
            # Create a copy for testing
            test_graph = graph.copy()

            if critical_nodes is None:
                # Test random node removal
                nodes = list(test_graph.nodes())
                critical_nodes = nodes[:min(10, len(nodes))]

            removed_count = 0
            still_connected = 0

            for node in critical_nodes:
                if node in test_graph.nodes():
                    test_graph.remove_node(node)
                    removed_count += 1

                    # Check connectivity after removal
                    if test_graph.is_directed():
                        connected = nx.is_weakly_connected(test_graph)
                    else:
                        connected = nx.is_connected(test_graph)

                    if connected:
                        still_connected += 1

            # Robustness = fraction of times network stayed connected
            return still_connected / removed_count if removed_count > 0 else 1.0

        except Exception as e:
            logger.warning(f"Failed to calculate robustness: {e}")
            return 0.0

    @staticmethod
    def identify_bottlenecks(graph: Any, top_n: int = 10) -> List[Dict[str, Any]]:
        """
        Identify network bottlenecks using betweenness centrality. Pure function.

        Args:
            graph: NetworkX graph
            top_n: Number of top bottlenecks to return

        Returns:
            List of bottleneck nodes with centrality scores
        """
        if not NETWORKX_AVAILABLE or graph is None:
            return []

        try:
            # Calculate betweenness centrality
            centrality = nx.betweenness_centrality(graph, weight='length')

            # Sort by centrality
            sorted_nodes = sorted(
                centrality.items(),
                key=lambda x: x[1],
                reverse=True
            )[:top_n]

            bottlenecks = []
            for node_id, score in sorted_nodes:
                node_data = graph.nodes[node_id]
                bottlenecks.append({
                    'node_id': node_id,
                    'centrality_score': score,
                    'x': node_data.get('x', 0.0),
                    'y': node_data.get('y', 0.0)
                })

            return bottlenecks

        except Exception as e:
            logger.warning(f"Failed to identify bottlenecks: {e}")
            return []

    @staticmethod
    def calculate_network_efficiency(graph: Any) -> float:
        """
        Calculate network efficiency. Pure function.

        Measures how efficiently information (or people) can flow through network.

        Args:
            graph: NetworkX graph

        Returns:
            Efficiency score (0-1, higher is better)
        """
        if not NETWORKX_AVAILABLE or graph is None:
            return 0.0

        try:
            # Use global efficiency from NetworkX
            if graph.is_directed():
                # Convert to undirected for efficiency calculation
                undirected = graph.to_undirected()
                efficiency = nx.global_efficiency(undirected)
            else:
                efficiency = nx.global_efficiency(graph)

            return efficiency

        except Exception as e:
            logger.warning(f"Failed to calculate efficiency: {e}")
            return 0.0

    @staticmethod
    def calculate_coverage_metrics(
        graph: Any,
        safe_zones: List[Any],
        max_distance: float = 2000.0
    ) -> Dict[str, Any]:
        """
        Calculate safe zone coverage metrics. Pure function.

        Args:
            graph: NetworkX graph
            safe_zones: List of safe zone node IDs
            max_distance: Maximum acceptable distance to safe zone (meters)

        Returns:
            Dictionary of coverage metrics
        """
        if not NETWORKX_AVAILABLE or graph is None or not safe_zones:
            return {}

        try:
            nodes_within_range = 0
            total_nodes = graph.number_of_nodes()
            distances = []

            # Sample nodes for performance (check every 10th node)
            sample_nodes = list(graph.nodes())[::10]

            for node in sample_nodes:
                min_distance = float('inf')

                for safe_zone in safe_zones:
                    try:
                        distance = nx.shortest_path_length(
                            graph, node, safe_zone, weight='length'
                        )
                        min_distance = min(min_distance, distance)
                    except nx.NetworkXNoPath:
                        continue

                if min_distance <= max_distance:
                    nodes_within_range += 1

                if min_distance != float('inf'):
                    distances.append(min_distance)

            coverage_ratio = nodes_within_range / len(sample_nodes) if sample_nodes else 0.0
            avg_distance = sum(distances) / len(distances) if distances else 0.0

            return {
                'coverage_ratio': coverage_ratio,
                'nodes_within_range': nodes_within_range,
                'avg_distance_to_safe_zone': avg_distance,
                'max_acceptable_distance': max_distance,
                'num_safe_zones': len(safe_zones)
            }

        except Exception as e:
            logger.warning(f"Failed to calculate coverage: {e}")
            return {}

    @staticmethod
    def calculate_evacuation_metrics(
        graph: Any,
        routes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate evacuation-specific metrics from routes. Pure function.

        Args:
            graph: NetworkX graph
            routes: List of route dictionaries with 'route', 'length', 'capacity'

        Returns:
            Dictionary of evacuation metrics
        """
        if not NETWORKX_AVAILABLE or graph is None or not routes:
            return {}

        try:
            lengths = [r.get('length', 0.0) for r in routes]
            capacities = [r.get('capacity', 0.0) for r in routes]

            return {
                'num_routes': len(routes),
                'avg_route_length': sum(lengths) / len(lengths) if lengths else 0.0,
                'min_route_length': min(lengths) if lengths else 0.0,
                'max_route_length': max(lengths) if lengths else 0.0,
                'avg_route_capacity': sum(capacities) / len(capacities) if capacities else 0.0,
                'min_route_capacity': min(capacities) if capacities else 0.0,
                'total_capacity': sum(capacities)
            }

        except Exception as e:
            logger.warning(f"Failed to calculate evacuation metrics: {e}")
            return {}
