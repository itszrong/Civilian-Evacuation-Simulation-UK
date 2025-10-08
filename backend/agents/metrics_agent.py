"""
Metrics Agent

An example agent that uses the metrics system to analyze evacuation simulations
and provide insights for emergency planning.

REFACTORED: Now uses stateless MetricsService with dependency injection.
"""

from typing import Dict, Any, List, Optional
import json
from pathlib import Path

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from services.metrics.metrics_service import MetricsService


class MetricsAgent:
    """Agent that analyzes evacuation metrics and provides insights."""

    def __init__(
        self,
        data_path: str = "local_s3/runs",
        metrics_service: Optional[MetricsService] = None
    ):
        """
        Initialize the metrics agent with dependency injection.

        Args:
            data_path: Path to data directory (passed to service, not stored)
            metrics_service: Optional MetricsService instance (defaults to new instance)
        """
        self.data_path = data_path  # Store only data path, not service instance
        self.metrics_service = metrics_service or MetricsService()
        self.standard_metrics = self._load_standard_metrics()
    
    def _load_standard_metrics(self) -> Dict[str, Any]:
        """Load standard evacuation metrics configuration."""
        return {
            'metrics': {
                # Evacuation completion metrics
                'clearance_p50': {
                    'source': 'timeseries',
                    'metric_key': 'clearance_pct',
                    'operation': 'percentile_time_to_threshold',
                    'args': {'threshold_pct': 50},
                    'filters': {'scope': 'city'},
                    'post_process': {'divide_by': 60, 'round_to': 1}
                },
                'clearance_p95': {
                    'source': 'timeseries',
                    'metric_key': 'clearance_pct',
                    'operation': 'percentile_time_to_threshold',
                    'args': {'threshold_pct': 95},
                    'filters': {'scope': 'city'},
                    'post_process': {'divide_by': 60, 'round_to': 1}
                },
                
                # Congestion metrics
                'max_queue_length': {
                    'source': 'timeseries',
                    'metric_key': 'queue_len',
                    'operation': 'max_value',
                    'filters': {'scope_contains': 'edge:'}
                },
                'avg_queue_length': {
                    'source': 'timeseries',
                    'metric_key': 'queue_len',
                    'operation': 'mean_value',
                    'filters': {'scope_contains': 'edge:'}
                },
                
                # Platform safety metrics
                'max_platform_density': {
                    'source': 'timeseries',
                    'metric_key': 'density',
                    'operation': 'max_value',
                    'filters': {'scope_contains': 'station'}
                },
                'platform_overcrowding_time': {
                    'source': 'timeseries',
                    'metric_key': 'density',
                    'operation': 'time_above_threshold',
                    'args': {'threshold': 4.0},
                    'filters': {'scope_contains': 'station'},
                    'post_process': {'divide_by': 60, 'round_to': 1}
                },
                
                # Event metrics
                'total_events': {
                    'source': 'events',
                    'operation': 'count_events'
                }
            }
        }
    
    def analyze_evacuation_performance(self, run_id: str) -> Dict[str, Any]:
        """
        Analyze evacuation performance for a simulation run.

        Args:
            run_id: Simulation run ID

        Returns:
            Analysis results with metrics and insights
        """
        # Calculate standard metrics using stateless service
        metrics = self.metrics_service.calculate_metrics(
            run_id=run_id,
            metrics_config=self.standard_metrics,
            data_path=self.data_path
        )
        
        # Generate insights based on metrics
        insights = self._generate_insights(metrics)
        
        # Get bottleneck analysis
        bottlenecks = self._analyze_bottlenecks(run_id)
        
        return {
            'run_id': run_id,
            'metrics': metrics,
            'insights': insights,
            'bottlenecks': bottlenecks,
            'recommendations': self._generate_recommendations(metrics, bottlenecks)
        }
    
    def _generate_insights(self, metrics: Dict[str, Any]) -> List[str]:
        """Generate human-readable insights from metrics."""
        insights = []
        
        # Evacuation timing insights
        if 'clearance_p50' in metrics and 'clearance_p95' in metrics:
            p50 = metrics['clearance_p50']
            p95 = metrics['clearance_p95']
            
            if isinstance(p50, (int, float)) and isinstance(p95, (int, float)):
                insights.append(f"50% of people evacuated in {p50} minutes, 95% in {p95} minutes")
                
                if p95 > 30:
                    insights.append("⚠️  Evacuation time is concerning - 95% clearance took over 30 minutes")
                elif p95 > 20:
                    insights.append("⚡ Evacuation time is acceptable but could be improved")
                else:
                    insights.append("✅ Good evacuation performance - 95% cleared in under 20 minutes")
        
        # Congestion insights
        if 'max_queue_length' in metrics:
            max_queue = metrics['max_queue_length']
            if isinstance(max_queue, (int, float)) and max_queue > 40:
                insights.append(f"⚠️  High congestion detected - maximum queue length of {max_queue:.1f}")
            elif isinstance(max_queue, (int, float)) and max_queue > 25:
                insights.append(f"⚡ Moderate congestion - maximum queue length of {max_queue:.1f}")
        
        # Platform safety insights
        if 'max_platform_density' in metrics:
            max_density = metrics['max_platform_density']
            if isinstance(max_density, (int, float)):
                if max_density > 6:
                    insights.append(f"🚨 Dangerous platform overcrowding - peak density of {max_density:.1f} people/m²")
                elif max_density > 4:
                    insights.append(f"⚠️  Platform overcrowding detected - peak density of {max_density:.1f} people/m²")
        
        if 'platform_overcrowding_time' in metrics:
            overcrowding_time = metrics['platform_overcrowding_time']
            if isinstance(overcrowding_time, (int, float)) and overcrowding_time > 5:
                insights.append(f"⚠️  Platforms were overcrowded for {overcrowding_time} minutes")
        
        return insights
    
    def _analyze_bottlenecks(self, run_id: str) -> Dict[str, Any]:
        """Analyze bottlenecks in the evacuation."""
        # Get queue lengths by edge using stateless service
        queue_config = {
            'source': 'timeseries',
            'metric_key': 'queue_len',
            'operation': 'max_value',
            'group_by': 'scope',
            'filters': {'scope_contains': 'edge:'}
        }

        edge_queues = self.metrics_service.calculate_single_metric(
            run_id=run_id,
            metric_config=queue_config,
            data_path=self.data_path
        )

        # Get platform densities using stateless service
        density_config = {
            'source': 'timeseries',
            'metric_key': 'density',
            'operation': 'max_value',
            'group_by': 'scope',
            'filters': {'scope_contains': 'station'}
        }

        station_densities = self.metrics_service.calculate_single_metric(
            run_id=run_id,
            metric_config=density_config,
            data_path=self.data_path
        )
        
        # Identify top bottlenecks
        bottlenecks = {
            'worst_edges': [],
            'worst_stations': []
        }
        
        if hasattr(edge_queues, 'items'):
            # Sort edges by queue length
            sorted_edges = sorted(edge_queues.items(), key=lambda x: x[1], reverse=True)
            bottlenecks['worst_edges'] = [
                {'location': edge, 'max_queue': queue}
                for edge, queue in sorted_edges[:3]  # Top 3
            ]
        
        if hasattr(station_densities, 'items'):
            # Sort stations by density
            sorted_stations = sorted(station_densities.items(), key=lambda x: x[1], reverse=True)
            bottlenecks['worst_stations'] = [
                {'location': station, 'max_density': density}
                for station, density in sorted_stations[:3]  # Top 3
            ]
        
        return bottlenecks
    
    def _generate_recommendations(self, metrics: Dict[str, Any], bottlenecks: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on analysis."""
        recommendations = []
        
        # Evacuation time recommendations
        if 'clearance_p95' in metrics:
            p95 = metrics['clearance_p95']
            if isinstance(p95, (int, float)) and p95 > 25:
                recommendations.append("Consider additional evacuation routes or improved signage to reduce clearance time")
        
        # Congestion recommendations
        if bottlenecks.get('worst_edges'):
            worst_edge = bottlenecks['worst_edges'][0]
            if worst_edge['max_queue'] > 35:
                recommendations.append(f"Address congestion at {worst_edge['location']} - consider traffic management or alternative routing")
        
        # Platform safety recommendations
        if bottlenecks.get('worst_stations'):
            worst_station = bottlenecks['worst_stations'][0]
            if worst_station['max_density'] > 5:
                recommendations.append(f"Implement crowd control measures at {worst_station['location']} to prevent dangerous overcrowding")
        
        # Platform overcrowding time
        if 'platform_overcrowding_time' in metrics:
            overcrowding_time = metrics['platform_overcrowding_time']
            if isinstance(overcrowding_time, (int, float)) and overcrowding_time > 3:
                recommendations.append("Deploy additional staff to manage platform crowds during peak evacuation periods")
        
        if not recommendations:
            recommendations.append("✅ Evacuation performance looks good - no major issues identified")
        
        return recommendations
    
    def compare_scenarios(self, run_ids: List[str]) -> Dict[str, Any]:
        """
        Compare multiple evacuation scenarios.
        
        Args:
            run_ids: List of simulation run IDs to compare
            
        Returns:
            Comparison analysis
        """
        comparison = {
            'scenarios': {},
            'best_performer': None,
            'key_differences': []
        }
        
        # Analyze each scenario
        for run_id in run_ids:
            analysis = self.analyze_evacuation_performance(run_id)
            comparison['scenarios'][run_id] = analysis
        
        # Find best performer (lowest p95 clearance time)
        best_p95 = float('inf')
        best_run = None
        
        for run_id, analysis in comparison['scenarios'].items():
            p95 = analysis['metrics'].get('clearance_p95')
            if isinstance(p95, (int, float)) and p95 < best_p95:
                best_p95 = p95
                best_run = run_id
        
        comparison['best_performer'] = best_run
        
        # Generate key differences
        if len(run_ids) >= 2:
            comparison['key_differences'] = self._identify_key_differences(comparison['scenarios'])
        
        return comparison
    
    def _identify_key_differences(self, scenarios: Dict[str, Any]) -> List[str]:
        """Identify key differences between scenarios."""
        differences = []
        
        # Compare clearance times
        clearance_times = {}
        for run_id, analysis in scenarios.items():
            p95 = analysis['metrics'].get('clearance_p95')
            if isinstance(p95, (int, float)):
                clearance_times[run_id] = p95
        
        if len(clearance_times) >= 2:
            min_time = min(clearance_times.values())
            max_time = max(clearance_times.values())
            time_diff = max_time - min_time
            
            if time_diff > 5:  # More than 5 minutes difference
                best_run = min(clearance_times, key=clearance_times.get)
                worst_run = max(clearance_times, key=clearance_times.get)
                differences.append(f"Significant clearance time difference: {best_run} ({min_time:.1f}min) vs {worst_run} ({max_time:.1f}min)")
        
        return differences
    
    def generate_report(self, run_id: str) -> str:
        """Generate a human-readable report for a simulation run."""
        analysis = self.analyze_evacuation_performance(run_id)
        
        report = f"""
# Evacuation Analysis Report
**Run ID:** {run_id}

## Key Metrics
"""
        
        for metric_name, value in analysis['metrics'].items():
            if not isinstance(value, dict) or 'error' not in value:
                report += f"- **{metric_name.replace('_', ' ').title()}:** {value}\n"
        
        report += "\n## Insights\n"
        for insight in analysis['insights']:
            report += f"- {insight}\n"
        
        if analysis['bottlenecks']['worst_edges']:
            report += "\n## Worst Congestion Points\n"
            for edge in analysis['bottlenecks']['worst_edges']:
                report += f"- {edge['location']}: {edge['max_queue']:.1f} max queue length\n"
        
        if analysis['bottlenecks']['worst_stations']:
            report += "\n## Highest Density Stations\n"
            for station in analysis['bottlenecks']['worst_stations']:
                report += f"- {station['location']}: {station['max_density']:.1f} people/m² max density\n"
        
        report += "\n## Recommendations\n"
        for rec in analysis['recommendations']:
            report += f"- {rec}\n"
        
        return report


def demo_metrics_agent():
    """Demonstrate the metrics agent capabilities."""
    agent = MetricsAgent()
    
    print("🤖 Metrics Agent Demo")
    print("=" * 50)
    
    # Analyze the sample run
    print("\n📊 Analysing evacuation performance...")
    analysis = agent.analyze_evacuation_performance("sample_run")
    
    print(f"\n📈 Key Metrics:")
    for metric, value in analysis['metrics'].items():
        if not isinstance(value, dict) or 'error' not in value:
            print(f"  - {metric}: {value}")
    
    print(f"\n💡 Insights:")
    for insight in analysis['insights']:
        print(f"  - {insight}")
    
    print(f"\n🎯 Recommendations:")
    for rec in analysis['recommendations']:
        print(f"  - {rec}")
    
    print("\n📋 Full Report:")
    print(agent.generate_report("sample_run"))


if __name__ == "__main__":
    demo_metrics_agent()
