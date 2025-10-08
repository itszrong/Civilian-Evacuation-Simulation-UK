"""
Graph Manager Service
Handles graph loading, caching, and management for evacuation simulations.
Extracted from multi_city_simulation.py for better separation of concerns.
"""

import networkx as nx
import osmnx as ox
import geopandas as gpd
from shapely.geometry import Point
from typing import Dict, List, Tuple, Optional, Any
import structlog
from pathlib import Path
import pickle
import asyncio
from concurrent.futures import ThreadPoolExecutor
import random

from .error_handler import get_error_handler, handle_graph_errors

logger = structlog.get_logger(__name__)
error_handler = get_error_handler("graph_manager")

# Global thread pool for async operations - optimized for I/O bound tasks
_thread_pool = ThreadPoolExecutor(max_workers=20, thread_name_prefix="graph_loader")


class GraphManager:
    """
    Unified graph management service for all evacuation simulations.
    Replaces multiple graph loading implementations across the codebase.
    """

    def __init__(self, cache_dir: Optional[str] = None, max_cache_size: int = 10):
        """
        Initialize GraphManager with enhanced caching and performance optimizations.
        
        Args:
            cache_dir: Directory for caching graphs. Defaults to backend/cache/graphs
            max_cache_size: Maximum number of graphs to keep in memory cache
        """
        self.cache_dir = Path(cache_dir) if cache_dir else Path("backend/cache/graphs")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Enhanced in-memory cache with LRU eviction
        self._graph_cache = {}
        self._cache_access_order = []  # Track access order for LRU
        self._max_cache_size = max_cache_size
        
        # Connection pool for concurrent operations
        self._loading_locks = {}  # Prevent duplicate loading of same city
        
        # Performance tracking
        self._load_times = {}
        self._cache_hits = 0
        self._cache_misses = 0
        
        # City configurations for supported cities
        self.city_configs = {
            "city_of_london": {
                "place_name": "City of London, London, UK",
                "network_type": "walk",
                "safe_zones": ["Bank Station", "Liverpool Street", "Moorgate"],
                "population_centers": ["Bank", "Cheapside", "Guildhall"]
            },
            "westminster": {
                "place_name": "City of Westminster, London, England", 
                "network_type": "walk",
                "center": (51.4975, -0.1357),
                "dist": 3000,
                "safe_zones": ["Westminster Bridge", "Victoria Station", "Green Park"],
                "population_centers": ["Oxford Circus", "Piccadilly Circus", "Westminster"]
            },
            "kensington_and_chelsea": {
                "place_name": "Kensington and Chelsea, London, UK",
                "network_type": "walk", 
                "safe_zones": ["Hyde Park", "Kensington Gardens", "Chelsea Bridge"],
                "population_centers": ["South Kensington", "Knightsbridge", "Chelsea"]
            }
        }

    async def load_graph_async(self, city: str, force_reload: bool = False) -> Optional[nx.MultiDiGraph]:
        """
        Asynchronously load graph for a city with caching.
        
        Args:
            city: City name (must be in city_configs)
            force_reload: Force reload even if cached
            
        Returns:
            NetworkX graph or None if failed
        """
        return await asyncio.get_event_loop().run_in_executor(
            _thread_pool, self.load_graph, city, force_reload
        )

    def load_graph(self, city: str, force_reload: bool = False) -> Optional[nx.MultiDiGraph]:
        """
        Load graph for a city with enhanced caching and performance optimizations.
        
        Args:
            city: City name (must be in city_configs)
            force_reload: Force reload even if cached
            
        Returns:
            NetworkX graph or None if failed
        """
        import time
        start_time = time.time()
        
        if city not in self.city_configs:
            error = error_handler.handle_error(
                error=f"Unsupported city: {city}",
                error_code="UNSUPPORTED_CITY",
                operation_name="load_graph",
                additional_data={"city": city, "supported_cities": list(self.city_configs.keys())}
            )
            logger.error(f"Unsupported city: {city}. Supported: {list(self.city_configs.keys())}")
            return None

        # Check in-memory cache first with LRU management
        cache_key = f"{city}_graph"
        if not force_reload and cache_key in self._graph_cache:
            logger.info(f"Cache HIT: Using in-memory cached graph for {city}")
            self._cache_hits += 1
            self._update_cache_access(cache_key)
            return self._graph_cache[cache_key]
        
        self._cache_misses += 1
        logger.info(f"Cache MISS: Loading graph for {city} (hits: {self._cache_hits}, misses: {self._cache_misses})")

        # Check disk cache
        cache_file = self.cache_dir / f"{city}_graph.pkl"
        if not force_reload and cache_file.exists():
            try:
                logger.info(f"Loading cached graph for {city} from disk")
                with open(cache_file, 'rb') as f:
                    graph = pickle.load(f)
                self._graph_cache[cache_key] = graph
                return graph
            except Exception as e:
                logger.warning(f"Failed to load cached graph for {city}: {e}")

        # Load from OSMnx
        try:
            logger.info(f"Loading graph for {city} from OSMnx")
            config = self.city_configs[city]
            
            # Try place-based loading first
            try:
                graph = ox.graph_from_place(
                    config["place_name"],
                    network_type=config["network_type"],
                    simplify=True
                )
                logger.info(f"Successfully loaded graph using place name: {config['place_name']}")
            except Exception as e:
                logger.warning(f"Place-based loading failed for {city}: {e}")
                # Fallback to center-based loading if coordinates are available
                if "center" in config and "dist" in config:
                    logger.info(f"Trying center-based loading for {city}")
                    graph = ox.graph_from_point(
                        config["center"],
                        dist=config["dist"],
                        network_type=config["network_type"],
                        simplify=True
                    )
                    logger.info(f"Successfully loaded graph using center coordinates: {config['center']}")
                else:
                    raise e
            
            # Add node coordinates as attributes for faster access
            for node, data in graph.nodes(data=True):
                if 'x' not in data or 'y' not in data:
                    data['x'] = data.get('lon', 0)
                    data['y'] = data.get('lat', 0)

            # Cache to disk
            try:
                with open(cache_file, 'wb') as f:
                    pickle.dump(graph, f)
                logger.info(f"Cached graph for {city} to disk")
            except Exception as e:
                logger.warning(f"Failed to cache graph for {city}: {e}")

            # Cache in memory with LRU management
            self._add_to_cache(cache_key, graph)
            
            # Track performance
            load_time = time.time() - start_time
            self._load_times[city] = load_time
            
            logger.info(f"Successfully loaded graph for {city}: {len(graph.nodes)} nodes, {len(graph.edges)} edges (took {load_time:.2f}s)")
            return graph
            
        except Exception as e:
            error = error_handler.handle_error(
                error=e,
                error_code="GRAPH_LOAD_FAILED",
                operation_name="load_graph",
                additional_data={"city": city, "force_reload": force_reload}
            )
            logger.error(f"Failed to load graph for {city}: {e}")
            return None

    def get_safe_zones(self, city: str, graph: nx.MultiDiGraph) -> List[int]:
        """
        Get safe zone nodes for a city.
        
        Args:
            city: City name
            graph: NetworkX graph
            
        Returns:
            List of node IDs representing safe zones
        """
        if city not in self.city_configs:
            return []

        config = self.city_configs[city]
        safe_zone_names = config.get("safe_zones", [])
        
        # For now, return random nodes as safe zones
        # In production, this would use actual safe zone coordinates
        nodes = list(graph.nodes())
        if len(nodes) < len(safe_zone_names):
            return nodes
            
        return random.sample(nodes, min(len(safe_zone_names), len(nodes)))

    def get_population_centers(self, city: str, graph: nx.MultiDiGraph) -> List[int]:
        """
        Get population center nodes for a city.
        
        Args:
            city: City name
            graph: NetworkX graph
            
        Returns:
            List of node IDs representing population centers
        """
        if city not in self.city_configs:
            return []

        config = self.city_configs[city]
        pop_center_names = config.get("population_centers", [])
        
        # For now, return random nodes as population centers
        # In production, this would use actual population density data
        nodes = list(graph.nodes())
        if len(nodes) < len(pop_center_names):
            return nodes
            
        return random.sample(nodes, min(len(pop_center_names), len(nodes)))

    def calculate_node_distance(self, graph: nx.MultiDiGraph, node1: int, node2: int) -> float:
        """
        Calculate Euclidean distance between two nodes.
        
        Args:
            graph: NetworkX graph
            node1: First node ID
            node2: Second node ID
            
        Returns:
            Distance in meters (approximate)
        """
        try:
            n1_data = graph.nodes[node1]
            n2_data = graph.nodes[node2]
            
            # Use x,y coordinates (longitude, latitude)
            x1, y1 = n1_data.get('x', 0), n1_data.get('y', 0)
            x2, y2 = n2_data.get('x', 0), n2_data.get('y', 0)
            
            # Approximate conversion to meters (rough for London area)
            dx = (x2 - x1) * 111320 * 0.7  # longitude to meters, adjusted for latitude
            dy = (y2 - y1) * 110540  # latitude to meters
            
            return (dx**2 + dy**2)**0.5
            
        except KeyError:
            return float('inf')

    def get_supported_cities(self) -> List[str]:
        """Get list of supported cities."""
        return list(self.city_configs.keys())

    def clear_cache(self, city: Optional[str] = None):
        """
        Clear graph cache.
        
        Args:
            city: Specific city to clear, or None to clear all
        """
        if city:
            cache_key = f"{city}_graph"
            self._graph_cache.pop(cache_key, None)
            
            cache_file = self.cache_dir / f"{city}_graph.pkl"
            if cache_file.exists():
                cache_file.unlink()
                
            logger.info(f"Cleared cache for {city}")
        else:
            self._graph_cache.clear()
            
            for cache_file in self.cache_dir.glob("*_graph.pkl"):
                cache_file.unlink()
                
            logger.info("Cleared all graph cache")

    def preload_graphs(self, cities: Optional[List[str]] = None):
        """
        Preload graphs for specified cities.
        
        Args:
            cities: List of cities to preload, or None for all supported cities
        """
        cities_to_load = cities or list(self.city_configs.keys())
        
        for city in cities_to_load:
            try:
                self.load_graph(city)
                logger.info(f"Preloaded graph for {city}")
            except Exception as e:
                logger.error(f"Failed to preload graph for {city}: {e}")

    async def batch_load_graphs(self, cities: List[str]) -> Dict[str, Optional[nx.MultiDiGraph]]:
        """
        Load multiple graphs concurrently for maximum performance.
        
        Args:
            cities: List of cities to load
            
        Returns:
            Dictionary mapping city names to loaded graphs
        """
        logger.info(f"Batch loading {len(cities)} graphs concurrently")
        
        # Create concurrent loading tasks
        tasks = [self.load_graph_async(city) for city in cities]
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        graph_results = {}
        for city, result in zip(cities, results):
            if isinstance(result, Exception):
                logger.error(f"Failed to load graph for {city}: {result}")
                graph_results[city] = None
            else:
                graph_results[city] = result
        
        successful_loads = sum(1 for g in graph_results.values() if g is not None)
        logger.info(f"Batch loading completed: {successful_loads}/{len(cities)} successful")
        
        return graph_results

    def _add_to_cache(self, cache_key: str, graph: nx.MultiDiGraph):
        """Add graph to in-memory cache with LRU eviction."""
        # Remove if already exists to update position
        if cache_key in self._graph_cache:
            self._cache_access_order.remove(cache_key)
        
        # Add to cache
        self._graph_cache[cache_key] = graph
        self._cache_access_order.append(cache_key)
        
        # Evict oldest if cache is full
        while len(self._graph_cache) > self._max_cache_size:
            oldest_key = self._cache_access_order.pop(0)
            del self._graph_cache[oldest_key]
            logger.debug(f"Evicted {oldest_key} from cache (LRU)")

    def _update_cache_access(self, cache_key: str):
        """Update cache access order for LRU management."""
        if cache_key in self._cache_access_order:
            self._cache_access_order.remove(cache_key)
            self._cache_access_order.append(cache_key)

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for monitoring and optimization."""
        total_requests = self._cache_hits + self._cache_misses
        cache_hit_rate = self._cache_hits / total_requests if total_requests > 0 else 0
        
        return {
            "cache_stats": {
                "hits": self._cache_hits,
                "misses": self._cache_misses,
                "hit_rate": cache_hit_rate,
                "cache_size": len(self._graph_cache),
                "max_cache_size": self._max_cache_size
            },
            "load_times": self._load_times.copy(),
            "avg_load_time": sum(self._load_times.values()) / len(self._load_times) if self._load_times else 0,
            "cached_cities": list(self._graph_cache.keys())
        }
