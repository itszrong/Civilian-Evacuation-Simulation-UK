"""
Stateless Metrics Service

Wraps MetricsBuilderService with a stateless, dependency-injectable interface.
All operations are stateless - data path and configuration passed as parameters.
"""

from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import structlog

from .metrics_builder_service import MetricsBuilderService

logger = structlog.get_logger(__name__)


class MetricsService:
    """
    Stateless service for metrics calculation.

    All methods accept data_path as parameter instead of storing it as instance state.
    This allows the service to work across multiple data sources concurrently.
    """

    def __init__(self):
        """Initialize service. No instance state stored."""
        pass

    @staticmethod
    def calculate_metrics(
        run_id: str,
        metrics_config: Union[Dict[str, Any], str, Path],
        data_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate metrics for a simulation run. Stateless operation.

        Args:
            run_id: Simulation run ID
            metrics_config: Metrics configuration (dict or path to config file)
            data_path: Path to data directory (if None, uses default)

        Returns:
            Dictionary of calculated metrics
        """
        # Create temporary builder instance (no state stored in service)
        builder = MetricsBuilderService(data_path=data_path)

        try:
            results = builder.calculate_metrics(run_id, metrics_config)
            return results
        except Exception as e:
            logger.error(f"Failed to calculate metrics: {e}", exc_info=True)
            return {"error": str(e)}

    @staticmethod
    def calculate_single_metric(
        run_id: str,
        metric_config: Dict[str, Any],
        data_path: Optional[str] = None
    ) -> Any:
        """
        Calculate a single metric. Stateless operation.

        Args:
            run_id: Simulation run ID
            metric_config: Single metric configuration
            data_path: Path to data directory

        Returns:
            Calculated metric value
        """
        builder = MetricsBuilderService(data_path=data_path)

        try:
            result = builder.calculate_metric(run_id, metric_config)
            return result
        except Exception as e:
            logger.error(f"Failed to calculate metric: {e}", exc_info=True)
            return {"error": str(e)}

    @staticmethod
    def get_available_metrics(
        run_id: str,
        data_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get information about available metrics for a run. Stateless operation.

        Args:
            run_id: Simulation run ID
            data_path: Path to data directory

        Returns:
            Dictionary with available data and metrics
        """
        builder = MetricsBuilderService(data_path=data_path)

        try:
            info = builder.get_available_metrics(run_id)
            return info
        except Exception as e:
            logger.error(f"Failed to get available metrics: {e}", exc_info=True)
            return {"error": str(e)}

    @staticmethod
    def compute_framework_metrics(
        run_id: str,
        scenario_results: List[Dict[str, Any]],
        scenario_template: Optional[str] = None,
        data_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compute framework-specific metrics. Stateless operation.

        Args:
            run_id: Simulation run ID
            scenario_results: List of scenario result data
            scenario_template: Framework template name
            data_path: Path to data directory

        Returns:
            Framework metrics with evaluation
        """
        builder = MetricsBuilderService(data_path=data_path)

        try:
            results = builder.compute_framework_metrics(
                run_id=run_id,
                scenario_results=scenario_results,
                scenario_template=scenario_template
            )
            return results
        except Exception as e:
            logger.error(f"Failed to compute framework metrics: {e}", exc_info=True)
            return {"error": str(e)}

    @staticmethod
    def create_evaluation_report(
        run_id: str,
        framework_metrics_results: List[Dict[str, Any]],
        data_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create evaluation report for a run. Stateless operation.

        Args:
            run_id: Simulation run ID
            framework_metrics_results: List of framework metrics results
            data_path: Path to data directory

        Returns:
            Comprehensive evaluation report
        """
        builder = MetricsBuilderService(data_path=data_path)

        try:
            report = builder.create_evaluation_report(
                run_id=run_id,
                framework_metrics_results=framework_metrics_results
            )
            return report
        except Exception as e:
            logger.error(f"Failed to create evaluation report: {e}", exc_info=True)
            return {"error": str(e)}

    @staticmethod
    def get_standard_metrics_config() -> Dict[str, Any]:
        """
        Get standard evacuation metrics configuration. Pure function.

        Returns:
            Standard metrics configuration dictionary
        """
        return {
            'metrics': {
                # Evacuation completion
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

                # Congestion
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

                # Platform safety
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

                # Events
                'total_events': {
                    'source': 'events',
                    'operation': 'count_events'
                }
            }
        }
