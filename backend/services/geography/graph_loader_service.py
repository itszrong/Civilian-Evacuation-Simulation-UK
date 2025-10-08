"""
Graph Loader Service
Handles street network graph loading with caching and fallback strategies.
Extracted from multi_city_orchestrator.py to improve code organization.
"""

from typing import Dict, List, Optional
import threading
from pathlib import Path
import structlog
import osmnx as ox
import networkx as nx

from services.graph_manager import GraphManager
from services.geography.city_resolver_service import CityResolverService

logger = structlog.get_logger(__name__)


class GraphLoaderService:
    """Service for loading and caching street network graphs with fallback strategies."""
    
    def __init__(
        self,
        city_resolver: Optional[CityResolverService] = None,
        graph_manager: Optional[GraphManager] = None,
        cache_dir: str = "backend/cache/graphs"
    ):
        """
        Initialize the graph loader service.
        
        Args:
            city_resolver: City resolver service for name resolution
            graph_manager: Graph manager for disk caching
            cache_dir: Directory for graph cache
        """
        self.city_resolver = city_resolver or CityResolverService()
        self.graph_manager = graph_manager or GraphManager(cache_dir=cache_dir)
        
        # In-memory cache for loaded graphs
        self.graph_cache: Dict[str, nx.MultiDiGraph] = {}
        
        # Top cities to cache on initialization
        self.top_cities_to_cache = [
            "city_of_london",
            "kensington_and_chelsea",
            "westminster"
        ]
    
    def initialize_cache(self, cities: Optional[List[str]] = None):
        """
        Initialize graph cache for specified cities in background thread.
        
        Args:
            cities: List of city names to cache. If None, uses top_cities_to_cache.
        """
        cities_to_load = cities or self.top_cities_to_cache
        
        def load_graphs():
            logger.info("🚀 Initializing graph cache for top cities...")
            for city in cities_to_load:
                try:
                    logger.info(f"📡 Caching graph for {city}...")
                    
                    # Use unified GraphManager with disk caching
                    graph = self.graph_manager.load_graph(
                        city=city.replace(" ", "_"),
                        force_reload=False
                    )
                    
                    if graph is not None:
                        # Store in instance cache
                        self.graph_cache[city] = graph
                        logger.info(
                            f"✅ Cached {city}: {len(graph.nodes)} nodes, {len(graph.edges)} edges"
                        )
                    else:
                        logger.warning(f"❌ Failed to cache graph for {city}")
                except Exception as e:
                    logger.error(f"Failed to cache graph for {city}: {e}")
            
            logger.info(f"🎉 Graph cache initialized: {len(self.graph_cache)} cities cached")
        
        # Load graphs in background thread
        cache_thread = threading.Thread(target=load_graphs, daemon=True)
        cache_thread.start()
    
    async def load_graph_async(self, city: str, force_reload: bool = False) -> Optional[nx.MultiDiGraph]:
        """
        Async version of load_graph for compatibility with async orchestrators.
        
        Args:
            city: City name to load
            force_reload: Force reload even if cached
            
        Returns:
            NetworkX graph or None if all strategies fail
        """
        # Run the synchronous load_graph in a thread pool
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.load_graph, city, force_reload)
    
    def load_graph(self, city: str, force_reload: bool = False) -> Optional[nx.MultiDiGraph]:
        """
        Load graph with multiple fallback strategies.
        
        Args:
            city: City name to load
            force_reload: Force reload even if cached
            
        Returns:
            NetworkX graph or None if all strategies fail
        """
        # Sanitize city name
        city = self.city_resolver.sanitize_city_name(city)
        
        # Check in-memory cache first
        if not force_reload and city in self.graph_cache:
            logger.info(f"⚡ Using cached graph for {city} (instant)")
            return self.graph_cache[city]
        
        # Try loading with fallback strategies
        graph = self._load_with_fallbacks(city)
        
        # Cache if successful
        if graph is not None:
            self.graph_cache[city] = graph
            logger.info(f"✅ Loaded and cached {city}: {len(graph.nodes)} nodes, {len(graph.edges)} edges")
        
        return graph
    
    def _load_with_fallbacks(self, city: str) -> Optional[nx.MultiDiGraph]:
        """
        Load city graph with multiple fallback strategies.
        
        Args:
            city: Sanitized city name
            
        Returns:
            Graph or None if all strategies fail
        """
        # Strategy 1: Try query variations
        city_variations = self.city_resolver.get_query_variations(city)
        
        for i, city_query in enumerate(city_variations):
            try:
                logger.info(
                    f"Attempting to load {city} with query: '{city_query}' "
                    f"(attempt {i+1}/{len(city_variations)})"
                )
                graph = ox.graph_from_place(city_query, network_type='walk')
                logger.info(f"Successfully loaded {city} using query: '{city_query}'")
                return graph
            except Exception as e:
                logger.warning(f"Failed to load {city} with query '{city_query}': {e}")
                continue
        
        # Strategy 2: Try bounding box approach
        try:
            logger.info(f"Trying bounding box approach for {city}")
            return self.city_resolver.load_by_bounding_box(city)
        except Exception as e:
            logger.error(f"All geocoding strategies failed for {city}: {e}")
            return None
    
    def load_borough_graph(self, city: str) -> Optional[nx.MultiDiGraph]:
        """
        Load borough-specific street network for London boroughs.
        
        Args:
            city: Borough name
            
        Returns:
            Graph or None if loading fails
        """
        try:
            logger.info(f"Loading borough-specific network for {city}")
            
            # Get place mapping for this borough
            place_query = self.city_resolver.get_place_mapping(city)
            
            if place_query is None:
                # Fallback to generic query
                place_query = f"{city.title()}, London, UK"
            
            # Load the specific borough network
            graph = ox.graph_from_place(place_query, network_type='all')
            logger.info(
                f"Loaded {city} graph with {graph.number_of_nodes()} nodes "
                f"and {graph.number_of_edges()} edges"
            )
            
            return graph
            
        except Exception as e:
            logger.warning(f"Failed to load {city} specific network: {e}")
            return None
    
    def get_cached_graph(self, city: str) -> Optional[nx.MultiDiGraph]:
        """
        Get graph from cache without loading.
        
        Args:
            city: City name
            
        Returns:
            Cached graph or None if not in cache
        """
        city = self.city_resolver.sanitize_city_name(city)
        return self.graph_cache.get(city)
    
    def clear_cache(self, city: Optional[str] = None):
        """
        Clear graph cache.
        
        Args:
            city: Specific city to clear, or None to clear all
        """
        if city is not None:
            city = self.city_resolver.sanitize_city_name(city)
            if city in self.graph_cache:
                del self.graph_cache[city]
                logger.info(f"Cleared cache for {city}")
        else:
            self.graph_cache.clear()
            logger.info("Cleared all graph cache")
    
    def get_cache_stats(self) -> Dict[str, any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        return {
            "cached_cities": list(self.graph_cache.keys()),
            "cache_size": len(self.graph_cache),
            "total_nodes": sum(len(g.nodes) for g in self.graph_cache.values()),
            "total_edges": sum(len(g.edges) for g in self.graph_cache.values())
        }
