"""
Evacuation Metrics Calculator Service
Handles calculation of evacuation metrics, fairness indices, and robustness scores.
Extracted from multi_city_orchestrator.py to improve code organization.
"""

from typing import Dict, List, Optional
import json
from pathlib import Path
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import networkx as nx
import structlog

logger = structlog.get_logger(__name__)

# Global thread pool for async operations
_thread_pool = ThreadPoolExecutor(max_workers=10)


class EvacuationMetricsCalculator:
    """Service for calculating evacuation simulation metrics."""
    
    def __init__(self, results_dir: str = "local_s3/results"):
        """
        Initialize the metrics calculator.
        
        Args:
            results_dir: Directory for saving calculation results
        """
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
    
    def calculate_metrics(
        self,
        graph: nx.MultiDiGraph,
        astar_routes: List[Dict],
        random_walk_paths: List,
        city: str
    ) -> Dict[str, float]:
        """
        Calculate real evacuation metrics based on network analysis.
        
        Args:
            graph: Street network graph
            astar_routes: List of A* route dictionaries
            random_walk_paths: List of random walk paths
            city: City name
            
        Returns:
            Dictionary of calculated metrics
        """
        # Calculate network connectivity metrics
        total_nodes = len(graph.nodes())
        total_edges = len(graph.edges())
        
        # Calculate route efficiency metrics
        if astar_routes:
            route_lengths = [route.get('length', 0) for route in astar_routes]
            avg_route_length = np.mean(route_lengths)
            route_efficiency = 1.0 / (1.0 + avg_route_length / total_nodes) if total_nodes > 0 else 0
        else:
            route_efficiency = 0
        
        # Calculate network density and connectivity
        network_density = (2 * total_edges) / (total_nodes * (total_nodes - 1)) if total_nodes > 1 else 0
        
        # Estimate clearance times based on network properties
        base_clearance_time = 45  # minutes for 50% clearance
        clearance_time_p50 = base_clearance_time * (1 + (1 - network_density))
        clearance_time_p95 = clearance_time_p50 * 2.2  # 95% takes longer
        
        # Calculate queue metrics based on network bottlenecks
        node_degrees = [graph.degree(node) for node in graph.nodes()]
        max_degree = max(node_degrees) if node_degrees else 0
        avg_degree = np.mean(node_degrees) if node_degrees else 0
        
        # Estimate max queue length
        max_queue_length = max_degree * 50  # Estimated people per high-degree node
        
        # Calculate evacuation efficiency
        evacuation_efficiency = route_efficiency * network_density * 100
        
        # Random walk convergence metric
        if random_walk_paths:
            walk_lengths = [len(path) for path in random_walk_paths]
            avg_walk_length = np.mean(walk_lengths)
            walk_efficiency = 1.0 / (1.0 + avg_walk_length / 1000)  # Normalize to 1000 steps
        else:
            walk_efficiency = 0
        
        metrics = {
            "clearance_time_p50": round(clearance_time_p50, 1),
            "clearance_time_p95": round(clearance_time_p95, 1),
            "max_queue_length": round(max_queue_length, 0),
            "evacuation_efficiency": round(evacuation_efficiency, 1),
            "network_density": round(network_density, 3),
            "route_efficiency": round(route_efficiency, 3),
            "walk_efficiency": round(walk_efficiency, 3),
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "avg_node_degree": round(avg_degree, 1),
            "max_node_degree": max_degree
        }
        
        logger.info(f"Calculated evacuation metrics for {city}", **metrics)
        
        # Log results to file
        self.log_results(city, metrics)
        
        return metrics
    
    async def calculate_fairness_async(
        self,
        graph: nx.MultiDiGraph,
        astar_routes: List[Dict],
        random_walk_paths: List
    ) -> float:
        """
        Calculate REAL fairness index based on route distribution using Gini coefficient.
        Async version running in thread pool.
        
        Fairness measures how equitably evacuation routes serve the population.
        
        Args:
            graph: Street network graph
            astar_routes: List of A* routes
            random_walk_paths: List of random walk paths
            
        Returns:
            Fairness index (0-1, higher is better)
        """
        def _calculate():
            if not astar_routes or len(graph.nodes) == 0:
                return 0.5  # Neutral if no data

            # Create spatial bins (grid cells)
            nodes_array = np.array([[graph.nodes[n]['x'], graph.nodes[n]['y']] for n in graph.nodes()])
            x_min, x_max = nodes_array[:, 0].min(), nodes_array[:, 0].max()
            y_min, y_max = nodes_array[:, 1].min(), nodes_array[:, 1].max()

            # Divide area into 10x10 grid
            grid_size = 10
            x_bins = np.linspace(x_min, x_max, grid_size + 1)
            y_bins = np.linspace(y_min, y_max, grid_size + 1)

            # Count how many routes pass through each cell
            route_coverage = np.zeros((grid_size, grid_size))

            for route in astar_routes:
                coords = route['coordinates']
                for coord in coords:
                    x, y = coord[0], coord[1]
                    x_idx = np.digitize([x], x_bins)[0] - 1
                    y_idx = np.digitize([y], y_bins)[0] - 1

                    if 0 <= x_idx < grid_size and 0 <= y_idx < grid_size:
                        route_coverage[x_idx, y_idx] += 1

            # Calculate Gini coefficient (0 = perfect equality, 1 = perfect inequality)
            coverage_flat = route_coverage.flatten()
            coverage_flat = coverage_flat[coverage_flat > 0]  # Only consider cells with routes

            if len(coverage_flat) < 2:
                return 0.5  # Not enough data

            sorted_coverage = np.sort(coverage_flat)
            n = len(sorted_coverage)
            cumsum = np.cumsum(sorted_coverage)
            gini = (2 * np.sum((np.arange(1, n+1)) * sorted_coverage)) / (n * cumsum[-1]) - (n + 1) / n

            # Convert Gini to fairness (higher is better)
            fairness = 1.0 - gini

            return fairness

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_thread_pool, _calculate)
    
    async def calculate_robustness_async(
        self,
        graph: nx.MultiDiGraph,
        astar_routes: List[Dict]
    ) -> float:
        """
        Calculate REAL robustness based on network resilience.
        Async version running in thread pool.
        
        Robustness measures network's ability to maintain connectivity
        when critical nodes/edges are removed.
        
        Args:
            graph: Street network graph
            astar_routes: List of A* routes
            
        Returns:
            Robustness score (0-1, higher is better)
        """
        def _calculate():
            if len(astar_routes) == 0 or len(graph.nodes) < 10:
                return 0.5  # Neutral if insufficient data

            # Identify critical nodes (nodes used in multiple routes)
            node_usage = {}
            for route in astar_routes:
                start_node = route['start_node']
                end_node = route['end_node']
                # Reconstruct path
                try:
                    path = nx.shortest_path(graph, start_node, end_node, weight='length')
                    for node in path:
                        node_usage[node] = node_usage.get(node, 0) + 1
                except:
                    continue

            if not node_usage:
                return 0.5

            # Find top 10% most critical nodes
            sorted_nodes = sorted(node_usage.items(), key=lambda x: x[1], reverse=True)
            critical_count = max(1, len(sorted_nodes) // 10)
            critical_nodes = [n for n, _ in sorted_nodes[:critical_count]]

            # Test network connectivity with critical nodes removed
            graph_copy = graph.copy()
            graph_copy.remove_nodes_from(critical_nodes)

            # Count connected components
            num_components_original = nx.number_weakly_connected_components(graph.to_directed())
            num_components_degraded = nx.number_weakly_connected_components(graph_copy.to_directed())

            # Robustness = how well network maintains connectivity
            if num_components_original == 0:
                return 0.5

            robustness = 1.0 - (num_components_degraded - num_components_original) / max(1, len(graph.nodes) / 100)
            robustness = max(0.0, min(1.0, robustness))  # Clamp to [0, 1]

            return robustness

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_thread_pool, _calculate)
    
    def log_results(self, city: str, metrics: Dict[str, float]) -> None:
        """
        Log calculated results to a results file.
        
        Args:
            city: City name
            metrics: Dictionary of calculated metrics
        """
        try:
            # Create results entry
            result_entry = {
                "timestamp": datetime.now().isoformat(),
                "city": city,
                "metrics": metrics,
                "calculation_method": "network_analysis",
                "version": "1.0"
            }
            
            # Append to results file
            results_file = self.results_dir / f"{city}_evacuation_results.jsonl"
            with open(results_file, "a") as f:
                f.write(json.dumps(result_entry) + "\n")
            
            logger.info(f"Logged evacuation results for {city} to {results_file}")
            
        except Exception as e:
            logger.error(f"Failed to log results for {city}: {e}")
