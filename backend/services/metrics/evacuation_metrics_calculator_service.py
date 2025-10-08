"""
Evacuation Metrics Calculator Service
Advanced metrics calculation and analysis for evacuation simulations.
Extracted from multi_city_simulation.py for better separation of concerns.
"""

import numpy as np
import networkx as nx
from typing import Dict, List, Tuple, Optional, Any
import structlog
from dataclasses import dataclass
from datetime import datetime, timedelta
import json

logger = structlog.get_logger(__name__)


@dataclass
class EvacuationMetrics:
    """Comprehensive evacuation metrics for a simulation."""
    
    # Basic metrics
    total_agents: int
    successful_evacuations: int
    failed_evacuations: int
    success_rate: float
    
    # Time metrics
    avg_evacuation_time: float
    max_evacuation_time: float
    min_evacuation_time: float
    std_evacuation_time: float
    
    # Distance metrics
    avg_distance_traveled: float
    total_distance_traveled: float
    avg_efficiency_score: float
    
    # Behavioral metrics
    avg_panic_level: float
    avg_familiarity_level: float
    crowd_following_rate: float
    official_guidance_following_rate: float
    
    # Network metrics
    network_congestion_score: float
    bottleneck_locations: List[int]
    critical_path_usage: float
    
    # Performance scores
    overall_performance_score: float
    time_performance_score: float
    efficiency_performance_score: float
    safety_performance_score: float


class EvacuationMetricsCalculatorService:
    """Advanced metrics calculator for evacuation simulations."""
    
    def __init__(self):
        """Initialize metrics calculator."""
        self.calculation_history = []
        
    def calculate_comprehensive_metrics(
        self, 
        simulation_results: Dict[str, Any],
        graph: nx.MultiDiGraph
    ) -> EvacuationMetrics:
        """
        Calculate comprehensive evacuation metrics from simulation results.
        
        Args:
            simulation_results: Results from simulation engine
            graph: NetworkX graph used in simulation
            
        Returns:
            EvacuationMetrics object with all calculated metrics
        """
        try:
            logger.info("Calculating comprehensive evacuation metrics")
            
            agent_metrics = simulation_results.get('agent_metrics', [])
            agent_paths = simulation_results.get('agent_paths', [])
            
            if not agent_metrics:
                logger.warning("No agent metrics found in simulation results")
                return self._create_empty_metrics()
            
            # Calculate basic metrics
            basic_metrics = self._calculate_basic_metrics(agent_metrics)
            
            # Calculate time metrics
            time_metrics = self._calculate_time_metrics(agent_metrics)
            
            # Calculate distance metrics
            distance_metrics = self._calculate_distance_metrics(agent_metrics)
            
            # Calculate behavioral metrics
            behavioral_metrics = self._calculate_behavioral_metrics(agent_metrics)
            
            # Calculate network metrics
            network_metrics = self._calculate_network_metrics(agent_paths, graph)
            
            # Calculate performance scores
            performance_scores = self._calculate_performance_scores(
                basic_metrics, time_metrics, distance_metrics, behavioral_metrics, network_metrics
            )
            
            # Combine all metrics
            comprehensive_metrics = EvacuationMetrics(
                **basic_metrics,
                **time_metrics,
                **distance_metrics,
                **behavioral_metrics,
                **network_metrics,
                **performance_scores
            )
            
            # Store in history
            self.calculation_history.append({
                'timestamp': datetime.now(),
                'metrics': comprehensive_metrics,
                'agent_count': len(agent_metrics)
            })
            
            logger.info(f"Successfully calculated metrics for {len(agent_metrics)} agents")
            return comprehensive_metrics
            
        except Exception as e:
            logger.error(f"Error calculating comprehensive metrics: {e}", exc_info=True)
            return self._create_empty_metrics()
    
    def _calculate_basic_metrics(self, agent_metrics: List[Dict]) -> Dict[str, Any]:
        """Calculate basic evacuation metrics."""
        total_agents = len(agent_metrics)
        successful_evacuations = sum(1 for agent in agent_metrics if agent.get('evacuated', False))
        failed_evacuations = total_agents - successful_evacuations
        success_rate = successful_evacuations / total_agents if total_agents > 0 else 0.0
        
        return {
            'total_agents': total_agents,
            'successful_evacuations': successful_evacuations,
            'failed_evacuations': failed_evacuations,
            'success_rate': success_rate
        }
    
    def _calculate_time_metrics(self, agent_metrics: List[Dict]) -> Dict[str, float]:
        """Calculate time-based evacuation metrics."""
        evacuation_times = []
        
        for agent in agent_metrics:
            if agent.get('evacuated', False) and 'evacuation_time' in agent:
                evacuation_times.append(agent['evacuation_time'])
        
        if not evacuation_times:
            return {
                'avg_evacuation_time': 0.0,
                'max_evacuation_time': 0.0,
                'min_evacuation_time': 0.0,
                'std_evacuation_time': 0.0
            }
        
        return {
            'avg_evacuation_time': float(np.mean(evacuation_times)),
            'max_evacuation_time': float(np.max(evacuation_times)),
            'min_evacuation_time': float(np.min(evacuation_times)),
            'std_evacuation_time': float(np.std(evacuation_times))
        }
    
    def _calculate_distance_metrics(self, agent_metrics: List[Dict]) -> Dict[str, float]:
        """Calculate distance-based evacuation metrics."""
        distances = []
        efficiency_scores = []
        
        for agent in agent_metrics:
            if 'distance_traveled' in agent:
                distances.append(agent['distance_traveled'])
            if 'efficiency_score' in agent:
                efficiency_scores.append(agent['efficiency_score'])
        
        total_distance = sum(distances) if distances else 0.0
        avg_distance = float(np.mean(distances)) if distances else 0.0
        avg_efficiency = float(np.mean(efficiency_scores)) if efficiency_scores else 0.0
        
        return {
            'avg_distance_traveled': avg_distance,
            'total_distance_traveled': total_distance,
            'avg_efficiency_score': avg_efficiency
        }
    
    def _calculate_behavioral_metrics(self, agent_metrics: List[Dict]) -> Dict[str, float]:
        """Calculate behavioral evacuation metrics."""
        panic_levels = []
        familiarity_levels = []
        crowd_followers = 0
        guidance_followers = 0
        
        for agent in agent_metrics:
            if 'panic_level' in agent:
                panic_levels.append(agent['panic_level'])
            if 'familiarity_level' in agent:
                familiarity_levels.append(agent['familiarity_level'])
            if agent.get('followed_crowd', False):
                crowd_followers += 1
            if agent.get('followed_guidance', False):
                guidance_followers += 1
        
        total_agents = len(agent_metrics)
        
        return {
            'avg_panic_level': float(np.mean(panic_levels)) if panic_levels else 0.0,
            'avg_familiarity_level': float(np.mean(familiarity_levels)) if familiarity_levels else 0.0,
            'crowd_following_rate': crowd_followers / total_agents if total_agents > 0 else 0.0,
            'official_guidance_following_rate': guidance_followers / total_agents if total_agents > 0 else 0.0
        }
    
    def _calculate_network_metrics(self, agent_paths: List[List], graph: nx.MultiDiGraph) -> Dict[str, Any]:
        """Calculate network-based evacuation metrics."""
        if not agent_paths or not graph:
            return {
                'network_congestion_score': 0.0,
                'bottleneck_locations': [],
                'critical_path_usage': 0.0
            }
        
        # Calculate edge usage frequency
        edge_usage = {}
        for path in agent_paths:
            for i in range(len(path) - 1):
                edge = (path[i], path[i + 1])
                edge_usage[edge] = edge_usage.get(edge, 0) + 1
        
        # Identify bottlenecks (top 10% most used edges)
        if edge_usage:
            usage_values = list(edge_usage.values())
            bottleneck_threshold = np.percentile(usage_values, 90)
            bottleneck_edges = [edge for edge, usage in edge_usage.items() if usage >= bottleneck_threshold]
            bottleneck_locations = list(set([node for edge in bottleneck_edges for node in edge]))
        else:
            bottleneck_locations = []
        
        # Calculate congestion score (normalized by graph size)
        total_usage = sum(edge_usage.values()) if edge_usage else 0
        total_edges = graph.number_of_edges()
        congestion_score = total_usage / total_edges if total_edges > 0 else 0.0
        
        # Calculate critical path usage (simplified)
        critical_path_usage = len(bottleneck_locations) / graph.number_of_nodes() if graph.number_of_nodes() > 0 else 0.0
        
        return {
            'network_congestion_score': float(congestion_score),
            'bottleneck_locations': bottleneck_locations[:20],  # Limit to top 20
            'critical_path_usage': float(critical_path_usage)
        }
    
    def _calculate_performance_scores(
        self, 
        basic_metrics: Dict, 
        time_metrics: Dict, 
        distance_metrics: Dict, 
        behavioral_metrics: Dict, 
        network_metrics: Dict
    ) -> Dict[str, float]:
        """Calculate overall performance scores."""
        
        # Time performance (lower evacuation time is better)
        max_reasonable_time = 3600  # 1 hour
        time_score = max(0, 1 - (time_metrics['avg_evacuation_time'] / max_reasonable_time))
        
        # Efficiency performance (higher efficiency is better)
        efficiency_score = distance_metrics['avg_efficiency_score']
        
        # Safety performance (lower panic, higher guidance following is better)
        panic_penalty = behavioral_metrics['avg_panic_level'] / 10.0  # Assume panic scale 0-10
        guidance_bonus = behavioral_metrics['official_guidance_following_rate']
        safety_score = max(0, guidance_bonus - panic_penalty)
        
        # Overall performance (weighted average)
        overall_score = (
            0.4 * basic_metrics['success_rate'] +
            0.3 * time_score +
            0.2 * efficiency_score +
            0.1 * safety_score
        )
        
        return {
            'overall_performance_score': float(overall_score),
            'time_performance_score': float(time_score),
            'efficiency_performance_score': float(efficiency_score),
            'safety_performance_score': float(safety_score)
        }
    
    def _create_empty_metrics(self) -> EvacuationMetrics:
        """Create empty metrics object for error cases."""
        return EvacuationMetrics(
            total_agents=0,
            successful_evacuations=0,
            failed_evacuations=0,
            success_rate=0.0,
            avg_evacuation_time=0.0,
            max_evacuation_time=0.0,
            min_evacuation_time=0.0,
            std_evacuation_time=0.0,
            avg_distance_traveled=0.0,
            total_distance_traveled=0.0,
            avg_efficiency_score=0.0,
            avg_panic_level=0.0,
            avg_familiarity_level=0.0,
            crowd_following_rate=0.0,
            official_guidance_following_rate=0.0,
            network_congestion_score=0.0,
            bottleneck_locations=[],
            critical_path_usage=0.0,
            overall_performance_score=0.0,
            time_performance_score=0.0,
            efficiency_performance_score=0.0,
            safety_performance_score=0.0
        )
    
    def get_calculation_history(self) -> List[Dict]:
        """Get history of all metric calculations."""
        return self.calculation_history.copy()
    
    def clear_calculation_history(self):
        """Clear the calculation history."""
        self.calculation_history.clear()
        logger.info("Calculation history cleared")
    
    def export_metrics_to_json(self, metrics: EvacuationMetrics, filepath: str):
        """Export metrics to JSON file."""
        try:
            metrics_dict = {
                'total_agents': metrics.total_agents,
                'successful_evacuations': metrics.successful_evacuations,
                'failed_evacuations': metrics.failed_evacuations,
                'success_rate': metrics.success_rate,
                'avg_evacuation_time': metrics.avg_evacuation_time,
                'max_evacuation_time': metrics.max_evacuation_time,
                'min_evacuation_time': metrics.min_evacuation_time,
                'std_evacuation_time': metrics.std_evacuation_time,
                'avg_distance_traveled': metrics.avg_distance_traveled,
                'total_distance_traveled': metrics.total_distance_traveled,
                'avg_efficiency_score': metrics.avg_efficiency_score,
                'avg_panic_level': metrics.avg_panic_level,
                'avg_familiarity_level': metrics.avg_familiarity_level,
                'crowd_following_rate': metrics.crowd_following_rate,
                'official_guidance_following_rate': metrics.official_guidance_following_rate,
                'network_congestion_score': metrics.network_congestion_score,
                'bottleneck_locations': metrics.bottleneck_locations,
                'critical_path_usage': metrics.critical_path_usage,
                'overall_performance_score': metrics.overall_performance_score,
                'time_performance_score': metrics.time_performance_score,
                'efficiency_performance_score': metrics.efficiency_performance_score,
                'safety_performance_score': metrics.safety_performance_score,
                'calculation_timestamp': datetime.now().isoformat()
            }
            
            with open(filepath, 'w') as f:
                json.dump(metrics_dict, f, indent=2)
            
            logger.info(f"Metrics exported to {filepath}")
            
        except Exception as e:
            logger.error(f"Error exporting metrics to JSON: {e}", exc_info=True)
    
    def compare_metrics(self, metrics1: EvacuationMetrics, metrics2: EvacuationMetrics) -> Dict[str, float]:
        """Compare two sets of metrics and return the differences."""
        comparison = {}
        
        # Compare key metrics
        comparison['success_rate_diff'] = metrics2.success_rate - metrics1.success_rate
        comparison['avg_evacuation_time_diff'] = metrics2.avg_evacuation_time - metrics1.avg_evacuation_time
        comparison['efficiency_score_diff'] = metrics2.avg_efficiency_score - metrics1.avg_efficiency_score
        comparison['overall_performance_diff'] = metrics2.overall_performance_score - metrics1.overall_performance_score
        comparison['congestion_score_diff'] = metrics2.network_congestion_score - metrics1.network_congestion_score
        
        return comparison
