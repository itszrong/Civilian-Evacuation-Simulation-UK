"""
Simulation service for London Evacuation Planning Tool.

This module handles graph-based evacuation simulation using NetworkX and OSMnx
for London street network analysis with capacity-aware routing.
"""

import pickle
import math
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import asyncio
import json
import base64
from io import BytesIO

import networkx as nx
import structlog
from pydantic import BaseModel

try:
    import osmnx as ox
    OSMNX_AVAILABLE = True
except ImportError:
    OSMNX_AVAILABLE = False
    ox = None

from core.config import get_settings
from models.schemas import ScenarioConfig, SimulationMetrics
from services.mesa_simulation.mesa_executor import MesaSimulationExecutor
from services.visualization.mesa_visualizer import MesaVisualizationService

logger = structlog.get_logger(__name__)


class EdgeAttributes(BaseModel):
    """Attributes for graph edges representing roads."""
    length: float
    speed: float  # km/h
    capacity: float  # vehicles per hour
    is_bridge: bool = False
    borough: str = ""
    road_class: str = ""
    original_capacity: float = 0.0


class NodeAttributes(BaseModel):
    """Attributes for graph nodes representing intersections."""
    x: float
    y: float
    elevation: Optional[float] = None
    is_poi: bool = False
    poi_type: Optional[str] = None


class SimulationState(BaseModel):
    """State of the simulation at a given time step."""
    time_step: int
    evacuated_count: int
    queue_lengths: Dict[str, float]
    active_routes: Dict[str, List[str]]
    completion_times: Dict[str, int]


class LondonGraphService:
    """
    DEPRECATED: Service for managing London street network graph.
    Use GraphManager from graph_manager.py instead for new code.
    """

    def __init__(self):
        self.settings = get_settings()
        # Use the new GraphManager for unified graph loading
        from .graph_manager import GraphManager
        self.graph_manager = GraphManager(cache_dir=str(Path(self.settings.LONDON_GRAPH_CACHE_PATH).parent))
        self.graph: Optional[nx.MultiDiGraph] = None
        
    async def get_london_graph(self) -> nx.MultiDiGraph:
        """
        Get London street network graph, loading from cache or creating new.
        REFACTORED: Now uses unified GraphManager for consistency.
        """
        if self.graph is not None:
            return self.graph
        
        # Use GraphManager for unified loading
        logger.info("Loading London graph using unified GraphManager")
        self.graph = await self.graph_manager.load_graph_async("city_of_london")
        
        if self.graph is None:
            # Fallback to synthetic graph
            logger.warning("Failed to load real graph, creating synthetic fallback")
            self.graph = self._create_synthetic_london_graph()
        
        logger.info("London graph loaded", 
                   nodes=self.graph.number_of_nodes(),
                   edges=self.graph.number_of_edges())
        
        return self.graph
    
    async def _create_london_graph(self) -> nx.MultiDiGraph:
        """Create London street network graph."""
        if not OSMNX_AVAILABLE:
            logger.warning("OSMnx not available, creating synthetic graph")
            return self._create_synthetic_london_graph()
        
        try:
            # Define London bounding box (rough approximation)
            # Central London area for faster processing
            north, south, east, west = 51.6, 51.4, 0.2, -0.5
            
            logger.info("Downloading London street network from OpenStreetMap")
            
            # Download street network
            G = ox.graph_from_bbox(
                north=north, south=south, east=east, west=west,
                network_type='drive',
                simplify=True,
                retain_all=False
            )
            
            logger.info("Processing London graph", 
                       nodes=G.number_of_nodes(),
                       edges=G.number_of_edges())
            
            # Add capacity and other attributes
            self._add_capacity_attributes(G)
            self._add_poi_information(G)
            
            return G
            
        except Exception as e:
            logger.error("Failed to create OSMnx graph", error=str(e))
            logger.info("Falling back to synthetic graph")
            return self._create_synthetic_london_graph()
    
    def _create_synthetic_london_graph(self) -> nx.MultiDiGraph:
        """Create a synthetic London-like graph for testing."""
        logger.info("Creating synthetic London graph")
        
        G = nx.MultiDiGraph()
        
        # Create a grid-like structure representing central London
        grid_size = 20
        spacing = 0.01  # Roughly 1km spacing
        
        # Base coordinates (roughly central London)
        base_lat, base_lon = 51.5074, -0.1278
        
        # Create nodes
        nodes = {}
        for i in range(grid_size):
            for j in range(grid_size):
                node_id = f"n_{i}_{j}"
                lat = base_lat + (i - grid_size/2) * spacing
                lon = base_lon + (j - grid_size/2) * spacing
                
                nodes[node_id] = {
                    'x': lon,
                    'y': lat,
                    'is_poi': False
                }
                
                # Mark some nodes as POIs
                if (i, j) in [(5, 5), (15, 15), (10, 8), (8, 12)]:
                    nodes[node_id]['is_poi'] = True
                    nodes[node_id]['poi_type'] = 'hospital'
        
        G.add_nodes_from(nodes.items())
        
        # Create edges (roads)
        for i in range(grid_size):
            for j in range(grid_size):
                current = f"n_{i}_{j}"
                
                # Connect to adjacent nodes
                for di, dj in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                    ni, nj = i + di, j + dj
                    if 0 <= ni < grid_size and 0 <= nj < grid_size:
                        neighbor = f"n_{ni}_{nj}"
                        
                        # Calculate edge attributes
                        length = spacing * 111000  # Convert to meters approximately
                        
                        # Vary road types
                        if i % 5 == 0 or j % 5 == 0:  # Major roads
                            capacity = 2000  # vehicles/hour
                            speed = 50  # km/h
                            road_class = "primary"
                        else:  # Minor roads
                            capacity = 800
                            speed = 30
                            road_class = "secondary"
                        
                        # Mark some edges as bridges
                        is_bridge = (i == grid_size//2 and 5 <= j <= 15)  # "Thames" crossing
                        
                        edge_attrs = {
                            'length': length,
                            'speed': speed,
                            'capacity': capacity,
                            'original_capacity': capacity,
                            'is_bridge': is_bridge,
                            'road_class': road_class,
                            'borough': self._get_synthetic_borough(i, j, grid_size)
                        }
                        
                        G.add_edge(current, neighbor, **edge_attrs)
        
        logger.info("Synthetic London graph created", 
                   nodes=G.number_of_nodes(),
                   edges=G.number_of_edges())
        
        return G
    
    def _get_synthetic_borough(self, i: int, j: int, grid_size: int) -> str:
        """Assign synthetic borough names based on grid position."""
        boroughs = [
            "Westminster", "Camden", "Islington", "Hackney",
            "Tower_Hamlets", "Southwark", "Lambeth", "Wandsworth"
        ]
        
        # Simple assignment based on grid quadrants
        if i < grid_size // 2:
            if j < grid_size // 2:
                return boroughs[0]  # Westminster
            else:
                return boroughs[1]  # Camden
        else:
            if j < grid_size // 2:
                return boroughs[6]  # Lambeth
            else:
                return boroughs[5]  # Southwark
    
    def _add_capacity_attributes(self, G: nx.MultiDiGraph) -> None:
        """Add capacity attributes to graph edges."""
        for u, v, k, data in G.edges(keys=True, data=True):
            # Get highway type
            highway = data.get('highway', 'residential')
            
            # Assign capacity based on road type
            if highway in ['motorway', 'trunk']:
                capacity = 4000  # vehicles/hour
                speed = 80
            elif highway in ['primary', 'secondary']:
                capacity = 2000
                speed = 50
            elif highway in ['tertiary', 'residential']:
                capacity = 800
                speed = 30
            else:
                capacity = 400
                speed = 20
            
            # Update edge attributes
            data['capacity'] = capacity
            data['original_capacity'] = capacity
            data['speed'] = speed if 'maxspeed' not in data else data.get('maxspeed', speed)
            data['is_bridge'] = 'bridge' in data.get('highway', '')
            data['road_class'] = highway
    
    def _add_poi_information(self, G: nx.MultiDiGraph) -> None:
        """Add points of interest to graph nodes."""
        # This is a simplified implementation
        # In practice, you'd query OSM for actual POIs
        
        poi_locations = [
            # Major hospitals (approximate coordinates)
            (51.4994, -0.1141, "StThomasHospital"),
            (51.5055, -0.0929, "KingsCollegeHospital"),
            # Major landmarks
            (51.5007, -0.1246, "BigBen"),
            (51.5033, -0.1195, "LondonEye"),
        ]
        
        for lat, lon, poi_name in poi_locations:
            # Find nearest node
            try:
                if OSMNX_AVAILABLE:
                    nearest_node = ox.distance.nearest_nodes(G, lon, lat)
                    G.nodes[nearest_node]['is_poi'] = True
                    G.nodes[nearest_node]['poi_type'] = poi_name
            except Exception:
                # Skip if can't find nearest node
                pass
    
    async def _cache_graph(self) -> None:
        """Cache the graph to disk."""
        try:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self._cache_path, 'wb') as f:
                pickle.dump(self.graph, f)
            
            logger.info("London graph cached successfully")
        except Exception as e:
            logger.error("Failed to cache graph", error=str(e))


class EvacuationSimulator:
    """Evacuation simulation engine."""

    def __init__(self, graph_service: LondonGraphService):
        self.graph_service = graph_service
        self.settings = get_settings()
        self.mesa_executor = MesaSimulationExecutor()
        self.mesa_visualizer = MesaVisualizationService()
    
    async def simulate_scenario(self, scenario: ScenarioConfig) -> SimulationMetrics:
        """Simulate an evacuation scenario and return metrics."""
        logger.info("Starting evacuation simulation", scenario_id=scenario.id)
        
        # Get the base graph
        graph = await self.graph_service.get_london_graph()
        
        # Apply scenario modifications
        modified_graph = self._apply_scenario_modifications(graph.copy(), scenario)
        
        # Run simulation
        simulation_results = await self._run_simulation(modified_graph, scenario)
        
        # Calculate metrics
        metrics = self._calculate_metrics(simulation_results, scenario)
        
        logger.info("Evacuation simulation completed", 
                   scenario_id=scenario.id,
                   clearance_time=metrics.clearance_time,
                   fairness_index=metrics.fairness_index)
        
        return metrics
    
    async def simulate_scenario_with_visualizations(
        self, 
        scenario: ScenarioConfig
    ) -> Tuple[SimulationMetrics, Dict[str, str]]:
        """
        Simulate an evacuation scenario and generate dual visualizations.
        
        Returns:
            Tuple of (metrics, visualizations_dict) where visualizations_dict contains:
            {
                'primary': 'path/to/primary_viz.html',      # Existing visualization
                'mesa_routes': 'path/to/mesa_routes.html'   # Mesa routes visualization
            }
        """
        logger.info("Starting simulation with dual visualizations", scenario_id=scenario.id)
        
        # Get the base graph
        graph = await self.graph_service.get_london_graph()
        
        # Apply scenario modifications
        modified_graph = self._apply_scenario_modifications(graph.copy(), scenario)
        
        # Run simulation
        simulation_results = await self._run_simulation(modified_graph, scenario)
        
        # Generate Mesa routes visualization
        mesa_viz_path = await self.mesa_visualizer.create_routes_from_mesa_results(
            mesa_results=simulation_results,
            graph=modified_graph,
            simulation_id=scenario.id
        )
        
        # Calculate metrics
        metrics = self._calculate_metrics(simulation_results, scenario)
        
        # Return metrics and visualization paths
        visualizations = {
            'mesa_routes': mesa_viz_path
            # 'primary' would be added by the caller if they have an existing visualization
        }
        
        logger.info("Simulation with visualizations completed", 
                   scenario_id=scenario.id,
                   mesa_viz=mesa_viz_path)
        
        return metrics, visualizations
    
    def _apply_scenario_modifications(self, graph: nx.MultiDiGraph, 
                                    scenario: ScenarioConfig) -> nx.MultiDiGraph:
        """Apply scenario modifications to the graph."""
        
        # Apply closures
        for closure in scenario.closures:
            if closure.type == "polygon_cordon":
                self._apply_area_closure(graph, closure.area)
        
        # Apply capacity changes
        for change in scenario.capacity_changes:
            self._apply_capacity_change(graph, change.edge_selector, change.multiplier)
        
        # Apply protected corridors
        for corridor in scenario.protected_corridors:
            if corridor.rule == "increase_capacity":
                self._apply_capacity_change(graph, corridor.name, corridor.multiplier)
        
        return graph
    
    def _apply_area_closure(self, graph: nx.MultiDiGraph, area: str) -> None:
        """Apply area closure to the graph."""
        # Simplified implementation - in practice, would use proper polygon geometry
        
        if area.lower() == "westminster":
            # Close roads in Westminster area (simplified as central grid area)
            nodes_to_close = []
            for node, data in graph.nodes(data=True):
                # Simple geometric check - in practice use proper polygon intersection
                if self._is_in_westminster_area(data.get('x', 0), data.get('y', 0)):
                    nodes_to_close.append(node)
            
            # Remove nodes and their edges
            for node in nodes_to_close:
                graph.remove_node(node)
    
    def _is_in_westminster_area(self, x: float, y: float) -> bool:
        """Check if coordinates are in Westminster area (simplified)."""
        # Westminster bounding box (approximate)
        return (-0.15 <= x <= -0.11) and (51.49 <= y <= 51.52)
    
    def _apply_capacity_change(self, graph: nx.MultiDiGraph, 
                             selector: str, multiplier: float) -> None:
        """Apply capacity changes to selected edges."""
        
        for u, v, k, data in graph.edges(keys=True, data=True):
            should_modify = False
            
            if selector == "is_bridge==true" and data.get('is_bridge', False):
                should_modify = True
            elif selector in data.get('road_class', ''):
                should_modify = True
            
            if should_modify:
                original_capacity = data.get('original_capacity', data.get('capacity', 1000))
                data['capacity'] = original_capacity * multiplier
    
    async def _run_simulation(self, graph: nx.MultiDiGraph, 
                            scenario: ScenarioConfig) -> Dict[str, Any]:
        """Run REAL Mesa agent-based evacuation simulation."""
        
        try:
            # Extract scenario parameters (use getattr for optional fields)
            # Default to 1000 agents for proper evacuation simulation
            total_population = getattr(scenario, 'population_size', 1000)
            duration_minutes = getattr(scenario, 'duration_minutes', 60)
            
            # Run Mesa simulation
            logger.info("Running Mesa simulation", 
                       population=total_population,
                       duration=duration_minutes)
            
            mesa_results = await self.mesa_executor.run_simulation(
                scenario=scenario.__dict__ if hasattr(scenario, '__dict__') else {},
                graph=graph,
                duration_minutes=duration_minutes,
                time_step_min=1.0,
                num_agents=total_population
            )
            
            logger.info("Mesa simulation completed",
                       evacuated=mesa_results.get('total_evacuated'),
                       clearance_time=mesa_results.get('clearance_time_p50'))
            
            return mesa_results
            
        except Exception as e:
            logger.error("Mesa simulation failed", error=str(e))
            # Fallback to heuristic if Mesa fails
            logger.warning("Falling back to heuristic simulation")
            return await self._run_simulation_fallback(graph, scenario)
    
    async def _run_simulation_fallback(self, graph: nx.MultiDiGraph,
                                       scenario: ScenarioConfig) -> Dict[str, Any]:
        """Fallback heuristic simulation if Mesa fails."""
        logger.warning("Using heuristic fallback - results will be estimates")
        
        # Use simple heuristic calculations as fallback (use getattr for optional fields)
        total_population = getattr(scenario, 'population_size', 50000)
        duration_minutes = getattr(scenario, 'duration_minutes', 180)
        
        # Calculate total network capacity
        total_capacity = sum(
            data.get('capacity', 1000) 
            for u, v, k, data in graph.edges(keys=True, data=True)
        )
        
        # Estimate clearance time based on capacity
        throughput_per_minute = total_capacity / 60  # Convert hourly to per minute
        estimated_clearance = total_population / throughput_per_minute if throughput_per_minute > 0 else duration_minutes
        estimated_clearance = min(estimated_clearance, duration_minutes)
        
        # Heuristic queue estimates
        num_edges = graph.number_of_edges()
        avg_queue = (total_population / num_edges) * 0.1 if num_edges > 0 else 50
        
        return {
            'clearance_time_p50': estimated_clearance,
            'clearance_time_p95': estimated_clearance * 1.5,
            'max_queue_length': avg_queue * 3,
            'total_evacuated': total_population,
            'evacuation_rate': 0.85,
            'simulation_time': duration_minutes,
            'confidence': 'VERY_LOW',
            'note': 'Heuristic fallback used - not real simulation',
            'simulation_engine': 'heuristic_fallback'
        }
    
    def _calculate_throughput(self, graph: nx.MultiDiGraph) -> float:
        """Calculate current evacuation throughput based on network capacity."""
        total_capacity = sum(
            data.get('capacity', 1000) 
            for u, v, k, data in graph.edges(keys=True, data=True)
        )
        return total_capacity / 60  # Convert from per hour to per minute
    
    def _calculate_metrics(self, mesa_results: Dict[str, Any], 
                          scenario: ScenarioConfig) -> SimulationMetrics:
        """Extract REAL metrics from Mesa simulation results."""
        
        # Extract real measured values from Mesa
        clearance_time = mesa_results.get('clearance_time_p50', 0.0)
        max_queue = mesa_results.get('max_queue_length', 0.0)
        
        # Calculate fairness index based on real clearance time distribution
        fairness_index = self._calculate_fairness(mesa_results)
        
        # Calculate robustness
        robustness = self._calculate_robustness(scenario)
        
        return SimulationMetrics(
            clearance_time=clearance_time,
            max_queue=max_queue,
            fairness_index=fairness_index,
            robustness=robustness
        )
    
    def _calculate_fairness(self, mesa_results: Dict[str, Any]) -> float:
        """Calculate fairness index from Mesa clearance time distribution."""
        # Use percentile spread as fairness indicator
        p50 = mesa_results.get('clearance_time_p50', 0.0)
        p95 = mesa_results.get('clearance_time_p95', 0.0)
        
        if p95 == 0:
            return 1.0
        
        # Lower spread = higher fairness
        spread = (p95 - p50) / p95 if p95 > 0 else 0
        fairness = max(0.0, 1.0 - spread)
        
        return fairness
    
    def _calculate_robustness(self, scenario: ScenarioConfig) -> float:
        """Calculate robustness metric."""
        # Simplified robustness calculation
        # In practice, this would test network performance under random failures
        
        base_robustness = 0.8
        
        # Reduce robustness for each closure
        for closure in scenario.closures:
            base_robustness -= 0.1
        
        # Reduce robustness for capacity reductions
        for change in scenario.capacity_changes:
            if change.multiplier < 1.0:
                base_robustness -= 0.05
        
        # Increase robustness for protected corridors
        for corridor in scenario.protected_corridors:
            if corridor.rule == "increase_capacity":
                base_robustness += 0.05
        
        return max(0.0, min(1.0, base_robustness))
