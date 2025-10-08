"""
Tests for services.network.route_calculator module.
"""

import pytest
from unittest.mock import Mock, patch
import networkx as nx

from services.network.route_calculator import RouteCalculatorService


class TestRouteCalculatorService:
    """Test the RouteCalculatorService class."""

    def setup_method(self):
        """Set up test environment with sample graph."""
        self.service = RouteCalculatorService()

        # Create a simple test graph
        self.graph = nx.DiGraph()

        # Add nodes with coordinates
        self.graph.add_node(1, x=0, y=0)
        self.graph.add_node(2, x=100, y=0)
        self.graph.add_node(3, x=200, y=0)
        self.graph.add_node(4, x=0, y=100)
        self.graph.add_node(5, x=100, y=100)

        # Add edges with attributes
        self.graph.add_edge(1, 2, length=100.0, width=4.0, gradient=0.0)
        self.graph.add_edge(2, 3, length=100.0, width=5.0, gradient=0.05)
        self.graph.add_edge(1, 4, length=100.0, width=3.0, gradient=0.02)
        self.graph.add_edge(4, 5, length=100.0, width=4.0, gradient=0.0)
        self.graph.add_edge(2, 5, length=100.0, width=6.0, gradient=0.01)
        self.graph.add_edge(5, 3, length=100.0, width=4.0, gradient=0.0)

    def test_calculate_shortest_path_success(self):
        """Test successful shortest path calculation."""
        route = self.service.calculate_shortest_path(self.graph, 1, 3)

        assert route is not None
        assert route[0] == 1
        assert route[-1] == 3
        assert len(route) >= 2

    def test_calculate_shortest_path_no_path(self):
        """Test shortest path when no path exists."""
        # Add isolated node
        self.graph.add_node(99, x=0, y=0)

        route = self.service.calculate_shortest_path(self.graph, 1, 99)

        assert route is None

    def test_calculate_shortest_path_none_graph(self):
        """Test shortest path with None graph."""
        route = self.service.calculate_shortest_path(None, 1, 3)

        assert route is None

    def test_calculate_shortest_path_custom_weight(self):
        """Test shortest path with custom weight attribute."""
        # Add edges with time weight
        for u, v in self.graph.edges():
            self.graph[u][v]['time'] = self.graph[u][v]['length'] / 10.0

        route = self.service.calculate_shortest_path(self.graph, 1, 3, weight='time')

        assert route is not None
        assert route[0] == 1
        assert route[-1] == 3

    def test_calculate_evacuation_route_default(self):
        """Test evacuation route calculation with default cost."""
        route = self.service.calculate_evacuation_route(self.graph, 1, 3)

        assert route is not None
        assert route[0] == 1
        assert route[-1] == 3

    def test_calculate_evacuation_route_custom_cost(self):
        """Test evacuation route with custom cost function."""
        def custom_cost(u, v, edge_data, graph):
            return edge_data.get('length', 0) * 2.0

        route = self.service.calculate_evacuation_route(
            self.graph, 1, 3, cost_function=custom_cost
        )

        assert route is not None
        assert route[0] == 1
        assert route[-1] == 3

    def test_calculate_distance_success(self):
        """Test distance calculation."""
        distance = self.service.calculate_distance(self.graph, 1, 3)

        assert distance > 0
        assert distance == 200.0  # Direct path 1->2->3

    def test_calculate_distance_no_path(self):
        """Test distance when no path exists."""
        self.graph.add_node(99, x=0, y=0)

        distance = self.service.calculate_distance(self.graph, 1, 99)

        assert distance == float('inf')

    def test_calculate_distance_none_graph(self):
        """Test distance with None graph."""
        distance = self.service.calculate_distance(None, 1, 3)

        assert distance == float('inf')

    def test_calculate_route_length(self):
        """Test route length calculation."""
        route = [1, 2, 3]

        length = self.service.calculate_route_length(self.graph, route)

        assert length == 200.0  # 100 + 100

    def test_calculate_route_length_empty_route(self):
        """Test route length with empty route."""
        length = self.service.calculate_route_length(self.graph, [])

        assert length == 0.0

    def test_calculate_route_length_single_node(self):
        """Test route length with single node."""
        length = self.service.calculate_route_length(self.graph, [1])

        assert length == 0.0

    def test_calculate_route_capacity(self):
        """Test route capacity calculation."""
        route = [1, 2, 3]

        capacity = self.service.calculate_route_capacity(self.graph, route)

        assert capacity > 0
        # Should return minimum capacity along route

    def test_calculate_route_capacity_bottleneck(self):
        """Test route capacity identifies bottleneck."""
        # Modify edge 2->3 to have narrower width
        self.graph[2][3]['width'] = 2.0

        route = [1, 2, 3]
        capacity = self.service.calculate_route_capacity(self.graph, route)

        # Capacity should be limited by narrowest segment
        assert capacity < 200.0  # Lower than wider segments

    def test_calculate_edge_capacity(self):
        """Test edge capacity calculation."""
        edge_data = {
            'width': 4.0,
            'length': 100.0
        }

        capacity = self.service._calculate_edge_capacity(edge_data)

        assert capacity > 0
        # Effective width = 4.0 - 0.6 = 3.4
        # Capacity = 3.4 * 78 = 265.2
        assert 250 < capacity < 280

    def test_calculate_edge_capacity_narrow_street(self):
        """Test edge capacity for narrow street."""
        edge_data = {
            'width': 2.0,
            'length': 100.0
        }

        capacity = self.service._calculate_edge_capacity(edge_data)

        # Effective width = max(2.0 - 0.6, 1.0) = 1.4
        assert capacity > 0
        assert capacity < 150

    def test_evacuation_cost_function(self):
        """Test evacuation cost function."""
        edge_data = {
            'length': 100.0,
            'width': 4.0,
            'gradient': 0.0
        }

        cost = self.service.evacuation_cost_function(1, 2, edge_data, self.graph)

        assert cost > 0
        # Should be reasonable evacuation time

    def test_evacuation_cost_function_with_gradient(self):
        """Test evacuation cost with gradient penalty."""
        edge_data_flat = {
            'length': 100.0,
            'width': 4.0,
            'gradient': 0.0
        }

        edge_data_steep = {
            'length': 100.0,
            'width': 4.0,
            'gradient': 0.1  # 10% gradient
        }

        cost_flat = self.service.evacuation_cost_function(1, 2, edge_data_flat, self.graph)
        cost_steep = self.service.evacuation_cost_function(1, 2, edge_data_steep, self.graph)

        # Steep gradient should increase cost
        assert cost_steep > cost_flat

    def test_evacuation_cost_function_with_narrow_street(self):
        """Test evacuation cost with capacity constraints."""
        edge_data_wide = {
            'length': 100.0,
            'width': 8.0,
            'gradient': 0.0
        }

        edge_data_narrow = {
            'length': 100.0,
            'width': 2.0,
            'gradient': 0.0
        }

        cost_wide = self.service.evacuation_cost_function(1, 2, edge_data_wide, self.graph)
        cost_narrow = self.service.evacuation_cost_function(1, 2, edge_data_narrow, self.graph)

        # Narrow street should have higher cost due to congestion
        assert cost_narrow > cost_wide

    def test_find_multiple_routes_success(self):
        """Test finding multiple routes."""
        start_nodes = [1, 4]
        end_nodes = [3, 5]

        routes = self.service.find_multiple_routes(
            self.graph, start_nodes, end_nodes, max_routes=5
        )

        assert len(routes) > 0
        for route_info in routes:
            assert 'route' in route_info
            assert 'start' in route_info
            assert 'end' in route_info
            assert 'length' in route_info
            assert 'capacity' in route_info

    def test_find_multiple_routes_with_cost_function(self):
        """Test finding multiple routes with custom cost function."""
        start_nodes = [1]
        end_nodes = [3]

        routes = self.service.find_multiple_routes(
            self.graph,
            start_nodes,
            end_nodes,
            cost_function=self.service.evacuation_cost_function,
            max_routes=1
        )

        assert len(routes) > 0

    def test_find_multiple_routes_none_graph(self):
        """Test finding routes with None graph."""
        routes = self.service.find_multiple_routes(None, [1], [3])

        assert routes == []

    def test_find_multiple_routes_empty_inputs(self):
        """Test finding routes with empty input lists."""
        routes = self.service.find_multiple_routes(self.graph, [], [])

        assert routes == []

    def test_calculate_euclidean_distance(self):
        """Test Euclidean distance calculation."""
        distance = self.service.calculate_euclidean_distance(self.graph, 1, 3)

        # Node 1 at (0, 0), Node 3 at (200, 0)
        assert distance == 200.0

    def test_calculate_euclidean_distance_diagonal(self):
        """Test Euclidean distance for diagonal route."""
        distance = self.service.calculate_euclidean_distance(self.graph, 1, 5)

        # Node 1 at (0, 0), Node 5 at (100, 100)
        # Distance = sqrt(100^2 + 100^2) = sqrt(20000) ≈ 141.42
        assert 140 < distance < 145

    def test_calculate_euclidean_distance_missing_node(self):
        """Test Euclidean distance with missing node."""
        distance = self.service.calculate_euclidean_distance(self.graph, 1, 999)

        assert distance == float('inf')

    def test_calculate_euclidean_distance_none_graph(self):
        """Test Euclidean distance with None graph."""
        distance = self.service.calculate_euclidean_distance(None, 1, 3)

        assert distance == float('inf')


@pytest.mark.unit
class TestRouteCalculatorServiceMultiGraph:
    """Test RouteCalculatorService with MultiDiGraph."""

    def setup_method(self):
        """Set up test environment with MultiDiGraph."""
        self.service = RouteCalculatorService()

        # Create MultiDiGraph (allows multiple edges between nodes)
        self.graph = nx.MultiDiGraph()

        # Add nodes
        self.graph.add_node(1, x=0, y=0)
        self.graph.add_node(2, x=100, y=0)
        self.graph.add_node(3, x=200, y=0)

        # Add multiple edges between same nodes
        self.graph.add_edge(1, 2, key=0, length=100.0, width=4.0)
        self.graph.add_edge(1, 2, key=1, length=120.0, width=5.0)  # Longer but wider
        self.graph.add_edge(2, 3, key=0, length=100.0, width=3.0)

    def test_calculate_route_length_multigraph(self):
        """Test route length calculation on MultiDiGraph."""
        route = [1, 2, 3]

        length = self.service.calculate_route_length(self.graph, route)

        # Should use first edge (key=0)
        assert length == 200.0  # 100 + 100

    def test_calculate_route_capacity_multigraph(self):
        """Test route capacity calculation on MultiDiGraph."""
        route = [1, 2, 3]

        capacity = self.service.calculate_route_capacity(self.graph, route)

        assert capacity > 0
        # Should use first edge capacities


@pytest.mark.unit
class TestRouteCalculatorServiceEdgeCases:
    """Test edge cases and error conditions."""

    def setup_method(self):
        """Set up test environment."""
        self.service = RouteCalculatorService()

    def test_calculate_shortest_path_same_start_end(self):
        """Test shortest path when start equals end."""
        graph = nx.DiGraph()
        graph.add_node(1)

        route = self.service.calculate_shortest_path(graph, 1, 1)

        # NetworkX returns single node path
        assert route == [1]

    def test_calculate_route_length_missing_edge(self):
        """Test route length when edge is missing."""
        graph = nx.DiGraph()
        graph.add_node(1)
        graph.add_node(2)
        # No edge between nodes

        route = [1, 2]
        length = self.service.calculate_route_length(graph, route)

        # Should return 0 since edge doesn't exist
        assert length == 0.0

    def test_calculate_edge_capacity_missing_attributes(self):
        """Test edge capacity with missing attributes."""
        edge_data = {}  # No width or length

        capacity = self.service._calculate_edge_capacity(edge_data)

        # Should use defaults
        assert capacity > 0

    def test_evacuation_cost_function_missing_attributes(self):
        """Test evacuation cost with missing attributes."""
        edge_data = {}  # No attributes
        graph = nx.DiGraph()

        cost = self.service.evacuation_cost_function(1, 2, edge_data, graph)

        # Should use defaults and return some cost
        assert cost > 0

    def test_find_multiple_routes_no_valid_routes(self):
        """Test finding routes when no valid routes exist."""
        graph = nx.DiGraph()
        graph.add_node(1)
        graph.add_node(2)
        # No edges - disconnected graph

        routes = self.service.find_multiple_routes(graph, [1], [2])

        assert routes == []

    @patch('services.network.route_calculator.NETWORKX_AVAILABLE', False)
    def test_methods_without_networkx(self):
        """Test that methods handle missing NetworkX gracefully."""
        graph = Mock()

        # All methods should return safe defaults
        assert self.service.calculate_shortest_path(graph, 1, 2) is None
        assert self.service.calculate_evacuation_route(graph, 1, 2) is None
        assert self.service.calculate_distance(graph, 1, 2) == float('inf')
        assert self.service.calculate_route_length(graph, [1, 2]) == 0.0
        assert self.service.calculate_route_capacity(graph, [1, 2]) == 0.0
        assert self.service.find_multiple_routes(graph, [1], [2]) == []

    def test_calculate_route_length_with_zero_length_edges(self):
        """Test route length with zero-length edges."""
        graph = nx.DiGraph()
        graph.add_node(1)
        graph.add_node(2)
        graph.add_edge(1, 2, length=0.0)

        length = self.service.calculate_route_length(graph, [1, 2])

        assert length == 0.0
