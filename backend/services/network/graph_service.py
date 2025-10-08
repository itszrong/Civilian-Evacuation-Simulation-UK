"""
Stateless Network Graph Service

Manages street network graphs for cities. All operations are stateless -
graph instances and cache are passed as parameters, not stored as instance state.
"""

import pickle
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import structlog

try:
    import networkx as nx
    import osmnx as ox
    OSMNX_AVAILABLE = True
except ImportError:
    OSMNX_AVAILABLE = False
    nx = None
    ox = None

logger = structlog.get_logger(__name__)


class NetworkGraphService:
    """
    Stateless service for loading and managing street network graphs.

    All methods are pure functions that don't modify instance state.
    Caching is handled externally via the cache parameter.
    """

    # City configuration - immutable class constants
    CITY_CONFIGS = {
        "westminster": {
            "place_name": "Westminster, London, England",
            "network_type": "drive",
            "center": (51.4975, -0.1357),
            "dist": 3000
        },
        "city_of_london": {
            "place_name": "City of London, London, England",
            "network_type": "drive",
            "center": (51.5074, -0.1278),
            "dist": 2000
        },
        "kensington_and_chelsea": {
            "place_name": "Kensington and Chelsea, London, England",
            "network_type": "drive",
            "center": (51.4991, -0.1938),
            "dist": 3000
        }
    }

    # Safe zone coordinates per city - immutable
    SAFE_ZONES = {
        "westminster": [
            (-0.1419, 51.5014),  # Hyde Park
            (-0.1537, 51.5226),  # Regent's Park
            (-0.1276, 51.5007),  # St James's Park
            (-0.1367, 51.4994),  # Green Park
            (-0.1040, 51.5014),  # Victoria Embankment Gardens
            (-0.1462, 51.4975),  # Battersea Park (south)
            (-0.1195, 51.5033),  # Covent Garden Piazza
            (-0.1278, 51.5074),  # Trafalgar Square
        ],
        "city_of_london": [
            (-0.0899, 51.5155),  # Finsbury Circus
            (-0.0813, 51.5193),  # Bunhill Fields
            (-0.0813, 51.5081),  # Tower Gardens
            (-0.1040, 51.5014),  # Victoria Embankment Gardens
        ]
    }

    # Population centers per city - immutable
    POPULATION_CENTERS = {
        "westminster": [
            (-0.1419, 51.5014),  # Oxford Circus area
            (-0.1276, 51.5007),  # Westminster/Whitehall
            (-0.1040, 51.5014),  # City of London edge
            (-0.1195, 51.5033),  # Covent Garden
            (-0.1367, 51.4994),  # Victoria area
            (-0.1537, 51.5226),  # Marylebone
            (-0.1462, 51.4975),  # Pimlico residential
            (-0.0899, 51.5033),  # Holborn/Chancery Lane
        ],
        "city_of_london": [
            (-0.0899, 51.5155),  # Liverpool Street
            (-0.0813, 51.5193),  # Moorgate
            (-0.0813, 51.5081),  # Bank/Monument
            (-0.0955, 51.5155),  # Barbican
        ]
    }

    def __init__(self):
        """Initialize service. No instance state stored."""
        if not OSMNX_AVAILABLE:
            logger.warning("OSMnx not available - graph operations will fail")

    @staticmethod
    def load_graph(
        city: str,
        cache_dir: Optional[Path] = None,
        force_reload: bool = False
    ) -> Optional[Any]:
        """
        Load street network graph for a city. Stateless operation.

        Args:
            city: City name (must be in CITY_CONFIGS)
            cache_dir: Optional cache directory for pickled graphs
            force_reload: If True, bypass cache and reload from OSMnx

        Returns:
            NetworkX graph or None if loading fails
        """
        if not OSMNX_AVAILABLE:
            logger.error("OSMnx not available")
            return None

        city_lower = city.lower().replace(" ", "_")

        if city_lower not in NetworkGraphService.CITY_CONFIGS:
            logger.error(f"Unknown city: {city}", available_cities=list(NetworkGraphService.CITY_CONFIGS.keys()))
            return None

        config = NetworkGraphService.CITY_CONFIGS[city_lower]

        # Try loading from cache first
        if cache_dir and not force_reload:
            cached_graph = NetworkGraphService._load_from_cache(city_lower, cache_dir)
            if cached_graph is not None:
                return cached_graph

        # Load from OSMnx
        try:
            logger.info(f"Loading street network for {city} from OSMnx...", config=config)

            # Try place-based loading first
            try:
                graph = ox.graph_from_place(
                    config["place_name"],
                    network_type=config["network_type"]
                )
                logger.info(f"Loaded graph with {len(graph.nodes)} nodes and {len(graph.edges)} edges")
            except Exception as e:
                logger.warning(f"Place-based loading failed: {e}, trying center-based loading")
                # Fallback to center-based loading
                graph = ox.graph_from_point(
                    config["center"],
                    dist=config["dist"],
                    network_type=config["network_type"]
                )
                logger.info(f"Loaded graph with {len(graph.nodes)} nodes and {len(graph.edges)} edges")

            # Cache the graph if cache_dir provided
            if cache_dir:
                NetworkGraphService._save_to_cache(graph, city_lower, cache_dir)

            return graph

        except Exception as e:
            logger.error(f"Failed to load graph for {city}: {e}", exc_info=True)
            return None

    @staticmethod
    def _load_from_cache(city: str, cache_dir: Path) -> Optional[Any]:
        """Load graph from cache. Pure function."""
        cache_file = cache_dir / f"graph_{city}.pkl"

        if not cache_file.exists():
            return None

        try:
            with open(cache_file, 'rb') as f:
                graph = pickle.load(f)
            logger.info(f"Loaded graph from cache: {cache_file}")
            return graph
        except Exception as e:
            logger.warning(f"Failed to load graph from cache: {e}")
            return None

    @staticmethod
    def _save_to_cache(graph: Any, city: str, cache_dir: Path) -> None:
        """Save graph to cache. Side effect: writes to disk."""
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / f"graph_{city}.pkl"

        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(graph, f)
            logger.info(f"Saved graph to cache: {cache_file}")
        except Exception as e:
            logger.warning(f"Failed to save graph to cache: {e}")

    @staticmethod
    def get_safe_zones(city: str, graph: Any) -> List[Any]:
        """
        Get safe zone nodes for a city. Stateless operation.

        Args:
            city: City name
            graph: NetworkX graph

        Returns:
            List of safe zone node IDs
        """
        if not OSMNX_AVAILABLE or graph is None:
            return []

        city_lower = city.lower().replace(" ", "_")
        safe_zone_coords = NetworkGraphService.SAFE_ZONES.get(city_lower, [])

        safe_zones = []
        for lon, lat in safe_zone_coords:
            try:
                nearest_node = ox.nearest_nodes(graph, X=lon, Y=lat)
                safe_zones.append(nearest_node)
            except Exception as e:
                logger.warning(f"Could not find node for safe zone at {lon}, {lat}: {e}")

        return safe_zones

    @staticmethod
    def get_population_centers(city: str, graph: Any) -> List[Any]:
        """
        Get population center nodes for a city. Stateless operation.

        Args:
            city: City name
            graph: NetworkX graph

        Returns:
            List of population center node IDs
        """
        if not OSMNX_AVAILABLE or graph is None:
            return []

        city_lower = city.lower().replace(" ", "_")
        pop_center_coords = NetworkGraphService.POPULATION_CENTERS.get(city_lower, [])

        population_centers = []
        for lon, lat in pop_center_coords:
            try:
                nearest_node = ox.nearest_nodes(graph, X=lon, Y=lat)
                population_centers.append(nearest_node)
            except Exception as e:
                logger.warning(f"Could not find node for population center at {lon}, {lat}: {e}")

        return population_centers

    @staticmethod
    def get_node_coordinates(graph: Any, node_id: Any) -> Tuple[float, float]:
        """
        Get (x, y) coordinates for a node. Pure function.

        Args:
            graph: NetworkX graph
            node_id: Node identifier

        Returns:
            Tuple of (x, y) coordinates or (0, 0) if not found
        """
        if graph is None or node_id not in graph.nodes:
            return (0.0, 0.0)

        node_data = graph.nodes[node_id]
        return (node_data.get('x', 0.0), node_data.get('y', 0.0))

    @staticmethod
    def get_route_coordinates(graph: Any, route: List[Any]) -> List[List[float]]:
        """
        Extract coordinates from a route. Pure function.

        Args:
            graph: NetworkX graph
            route: List of node IDs

        Returns:
            List of [x, y] coordinate pairs
        """
        if graph is None:
            return []

        coords = []
        for node_id in route:
            if node_id in graph.nodes:
                x = graph.nodes[node_id].get('x', 0.0)
                y = graph.nodes[node_id].get('y', 0.0)
                coords.append([x, y])

        return coords

    @staticmethod
    def is_city_supported(city: str) -> bool:
        """
        Check if a city is supported. Pure function.

        Args:
            city: City name

        Returns:
            True if city is supported
        """
        city_lower = city.lower().replace(" ", "_")
        return city_lower in NetworkGraphService.CITY_CONFIGS

    @staticmethod
    def get_supported_cities() -> List[str]:
        """
        Get list of supported cities. Pure function.

        Returns:
            List of supported city names
        """
        return list(NetworkGraphService.CITY_CONFIGS.keys())
