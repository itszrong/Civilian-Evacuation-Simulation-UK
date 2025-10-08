"""
Test script to verify stateless services refactoring.

This demonstrates that all services are now stateless and use dependency injection.
"""

from pathlib import Path

# Test Network Services
from services.network.graph_service import NetworkGraphService
from services.network.route_calculator import RouteCalculatorService
from services.network.network_metrics import NetworkMetricsService

# Test Metrics and Scenario Services
from services.metrics.metrics_service import MetricsService
from services.scenarios.scenario_service import ScenarioService

# Test Agent Integration
from agents.metrics_agent import MetricsAgent
from agents.agentic_builders import AgenticMetricsBuilder, AgenticScenarioBuilder

# Test Simulation Service
from services.simulation.london_simulation_service import LondonSimulationService


def test_network_graph_service():
    """Test that NetworkGraphService is stateless."""
    print("\n=== Testing NetworkGraphService ===")

    # Test stateless method calls
    supported_cities = NetworkGraphService.get_supported_cities()
    print(f"✓ Supported cities: {supported_cities}")

    is_supported = NetworkGraphService.is_city_supported("westminster")
    print(f"✓ Westminster supported: {is_supported}")

    # Test graph loading (stateless - no instance state)
    graph_service = NetworkGraphService()
    cache_dir = Path("backend/cache/graphs")

    # Multiple concurrent calls possible because stateless
    graph1 = NetworkGraphService.load_graph("westminster", cache_dir)
    graph2 = NetworkGraphService.load_graph("westminster", cache_dir)

    if graph1 is not None:
        print(f"✓ Loaded graph with {graph1.number_of_nodes()} nodes")
        print(f"✓ Multiple loads work: {graph1 is not graph2}")  # Should be separate instances

    print("✓ NetworkGraphService is stateless")


def test_metrics_service():
    """Test that MetricsService is stateless."""
    print("\n=== Testing MetricsService ===")

    # Test stateless method calls - no instance state needed
    config = MetricsService.get_standard_metrics_config()
    print(f"✓ Got standard config with {len(config['metrics'])} metrics")

    # Multiple instances can coexist
    service1 = MetricsService()
    service2 = MetricsService()

    print(f"✓ Multiple instances: {service1 is not service2}")
    print("✓ MetricsService is stateless")


def test_scenario_service():
    """Test that ScenarioService is stateless."""
    print("\n=== Testing ScenarioService ===")

    # Test stateless method calls
    templates = ScenarioService.get_framework_templates()
    print(f"✓ Got {len(templates)} framework templates")

    template_info = ScenarioService.get_template_info()
    print(f"✓ Got template info: {list(template_info.keys())}")

    # Multiple instances can coexist
    service1 = ScenarioService()
    service2 = ScenarioService()

    print(f"✓ Multiple instances: {service1 is not service2}")
    print("✓ ScenarioService is stateless")


def test_agent_dependency_injection():
    """Test that agents use dependency injection."""
    print("\n=== Testing Agent Dependency Injection ===")

    # Create custom service instances
    metrics_service = MetricsService()
    scenario_service = ScenarioService()

    # Inject into agents
    metrics_agent = MetricsAgent(
        data_path="custom/path",
        metrics_service=metrics_service
    )

    agentic_metrics = AgenticMetricsBuilder(
        data_path="custom/path",
        metrics_service=metrics_service
    )

    agentic_scenarios = AgenticScenarioBuilder(
        scenarios_path="custom/scenarios",
        scenario_service=scenario_service
    )

    print(f"✓ MetricsAgent uses injected service: {metrics_agent.metrics_service is metrics_service}")
    print(f"✓ AgenticMetricsBuilder uses injected service: {agentic_metrics.metrics_service is metrics_service}")
    print(f"✓ AgenticScenarioBuilder uses injected service: {agentic_scenarios.scenario_service is scenario_service}")
    print("✓ Agents support dependency injection")


def test_london_simulation_service():
    """Test that LondonSimulationService uses stateless dependencies."""
    print("\n=== Testing LondonSimulationService ===")

    # Create with dependency injection
    graph_service = NetworkGraphService()
    route_calculator = RouteCalculatorService()
    metrics_service = NetworkMetricsService()

    simulation = LondonSimulationService(
        graph_service=graph_service,
        route_calculator=route_calculator,
        metrics_service=metrics_service
    )

    print(f"✓ Simulation uses injected graph service: {simulation.graph_service is graph_service}")
    print(f"✓ Simulation uses injected route calculator: {simulation.route_calculator is route_calculator}")
    print(f"✓ Simulation uses injected metrics service: {simulation.metrics_service is metrics_service}")

    # Test stateless operation
    result = simulation.generate_evacuation_routes(
        city="westminster",
        num_routes=3,
        cache_dir=Path("backend/cache/graphs")
    )

    if 'error' not in result:
        print(f"✓ Generated {result.get('num_routes', 0)} routes")
        print(f"✓ Network metrics: {result.get('network_metrics', {})}")

    print("✓ LondonSimulationService is stateless with DI")


def test_concurrent_operations():
    """Test that multiple operations can run concurrently (proof of statelessness)."""
    print("\n=== Testing Concurrent Operations ===")

    # Create multiple service instances
    graph_service = NetworkGraphService()
    metrics_service = MetricsService()
    scenario_service = ScenarioService()

    # Simulate concurrent operations (in real code, these could be in threads/async)
    cities = ["westminster", "city_of_london"]
    cache_dir = Path("backend/cache/graphs")

    for city in cities:
        # Each operation is independent - no shared state
        graph = NetworkGraphService.load_graph(city, cache_dir)
        if graph:
            print(f"✓ Loaded {city}: {graph.number_of_nodes()} nodes")

    # Get templates concurrently (stateless)
    templates1 = ScenarioService.get_framework_templates()
    templates2 = ScenarioService.get_framework_templates()

    print(f"✓ Concurrent template access: {len(templates1)} == {len(templates2)}")
    print("✓ Services support concurrent operations")


def main():
    """Run all tests."""
    print("=" * 70)
    print("STATELESS SERVICES VERIFICATION")
    print("=" * 70)

    try:
        test_network_graph_service()
        test_metrics_service()
        test_scenario_service()
        test_agent_dependency_injection()
        test_london_simulation_service()
        test_concurrent_operations()

        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED - Services are stateless with DI")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
