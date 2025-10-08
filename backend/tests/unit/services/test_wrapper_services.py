"""
Unit tests for wrapper services (metrics, scenarios).

Tests verify stateless behavior and proper wrapping of builder classes.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

from services.metrics.metrics_service import MetricsService
from services.scenarios.scenario_service import ScenarioService


class TestMetricsService:
    """Test MetricsService wrapper."""

    def test_stateless_initialization(self):
        """Test that service is stateless."""
        service1 = MetricsService()
        service2 = MetricsService()

        assert service1 is not service2

    def test_get_standard_metrics_config_pure_function(self):
        """Test that standard config is pure function."""
        config1 = MetricsService.get_standard_metrics_config()
        config2 = MetricsService.get_standard_metrics_config()

        assert config1 == config2
        assert 'metrics' in config1
        assert len(config1['metrics']) > 0

    @patch('services.metrics.metrics_service.MetricsBuilder')
    def test_calculate_metrics_stateless(self, mock_builder_class):
        """Test that calculate_metrics doesn't store state."""
        # Setup mock
        mock_builder = MagicMock()
        mock_builder.calculate_metrics.return_value = {'metric1': 100}
        mock_builder_class.return_value = mock_builder

        # Call service
        result = MetricsService.calculate_metrics(
            run_id="test_run",
            metrics_config={'metrics': {}},
            data_path="/tmp/data"
        )

        assert result == {'metric1': 100}
        # Should create new builder each time (stateless)
        mock_builder_class.assert_called_with(data_path="/tmp/data")

    @patch('services.metrics.metrics_service.MetricsBuilder')
    def test_multiple_calls_create_new_builders(self, mock_builder_class):
        """Test that each call creates fresh builder (no shared state)."""
        mock_builder = MagicMock()
        mock_builder.calculate_metrics.return_value = {}
        mock_builder_class.return_value = mock_builder

        # Call twice
        MetricsService.calculate_metrics("run1", {}, "/path1")
        MetricsService.calculate_metrics("run2", {}, "/path2")

        # Should create builder twice
        assert mock_builder_class.call_count == 2


class TestScenarioService:
    """Test ScenarioService wrapper."""

    def test_stateless_initialization(self):
        """Test that service is stateless."""
        service1 = ScenarioService()
        service2 = ScenarioService()

        assert service1 is not service2

    def test_get_template_info_pure_function(self):
        """Test that template info is pure function."""
        info1 = ScenarioService.get_template_info()
        info2 = ScenarioService.get_template_info()

        assert info1 == info2
        assert 'framework_templates' in info1
        assert 'legacy_templates' in info1

    def test_get_framework_templates_pure_function(self):
        """Test that framework templates retrieval is pure."""
        templates1 = ScenarioService.get_framework_templates()
        templates2 = ScenarioService.get_framework_templates()

        # Check same keys (deterministic)
        assert set(templates1.keys()) == set(templates2.keys())
        assert isinstance(templates1, dict)
        assert len(templates1) > 0

        # Check that structure is the same
        for key in templates1.keys():
            assert key in templates2
            assert isinstance(templates1[key], dict)
            assert isinstance(templates2[key], dict)

    @patch('services.scenarios.scenario_service.ScenarioBuilder')
    def test_create_scenario_stateless(self, mock_builder_class):
        """Test that create_scenario doesn't store state."""
        # Setup mock
        mock_builder = MagicMock()
        mock_builder.create_scenario.return_value = {'scenario_id': 'test123'}
        mock_builder_class.return_value = mock_builder

        # Call service
        result = ScenarioService.create_scenario(
            template_name="flood_central",
            custom_params={},
            scenarios_path="/tmp/scenarios"
        )

        assert result == {'scenario_id': 'test123'}
        # Should create new builder each time
        mock_builder_class.assert_called_with(scenarios_path="/tmp/scenarios")

    @patch('services.scenarios.scenario_service.ScenarioBuilder')
    def test_create_framework_scenario_stateless(self, mock_builder_class):
        """Test framework scenario creation is stateless."""
        mock_builder = MagicMock()
        mock_builder.create_framework_scenario.return_value = {'scenario_id': 'framework123'}
        mock_builder_class.return_value = mock_builder

        result = ScenarioService.create_framework_scenario(
            template_name="mass_fluvial_flood_rwc",
            scenarios_path="/tmp/scenarios"
        )

        assert result == {'scenario_id': 'framework123'}
        mock_builder.create_framework_scenario.assert_called_once()

    def test_validate_scenario_stateless(self):
        """Test scenario validation is stateless."""
        scenario1 = {
            'name': 'Test',
            'hazard_type': 'flood',
            'duration_minutes': 120,
            'population_affected': 1000
        }

        # Call twice
        result1 = ScenarioService.validate_scenario(scenario1)
        result2 = ScenarioService.validate_scenario(scenario1)

        # Should be identical
        assert result1 == result2
        assert 'valid' in result1


class TestServicesConcurrency:
    """Test that services support concurrent operations."""

    @patch('services.metrics.metrics_service.MetricsBuilder')
    def test_concurrent_metrics_calculation(self, mock_builder_class):
        """Test that multiple metrics can be calculated concurrently."""
        mock_builder = MagicMock()
        mock_builder.calculate_metrics.return_value = {'metric': 1}
        mock_builder_class.return_value = mock_builder

        # Simulate concurrent calls
        results = []
        for i in range(5):
            result = MetricsService.calculate_metrics(f"run_{i}", {}, f"/path_{i}")
            results.append(result)

        # All should succeed
        assert len(results) == 5
        assert all(r == {'metric': 1} for r in results)

        # Should create 5 separate builders (no shared state)
        assert mock_builder_class.call_count == 5

    @patch('services.scenarios.scenario_service.ScenarioBuilder')
    def test_concurrent_scenario_creation(self, mock_builder_class):
        """Test that multiple scenarios can be created concurrently."""
        mock_builder = MagicMock()
        mock_builder.create_scenario.return_value = {'id': 'test'}
        mock_builder_class.return_value = mock_builder

        # Simulate concurrent calls
        scenarios = []
        for i in range(5):
            scenario = ScenarioService.create_scenario(
                template_name="flood_central",
                scenarios_path=f"/path_{i}"
            )
            scenarios.append(scenario)

        # All should succeed
        assert len(scenarios) == 5
        assert all(s == {'id': 'test'} for s in scenarios)

        # Should create 5 separate builders
        assert mock_builder_class.call_count == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
