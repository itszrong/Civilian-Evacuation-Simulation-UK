"""
Tests for agents.metrics_agent module.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any, List

from agents.metrics_agent import MetricsAgent


class TestMetricsAgent:
    """Test the MetricsAgent class."""

    def setup_method(self):
        """Set up test environment."""
        # Mock the MetricsService
        self.mock_metrics_service = Mock()
        self.agent = MetricsAgent(
            data_path="test_data_path",
            metrics_service=self.mock_metrics_service
        )

    def test_initialization(self):
        """Test MetricsAgent initialization."""
        agent = MetricsAgent()
        assert agent is not None
        assert agent.data_path == "local_s3/runs"
        assert agent.metrics_service is not None

    def test_initialization_with_custom_path(self):
        """Test MetricsAgent initialization with custom data path."""
        custom_path = "/custom/path"
        agent = MetricsAgent(data_path=custom_path)
        assert agent.data_path == custom_path

    def test_load_standard_metrics(self):
        """Test loading standard metrics configuration."""
        config = self.agent._load_standard_metrics()

        assert 'metrics' in config
        assert 'clearance_p50' in config['metrics']
        assert 'clearance_p95' in config['metrics']
        assert 'max_queue_length' in config['metrics']
        assert 'max_platform_density' in config['metrics']

    def test_analyze_evacuation_performance_success(self):
        """Test successful evacuation performance analysis."""
        # Mock metrics service return
        self.mock_metrics_service.calculate_metrics.return_value = {
            'clearance_p50': 15.0,
            'clearance_p95': 25.0,
            'max_queue_length': 30.0,
            'max_platform_density': 3.5
        }

        self.mock_metrics_service.calculate_single_metric.return_value = {
            'edge:123': 25.0,
            'edge:456': 30.0,
            'station:A': 3.5
        }

        result = self.agent.analyze_evacuation_performance("test_run")

        assert result['run_id'] == "test_run"
        assert 'metrics' in result
        assert 'insights' in result
        assert 'bottlenecks' in result
        assert 'recommendations' in result

    def test_generate_insights_good_performance(self):
        """Test insights generation for good evacuation performance."""
        metrics = {
            'clearance_p50': 10.0,
            'clearance_p95': 18.0,
            'max_queue_length': 20.0,
            'max_platform_density': 3.0
        }

        insights = self.agent._generate_insights(metrics)

        assert len(insights) > 0
        # Should have positive insight for good performance
        assert any("Good evacuation performance" in insight for insight in insights)

    def test_generate_insights_concerning_performance(self):
        """Test insights generation for concerning evacuation performance."""
        metrics = {
            'clearance_p50': 20.0,
            'clearance_p95': 35.0,
            'max_queue_length': 45.0,
            'max_platform_density': 5.5
        }

        insights = self.agent._generate_insights(metrics)

        assert len(insights) > 0
        # Should have warning insights
        assert any("⚠️" in insight for insight in insights)

    def test_generate_insights_dangerous_conditions(self):
        """Test insights generation for dangerous conditions."""
        metrics = {
            'clearance_p50': 30.0,
            'clearance_p95': 50.0,
            'max_queue_length': 60.0,
            'max_platform_density': 7.0,
            'platform_overcrowding_time': 8.0
        }

        insights = self.agent._generate_insights(metrics)

        assert len(insights) > 0
        # Should have danger alerts
        assert any("🚨" in insight or "Dangerous" in insight for insight in insights)

    def test_analyze_bottlenecks(self):
        """Test bottleneck analysis."""
        # Mock metrics service responses
        def mock_calculate_single_metric(run_id, metric_config, data_path):
            if 'queue_len' in str(metric_config):
                return {
                    'edge:123': 35.0,
                    'edge:456': 40.0,
                    'edge:789': 25.0
                }
            elif 'density' in str(metric_config):
                return {
                    'station:A': 5.5,
                    'station:B': 6.0,
                    'station:C': 4.0
                }
            return {}

        self.mock_metrics_service.calculate_single_metric.side_effect = mock_calculate_single_metric

        bottlenecks = self.agent._analyze_bottlenecks("test_run")

        assert 'worst_edges' in bottlenecks
        assert 'worst_stations' in bottlenecks
        assert len(bottlenecks['worst_edges']) <= 3
        assert len(bottlenecks['worst_stations']) <= 3

        # Check that worst bottlenecks are at the top
        if bottlenecks['worst_edges']:
            first_queue = bottlenecks['worst_edges'][0]['max_queue']
            for edge in bottlenecks['worst_edges'][1:]:
                assert edge['max_queue'] <= first_queue

    def test_generate_recommendations_good_performance(self):
        """Test recommendations for good performance."""
        metrics = {
            'clearance_p95': 18.0
        }
        bottlenecks = {
            'worst_edges': [],
            'worst_stations': []
        }

        recommendations = self.agent._generate_recommendations(metrics, bottlenecks)

        assert len(recommendations) > 0
        # Should have positive feedback
        assert any("✅" in rec for rec in recommendations)

    def test_generate_recommendations_needs_improvement(self):
        """Test recommendations for areas needing improvement."""
        metrics = {
            'clearance_p95': 30.0,
            'platform_overcrowding_time': 5.0
        }
        bottlenecks = {
            'worst_edges': [
                {'location': 'edge:123', 'max_queue': 40.0}
            ],
            'worst_stations': [
                {'location': 'station:A', 'max_density': 6.5}
            ]
        }

        recommendations = self.agent._generate_recommendations(metrics, bottlenecks)

        assert len(recommendations) > 0
        # Should have actionable recommendations
        assert any("consider" in rec.lower() or "implement" in rec.lower() for rec in recommendations)

    def test_compare_scenarios_single_scenario(self):
        """Test comparing scenarios with single scenario."""
        self.mock_metrics_service.calculate_metrics.return_value = {
            'clearance_p50': 15.0,
            'clearance_p95': 25.0
        }

        self.mock_metrics_service.calculate_single_metric.return_value = {}

        comparison = self.agent.compare_scenarios(['run_1'])

        assert 'scenarios' in comparison
        assert len(comparison['scenarios']) == 1
        assert 'best_performer' in comparison
        assert comparison['best_performer'] == 'run_1'

    def test_compare_scenarios_multiple_scenarios(self):
        """Test comparing multiple scenarios."""
        call_count = [0]

        def mock_metrics(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return {
                    'clearance_p50': 15.0,
                    'clearance_p95': 25.0
                }
            else:
                return {
                    'clearance_p50': 18.0,
                    'clearance_p95': 30.0
                }

        self.mock_metrics_service.calculate_metrics.side_effect = mock_metrics
        self.mock_metrics_service.calculate_single_metric.return_value = {}

        comparison = self.agent.compare_scenarios(['run_1', 'run_2'])

        assert len(comparison['scenarios']) == 2
        # run_1 should be best (lower clearance time)
        assert comparison['best_performer'] == 'run_1'
        assert len(comparison['key_differences']) > 0

    def test_identify_key_differences_significant(self):
        """Test identifying significant differences between scenarios."""
        scenarios = {
            'run_1': {
                'metrics': {
                    'clearance_p95': 20.0
                }
            },
            'run_2': {
                'metrics': {
                    'clearance_p95': 35.0
                }
            }
        }

        differences = self.agent._identify_key_differences(scenarios)

        assert len(differences) > 0
        assert any("Significant clearance time difference" in diff for diff in differences)

    def test_identify_key_differences_minimal(self):
        """Test identifying minimal differences between scenarios."""
        scenarios = {
            'run_1': {
                'metrics': {
                    'clearance_p95': 20.0
                }
            },
            'run_2': {
                'metrics': {
                    'clearance_p95': 22.0
                }
            }
        }

        differences = self.agent._identify_key_differences(scenarios)

        # Difference is less than 5 minutes, should not be flagged
        assert len(differences) == 0

    def test_generate_report(self):
        """Test generating human-readable report."""
        self.mock_metrics_service.calculate_metrics.return_value = {
            'clearance_p50': 15.0,
            'clearance_p95': 25.0,
            'max_queue_length': 30.0
        }

        self.mock_metrics_service.calculate_single_metric.return_value = {
            'edge:123': 30.0,
            'station:A': 4.5
        }

        report = self.agent.generate_report("test_run")

        assert isinstance(report, str)
        assert "Evacuation Analysis Report" in report
        assert "test_run" in report
        assert "Key Metrics" in report
        assert "Insights" in report
        assert "Recommendations" in report

    def test_analyze_bottlenecks_no_data(self):
        """Test bottleneck analysis with no data."""
        self.mock_metrics_service.calculate_single_metric.return_value = None

        bottlenecks = self.agent._analyze_bottlenecks("test_run")

        assert 'worst_edges' in bottlenecks
        assert 'worst_stations' in bottlenecks
        assert len(bottlenecks['worst_edges']) == 0
        assert len(bottlenecks['worst_stations']) == 0

    def test_generate_insights_with_non_numeric_metrics(self):
        """Test insights generation with non-numeric metric values."""
        metrics = {
            'clearance_p50': 'N/A',
            'clearance_p95': None,
            'max_queue_length': 30.0
        }

        insights = self.agent._generate_insights(metrics)

        # Should handle gracefully without crashing
        assert isinstance(insights, list)

    def test_generate_insights_empty_metrics(self):
        """Test insights generation with empty metrics."""
        metrics = {}

        insights = self.agent._generate_insights(metrics)

        assert isinstance(insights, list)
        assert len(insights) == 0

    def test_compare_scenarios_with_missing_metrics(self):
        """Test comparing scenarios when some metrics are missing."""
        call_count = [0]

        def mock_metrics(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return {'clearance_p95': 25.0}
            else:
                return {'clearance_p95': 'error'}

        self.mock_metrics_service.calculate_metrics.side_effect = mock_metrics
        self.mock_metrics_service.calculate_single_metric.return_value = {}

        comparison = self.agent.compare_scenarios(['run_1', 'run_2'])

        # Should handle missing/invalid metrics gracefully
        assert 'scenarios' in comparison
        assert comparison['best_performer'] is not None


@pytest.mark.unit
class TestMetricsAgentEdgeCases:
    """Test edge cases and error conditions."""

    def setup_method(self):
        """Set up test environment."""
        self.mock_metrics_service = Mock()
        self.agent = MetricsAgent(metrics_service=self.mock_metrics_service)

    def test_analyze_evacuation_performance_with_exception(self):
        """Test analysis when metrics service raises exception."""
        self.mock_metrics_service.calculate_metrics.side_effect = Exception("Service error")

        with pytest.raises(Exception):
            self.agent.analyze_evacuation_performance("test_run")

    def test_analyze_bottlenecks_with_exception(self):
        """Test bottleneck analysis when service raises exception."""
        self.mock_metrics_service.calculate_single_metric.side_effect = Exception("Service error")

        with pytest.raises(Exception):
            self.agent._analyze_bottlenecks("test_run")

    def test_generate_report_with_dict_error_values(self):
        """Test report generation when metrics contain error dicts."""
        self.mock_metrics_service.calculate_metrics.return_value = {
            'clearance_p50': {'error': 'calculation failed'},
            'clearance_p95': 25.0,
            'max_queue_length': {'error': 'no data'}
        }

        self.mock_metrics_service.calculate_single_metric.return_value = {}

        report = self.agent.generate_report("test_run")

        # Should skip error values and only show valid metrics
        assert "Clearance P95" in report
        assert report.count("error") == 0  # Error dicts should not appear in report

    def test_compare_scenarios_empty_list(self):
        """Test comparing scenarios with empty list."""
        comparison = self.agent.compare_scenarios([])

        assert comparison['scenarios'] == {}
        assert comparison['best_performer'] is None

    def test_identify_key_differences_single_scenario(self):
        """Test identifying differences with only one scenario."""
        scenarios = {
            'run_1': {
                'metrics': {
                    'clearance_p95': 20.0
                }
            }
        }

        differences = self.agent._identify_key_differences(scenarios)

        # Can't compare with less than 2 scenarios
        assert len(differences) == 0

    def test_analyze_bottlenecks_returns_dict_without_items(self):
        """Test bottleneck analysis when result is not a dict."""
        self.mock_metrics_service.calculate_single_metric.return_value = "invalid_result"

        bottlenecks = self.agent._analyze_bottlenecks("test_run")

        # Should handle gracefully
        assert 'worst_edges' in bottlenecks
        assert 'worst_stations' in bottlenecks
        assert len(bottlenecks['worst_edges']) == 0
        assert len(bottlenecks['worst_stations']) == 0

    def test_standard_metrics_config_structure(self):
        """Test that standard metrics config has correct structure."""
        config = self.agent._load_standard_metrics()

        # Verify structure of each metric
        for metric_name, metric_config in config['metrics'].items():
            assert 'source' in metric_config
            assert 'operation' in metric_config
            assert metric_config['source'] in ['timeseries', 'events']

    def test_generate_insights_with_boundary_values(self):
        """Test insights generation with exact boundary values."""
        metrics = {
            'clearance_p95': 30.0,  # Exactly at warning threshold
            'max_queue_length': 40.0,  # Exactly at warning threshold
            'max_platform_density': 4.0,  # Exactly at warning threshold
        }

        insights = self.agent._generate_insights(metrics)

        # Should generate insights at boundary conditions
        assert len(insights) > 0
