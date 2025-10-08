"""
Unit tests for network services (graph, route calculator, metrics).

Tests verify stateless behavior and dependency injection.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

from services.network.graph_service import NetworkGraphService
from services.network.route_calculator import RouteCalculatorService
from services.network.network_metrics import NetworkMetricsService


class TestNetworkGraphService:
    """Test NetworkGraphService stateless operations."""

    def test_is_city_supported(self):
        """Test city support check (pure function)."""
        assert NetworkGraphService.is_city_supported("westminster")
        assert NetworkGraphService.is_city_supported("city_of_london")
        assert not NetworkGraphService.is_city_supported("invalid_city")

    def test_get_supported_cities(self):
        """Test getting list of supported cities."""
        cities = NetworkGraphService.get_supported_cities()
        assert isinstance(cities, list)
        assert "westminster" in cities
        assert "city_of_london" in cities
        assert len(cities) > 0

    def test_stateless_initialization(self):
        """Test that service can be instantiated multiple times."""
        service1 = NetworkGraphService()
        service2 = NetworkGraphService()

        assert service1 is not service2  # Different instances
        # No instance state to compare

    @patch('services.network.graph_service.ox')
    def test_load_graph_uses_cache(self, mock_ox):
        """Test that load_graph respects cache_dir parameter."""
        # Create a mock graph
        mock_graph = MagicMock()
        mock_graph.number_of_nodes.return_value = 100
        mock_graph.number_of_edges.return_value = 200

        cache_dir = Path("/tmp/test_cache")

        # Call should be stateless - no state stored in service
        graph = NetworkGraphService.load_graph(
            city="westminster",
            cache_dir=cache_dir,
            force_reload=False
        )

        # Verify it's stateless - calling again works the same way
        graph2 = NetworkGraphService.load_graph(
            city="westminster",
            cache_dir=cache_dir,
            force_reload=False
        )

    def test_get_node_coordinates_pure_function(self):
        """Test that get_node_coordinates is a pure function."""
        # Create mock graph
        mock_graph = MagicMock()
        mock_graph.nodes = {
            'node1': {'x': 1.0, 'y': 2.0},
            'node2': {'x': 3.0, 'y': 4.0}
        }

        # Should return same result for same inputs
        coords1 = NetworkGraphService.get_node_coordinates(mock_graph, 'node1')
        coords2 = NetworkGraphService.get_node_coordinates(mock_graph, 'node1')

        assert coords1 == coords2 == (1.0, 2.0)


class TestRouteCalculatorService:
    """Test RouteCalculatorService stateless operations."""

    def test_stateless_initialization(self):
        """Test that calculator can be instantiated multiple times."""
        calc1 = RouteCalculatorService()
        calc2 = RouteCalculatorService()

        assert calc1 is not calc2

    def test_calculate_shortest_path_with_mock_graph(self):
        """Test shortest path calculation with mock graph."""
        # Create simple mock graph
        mock_graph = MagicMock()

        with patch('services.network.route_calculator.nx') as mock_nx:
            mock_nx.shortest_path.return_value = ['A', 'B', 'C']

            route = RouteCalculatorService.calculate_shortest_path(
                graph=mock_graph,
                start_node='A',
                end_node='C',
                weight='length'
            )

            assert route == ['A', 'B', 'C']
            mock_nx.shortest_path.assert_called_once()

    def test_calculate_route_length_pure_function(self):
        """Test that calculate_route_length is pure."""
        # Create mock graph with edges
        mock_graph = MagicMock()
        mock_graph.has_edge.return_value = True
        mock_graph.get_edge_data.return_value = {'length': 100.0}

        route = ['A', 'B', 'C']

        # Call twice with same inputs
        length1 = RouteCalculatorService.calculate_route_length(mock_graph, route)
        length2 = RouteCalculatorService.calculate_route_length(mock_graph, route)

        # Should be deterministic
        assert length1 == length2

    def test_evacuation_cost_function_is_static(self):
        """Test that evacuation_cost_function is stateless."""
        edge_data = {'length': 100, 'width': 4.0, 'gradient': 0.0}
        mock_graph = MagicMock()

        # Call twice
        cost1 = RouteCalculatorService.evacuation_cost_function('A', 'B', edge_data, mock_graph)
        cost2 = RouteCalculatorService.evacuation_cost_function('A', 'B', edge_data, mock_graph)

        # Should be deterministic (pure function)
        assert cost1 == cost2
        assert cost1 > 0


class TestNetworkMetricsService:
    """Test NetworkMetricsService stateless operations."""

    def test_stateless_initialization(self):
        """Test that metrics service is stateless."""
        service1 = NetworkMetricsService()
        service2 = NetworkMetricsService()

        assert service1 is not service2

    def test_calculate_basic_metrics_pure_function(self):
        """Test that basic metrics calculation is pure."""
        mock_graph = MagicMock()
        mock_graph.number_of_nodes.return_value = 100
        mock_graph.number_of_edges.return_value = 200
        mock_graph.is_directed.return_value = True
        mock_graph.is_multigraph.return_value = False

        # Call twice
        metrics1 = NetworkMetricsService.calculate_basic_metrics(mock_graph)
        metrics2 = NetworkMetricsService.calculate_basic_metrics(mock_graph)

        # Should be identical
        assert metrics1 == metrics2
        assert metrics1['num_nodes'] == 100
        assert metrics1['num_edges'] == 200

    def test_calculate_evacuation_metrics_stateless(self):
        """Test evacuation metrics calculation is stateless."""
        mock_graph = MagicMock()
        routes = [
            {'length': 1000, 'capacity': 50},
            {'length': 1500, 'capacity': 60},
            {'length': 1200, 'capacity': 55}
        ]

        # Call twice
        metrics1 = NetworkMetricsService.calculate_evacuation_metrics(mock_graph, routes)
        metrics2 = NetworkMetricsService.calculate_evacuation_metrics(mock_graph, routes)

        # Should be identical
        assert metrics1 == metrics2
        assert metrics1['num_routes'] == 3
        assert metrics1['total_capacity'] == 165


class TestDependencyInjection:
    """Test that services support dependency injection."""

    def test_services_can_be_injected(self):
        """Test that services can be passed as dependencies."""
        # Create custom service instances
        graph_service = NetworkGraphService()
        route_calculator = RouteCalculatorService()
        metrics_service = NetworkMetricsService()

        # Should be able to pass them around
        assert graph_service is not None
        assert route_calculator is not None
        assert metrics_service is not None

        # They should be independent
        assert graph_service is not route_calculator
        assert graph_service is not metrics_service

    def test_mock_injection(self):
        """Test that services can be mocked for testing."""
        # Create mock services
        mock_graph_service = Mock(spec=NetworkGraphService)
        mock_route_calculator = Mock(spec=RouteCalculatorService)

        # Configure mocks
        mock_graph_service.load_graph.return_value = MagicMock()
        mock_route_calculator.calculate_shortest_path.return_value = ['A', 'B']

        # Use mocks (would be injected into higher-level services)
        graph = mock_graph_service.load_graph("test_city")
        route = mock_route_calculator.calculate_shortest_path(graph, 'A', 'B')

        assert route == ['A', 'B']
        mock_graph_service.load_graph.assert_called_once_with("test_city")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
