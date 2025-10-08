"""
Stateless London Simulation Service

Evacuation simulation for London using OSMnx street networks.
All operations are stateless - graph and configuration passed as parameters.
"""

from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
import structlog

from services.network.graph_service import NetworkGraphService
from services.network.route_calculator import RouteCalculatorService
from services.network.network_metrics import NetworkMetricsService

logger = structlog.get_logger(__name__)


class LondonSimulationService:
    """
    Stateless service for London-based evacuation simulations.

    All methods accept dependencies as parameters instead of storing them as state.
    This allows concurrent simulations with different configurations.
    """

    def __init__(
        self,
        graph_service: Optional[NetworkGraphService] = None,
        route_calculator: Optional[RouteCalculatorService] = None,
        metrics_service: Optional[NetworkMetricsService] = None
    ):
        """
        Initialize with optional dependency injection.

        Args:
            graph_service: Optional NetworkGraphService instance
            route_calculator: Optional RouteCalculatorService instance
            metrics_service: Optional NetworkMetricsService instance
        """
        self.graph_service = graph_service or NetworkGraphService()
        self.route_calculator = route_calculator or RouteCalculatorService()
        self.metrics_service = metrics_service or NetworkMetricsService()

    def generate_evacuation_routes(
        self,
        city: str,
        num_routes: int = 10,
        cache_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Generate evacuation routes for a city. Stateless operation.

        Args:
            city: City name (e.g., 'westminster', 'city_of_london')
            num_routes: Number of routes to generate
            cache_dir: Optional cache directory for graphs

        Returns:
            Dictionary with routes, coordinates, and metrics
        """
        try:
            # Load graph using stateless service
            graph = self.graph_service.load_graph(
                city=city,
                cache_dir=cache_dir,
                force_reload=False
            )

            if graph is None:
                return {"error": f"Failed to load street network for {city}"}

            # Get safe zones and population centers
            safe_zones = self.graph_service.get_safe_zones(city, graph)
            population_centers = self.graph_service.get_population_centers(city, graph)

            if not safe_zones or not population_centers:
                return {"error": f"No safe zones or population centers defined for {city}"}

            # Calculate routes using stateless route calculator
            routes_data = self.route_calculator.find_multiple_routes(
                graph=graph,
                start_nodes=population_centers,
                end_nodes=safe_zones,
                cost_function=self.route_calculator.evacuation_cost_function,
                max_routes=num_routes
            )

            if not routes_data:
                return {"error": "No valid routes found"}

            # Extract coordinates for visualization
            routes_with_coords = []
            for route_info in routes_data:
                coords = self.graph_service.get_route_coordinates(
                    graph=graph,
                    route=route_info['route']
                )

                routes_with_coords.append({
                    'route': route_info['route'],
                    'coordinates': coords,
                    'length': route_info['length'],
                    'capacity': route_info['capacity'],
                    'num_nodes': route_info['num_nodes']
                })

            # Calculate network metrics
            basic_metrics = self.metrics_service.calculate_basic_metrics(graph)
            evacuation_metrics = self.metrics_service.calculate_evacuation_metrics(
                graph=graph,
                routes=routes_data
            )

            return {
                'city': city,
                'num_routes': len(routes_with_coords),
                'routes': routes_with_coords,
                'network_metrics': basic_metrics,
                'evacuation_metrics': evacuation_metrics,
                'num_safe_zones': len(safe_zones),
                'num_population_centers': len(population_centers)
            }

        except Exception as e:
            logger.error(f"Failed to generate evacuation routes: {e}", exc_info=True)
            return {"error": str(e)}

    def calculate_clearance_time(
        self,
        city: str,
        population_size: int,
        route_data: Optional[Dict[str, Any]] = None,
        cache_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Calculate evacuation clearance time. Stateless operation.

        Args:
            city: City name
            population_size: Number of people to evacuate
            route_data: Optional pre-calculated route data
            cache_dir: Optional cache directory for graphs

        Returns:
            Dictionary with clearance time and metrics
        """
        try:
            # Get routes if not provided
            if route_data is None:
                route_data = self.generate_evacuation_routes(
                    city=city,
                    num_routes=10,
                    cache_dir=cache_dir
                )

            if 'error' in route_data:
                return route_data

            # Calculate total capacity
            total_capacity = route_data['evacuation_metrics']['total_capacity']

            if total_capacity <= 0:
                return {"error": "No evacuation capacity available"}

            # Calculate clearance time (simple model)
            # Time = Population / Capacity (people/minute)
            clearance_time_minutes = population_size / total_capacity

            # Add congestion factor
            avg_route_length = route_data['evacuation_metrics']['avg_route_length']
            congestion_factor = 1.0 + (avg_route_length / 5000.0)  # Longer routes = more congestion

            clearance_time_minutes *= congestion_factor

            return {
                'city': city,
                'population_size': population_size,
                'clearance_time_minutes': round(clearance_time_minutes, 1),
                'total_capacity': total_capacity,
                'congestion_factor': congestion_factor,
                'num_routes': route_data['num_routes'],
                'avg_route_length': avg_route_length
            }

        except Exception as e:
            logger.error(f"Failed to calculate clearance time: {e}", exc_info=True)
            return {"error": str(e)}

    def analyze_network_robustness(
        self,
        city: str,
        cache_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Analyze network robustness. Stateless operation.

        Args:
            city: City name
            cache_dir: Optional cache directory

        Returns:
            Dictionary with robustness metrics
        """
        try:
            # Load graph
            graph = self.graph_service.load_graph(
                city=city,
                cache_dir=cache_dir,
                force_reload=False
            )

            if graph is None:
                return {"error": f"Failed to load street network for {city}"}

            # Calculate robustness
            robustness_score = self.metrics_service.calculate_robustness_score(graph)

            # Calculate connectivity metrics
            connectivity_metrics = self.metrics_service.calculate_connectivity_metrics(graph)

            # Identify bottlenecks
            bottlenecks = self.metrics_service.identify_bottlenecks(graph, top_n=5)

            return {
                'city': city,
                'robustness_score': robustness_score,
                'connectivity': connectivity_metrics,
                'top_bottlenecks': bottlenecks
            }

        except Exception as e:
            logger.error(f"Failed to analyze robustness: {e}", exc_info=True)
            return {"error": str(e)}

    def calculate_safe_zone_coverage(
        self,
        city: str,
        max_distance: float = 2000.0,
        cache_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Calculate safe zone coverage. Stateless operation.

        Args:
            city: City name
            max_distance: Maximum acceptable distance (meters)
            cache_dir: Optional cache directory

        Returns:
            Dictionary with coverage metrics
        """
        try:
            # Load graph
            graph = self.graph_service.load_graph(
                city=city,
                cache_dir=cache_dir,
                force_reload=False
            )

            if graph is None:
                return {"error": f"Failed to load street network for {city}"}

            # Get safe zones
            safe_zones = self.graph_service.get_safe_zones(city, graph)

            if not safe_zones:
                return {"error": f"No safe zones defined for {city}"}

            # Calculate coverage
            coverage_metrics = self.metrics_service.calculate_coverage_metrics(
                graph=graph,
                safe_zones=safe_zones,
                max_distance=max_distance
            )

            return {
                'city': city,
                **coverage_metrics
            }

        except Exception as e:
            logger.error(f"Failed to calculate coverage: {e}", exc_info=True)
            return {"error": str(e)}
