"""
Unit tests for GraphManager service.
Tests the unified graph loading, caching, and performance optimizations.
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import networkx as nx

from services.graph_manager import GraphManager


class TestGraphManager:
    """Test suite for GraphManager service."""
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def graph_manager(self, temp_cache_dir):
        """Create GraphManager instance for testing."""
        return GraphManager(cache_dir=temp_cache_dir, max_cache_size=3)
    
    @pytest.fixture
    def mock_graph(self):
        """Create mock NetworkX graph for testing."""
        graph = nx.MultiDiGraph()
        graph.add_node(1, x=-0.1, y=51.5)
        graph.add_node(2, x=-0.2, y=51.6)
        graph.add_edge(1, 2)
        return graph
    
    def test_init(self, temp_cache_dir):
        """Test GraphManager initialization."""
        manager = GraphManager(cache_dir=temp_cache_dir, max_cache_size=5)
        
        assert manager.cache_dir == Path(temp_cache_dir)
        assert manager._max_cache_size == 5
        assert len(manager._graph_cache) == 0
        assert manager._cache_hits == 0
        assert manager._cache_misses == 0
        assert manager.cache_dir.exists()
    
    def test_supported_cities(self, graph_manager):
        """Test getting supported cities."""
        cities = graph_manager.get_supported_cities()
        
        assert isinstance(cities, list)
        assert "city_of_london" in cities
        assert "westminster" in cities
        assert "kensington_and_chelsea" in cities
    
    def test_unsupported_city(self, graph_manager):
        """Test handling of unsupported city."""
        result = graph_manager.load_graph("unsupported_city")
        
        assert result is None
        assert graph_manager._cache_misses == 1
    
    @patch('services.graph_manager.ox.graph_from_place')
    def test_load_graph_success(self, mock_osmnx, graph_manager, mock_graph):
        """Test successful graph loading."""
        mock_osmnx.return_value = mock_graph
        
        result = graph_manager.load_graph("city_of_london")
        
        assert result is not None
        assert isinstance(result, nx.MultiDiGraph)
        assert graph_manager._cache_misses == 1
        assert len(graph_manager._graph_cache) == 1
        mock_osmnx.assert_called_once()
    
    @patch('services.graph_manager.ox.graph_from_place')
    def test_load_graph_cache_hit(self, mock_osmnx, graph_manager, mock_graph):
        """Test cache hit on second load."""
        mock_osmnx.return_value = mock_graph
        
        # First load
        result1 = graph_manager.load_graph("city_of_london")
        assert result1 is not None
        
        # Second load should hit cache
        result2 = graph_manager.load_graph("city_of_london")
        assert result2 is not None
        assert result1 is result2  # Same object from cache
        
        assert graph_manager._cache_hits == 1
        assert graph_manager._cache_misses == 1
        assert mock_osmnx.call_count == 1  # Only called once
    
    @patch('services.graph_manager.ox.graph_from_place')
    def test_lru_cache_eviction(self, mock_osmnx, graph_manager, mock_graph):
        """Test LRU cache eviction when cache is full."""
        mock_osmnx.return_value = mock_graph
        
        # Load graphs to fill cache (max_cache_size = 3)
        cities = ["city_of_london", "westminster", "kensington_and_chelsea"]
        for city in cities:
            graph_manager.load_graph(city)
        
        assert len(graph_manager._graph_cache) == 3
        
        # Load one more graph - should evict oldest
        with patch.object(graph_manager, 'city_configs', {
            **graph_manager.city_configs,
            "test_city": {
                "place_name": "Test City",
                "network_type": "walk",
                "safe_zones": [],
                "population_centers": []
            }
        }):
            graph_manager.load_graph("test_city")
        
        assert len(graph_manager._graph_cache) == 3
        # First city should be evicted
        assert "city_of_london_graph" not in graph_manager._graph_cache
    
    @patch('services.graph_manager.ox.graph_from_place')
    def test_force_reload(self, mock_osmnx, graph_manager, mock_graph):
        """Test force reload bypasses cache."""
        mock_osmnx.return_value = mock_graph
        
        # First load
        graph_manager.load_graph("city_of_london")
        
        # Force reload should bypass cache
        result = graph_manager.load_graph("city_of_london", force_reload=True)
        
        assert result is not None
        assert mock_osmnx.call_count == 2  # Called twice
        assert graph_manager._cache_misses == 2  # Both counted as misses
    
    @pytest.mark.asyncio
    async def test_async_load_graph(self, graph_manager, mock_graph):
        """Test async graph loading."""
        with patch('services.graph_manager.ox.graph_from_place', return_value=mock_graph):
            result = await graph_manager.load_graph_async("city_of_london")
            
            assert result is not None
            assert isinstance(result, nx.MultiDiGraph)
    
    @pytest.mark.asyncio
    async def test_batch_load_graphs(self, graph_manager, mock_graph):
        """Test batch loading of multiple graphs."""
        with patch('services.graph_manager.ox.graph_from_place', return_value=mock_graph):
            cities = ["city_of_london", "westminster"]
            results = await graph_manager.batch_load_graphs(cities)
            
            assert len(results) == 2
            assert all(graph is not None for graph in results.values())
            assert "city_of_london" in results
            assert "westminster" in results
    
    def test_get_safe_zones(self, graph_manager, mock_graph):
        """Test getting safe zones for a city."""
        with patch('services.graph_manager.ox.nearest_nodes', return_value=1):
            safe_zones = graph_manager.get_safe_zones("city_of_london", mock_graph)
            
            assert isinstance(safe_zones, list)
            assert len(safe_zones) > 0
    
    def test_get_population_centers(self, graph_manager, mock_graph):
        """Test getting population centers for a city."""
        with patch('services.graph_manager.ox.nearest_nodes', return_value=1):
            pop_centers = graph_manager.get_population_centers("city_of_london", mock_graph)
            
            assert isinstance(pop_centers, list)
            assert len(pop_centers) > 0
    
    def test_calculate_node_distance(self, graph_manager, mock_graph):
        """Test node distance calculation."""
        distance = graph_manager.calculate_node_distance(mock_graph, 1, 2)
        
        assert isinstance(distance, float)
        assert distance > 0
    
    def test_calculate_node_distance_invalid_nodes(self, graph_manager, mock_graph):
        """Test node distance calculation with invalid nodes."""
        distance = graph_manager.calculate_node_distance(mock_graph, 999, 1000)
        
        assert distance == float('inf')
    
    def test_clear_cache_specific_city(self, graph_manager, mock_graph):
        """Test clearing cache for specific city."""
        with patch('services.graph_manager.ox.graph_from_place', return_value=mock_graph):
            # Load a graph
            graph_manager.load_graph("city_of_london")
            assert len(graph_manager._graph_cache) == 1
            
            # Clear specific city
            graph_manager.clear_cache("city_of_london")
            assert len(graph_manager._graph_cache) == 0
    
    def test_clear_cache_all(self, graph_manager, mock_graph):
        """Test clearing all cache."""
        with patch('services.graph_manager.ox.graph_from_place', return_value=mock_graph):
            # Load multiple graphs
            graph_manager.load_graph("city_of_london")
            graph_manager.load_graph("westminster")
            assert len(graph_manager._graph_cache) == 2
            
            # Clear all cache
            graph_manager.clear_cache()
            assert len(graph_manager._graph_cache) == 0
    
    def test_performance_stats(self, graph_manager, mock_graph):
        """Test performance statistics."""
        with patch('services.graph_manager.ox.graph_from_place', return_value=mock_graph):
            # Generate some activity
            graph_manager.load_graph("city_of_london")  # Cache miss
            graph_manager.load_graph("city_of_london")  # Cache hit
            
            stats = graph_manager.get_performance_stats()
            
            assert "cache_stats" in stats
            assert "load_times" in stats
            assert "avg_load_time" in stats
            assert "cached_cities" in stats
            
            assert stats["cache_stats"]["hits"] == 1
            assert stats["cache_stats"]["misses"] == 1
            assert stats["cache_stats"]["hit_rate"] == 0.5
    
    @patch('services.graph_manager.ox.graph_from_place')
    def test_disk_cache_save_load(self, mock_osmnx, graph_manager, mock_graph):
        """Test saving and loading from disk cache."""
        mock_osmnx.return_value = mock_graph
        
        # Load graph (should save to disk)
        result1 = graph_manager.load_graph("city_of_london")
        assert result1 is not None
        
        # Clear memory cache
        graph_manager._graph_cache.clear()
        
        # Load again (should load from disk)
        result2 = graph_manager.load_graph("city_of_london")
        assert result2 is not None
        
        # Should only call OSMnx once (second load from disk)
        assert mock_osmnx.call_count == 1
    
    @patch('services.graph_manager.ox.graph_from_place')
    def test_error_handling_osmnx_failure(self, mock_osmnx, graph_manager):
        """Test error handling when OSMnx fails."""
        mock_osmnx.side_effect = Exception("OSMnx error")
        
        result = graph_manager.load_graph("city_of_london")
        
        assert result is None
        assert graph_manager._cache_misses == 1
    
    def test_preload_graphs(self, graph_manager, mock_graph):
        """Test preloading graphs."""
        with patch('services.graph_manager.ox.graph_from_place', return_value=mock_graph):
            cities = ["city_of_london", "westminster"]
            graph_manager.preload_graphs(cities)
            
            # Check that graphs are cached
            assert len(graph_manager._graph_cache) == 2
            assert "city_of_london_graph" in graph_manager._graph_cache
            assert "westminster_graph" in graph_manager._graph_cache
    
    def test_cache_access_order_update(self, graph_manager, mock_graph):
        """Test that cache access order is properly updated."""
        with patch('services.graph_manager.ox.graph_from_place', return_value=mock_graph):
            # Load graphs
            graph_manager.load_graph("city_of_london")
            graph_manager.load_graph("westminster")
            
            # Access first graph again
            graph_manager.load_graph("city_of_london")
            
            # Check access order (city_of_london should be last)
            assert graph_manager._cache_access_order[-1] == "city_of_london_graph"


class TestGraphManagerIntegration:
    """Integration tests for GraphManager with real dependencies."""
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_real_city_configs(self, temp_cache_dir):
        """Test that city configurations are valid."""
        manager = GraphManager(cache_dir=temp_cache_dir)
        
        for city, config in manager.city_configs.items():
            assert "place_name" in config
            assert "network_type" in config
            assert "safe_zones" in config
            assert "population_centers" in config
            
            assert isinstance(config["safe_zones"], list)
            assert isinstance(config["population_centers"], list)
    
    @pytest.mark.asyncio
    async def test_concurrent_loading(self, temp_cache_dir):
        """Test concurrent loading of graphs."""
        manager = GraphManager(cache_dir=temp_cache_dir)
        
        with patch('services.graph_manager.ox.graph_from_place') as mock_osmnx:
            # Create different mock graphs for each city
            mock_graphs = {}
            for city in ["city_of_london", "westminster"]:
                graph = nx.MultiDiGraph()
                graph.add_node(1, x=-0.1, y=51.5)
                mock_graphs[city] = graph
            
            def side_effect(place_name, **kwargs):
                for city, config in manager.city_configs.items():
                    if config["place_name"] == place_name:
                        return mock_graphs.get(city, mock_graphs["city_of_london"])
                return mock_graphs["city_of_london"]
            
            mock_osmnx.side_effect = side_effect
            
            # Load graphs concurrently
            tasks = [
                manager.load_graph_async("city_of_london"),
                manager.load_graph_async("westminster")
            ]
            
            results = await asyncio.gather(*tasks)
            
            assert all(result is not None for result in results)
            assert len(manager._graph_cache) == 2
