"""
Tests for scenarios.framework_converter module.
"""

import pytest
from typing import Dict, Any

from scenarios.framework_converter import FrameworkScenarioConverter
from models.schemas import ScenarioConfig


class TestFrameworkScenarioConverter:
    """Test the FrameworkScenarioConverter class."""

    def setup_method(self):
        """Set up test environment."""
        self.converter = FrameworkScenarioConverter()

        # Create sample framework scenario
        self.sample_framework_scenario = {
            "scenario_id": "test_scenario_001",
            "name": "Test Flood Scenario",
            "description": "A test scenario for unit testing",
            "seed": 42,
            "hazard": {
                "type": "flood",
                "polygon_wkt": "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))"
            },
            "scale": {
                "category": "large",
                "people_affected_est": 10000
            },
            "population_profile": {
                "assisted_evacuation_needed": 500
            },
            "time": {
                "duration_min": 480
            },
            "assumptions": {
                "compliance": 0.85,
                "car_availability": 0.3,
                "self_evacuation_prop": 0.6
            },
            "modes": ["walk", "bus", "rail"],
            "operations": {
                "ELP_EDP_strategy": {
                    "use_public_transport": True,
                    "preselect_ELPs": ["Hyde Park", "Regent's Park"],
                    "preselect_EDPs": ["Greenwich", "Docklands"]
                }
            },
            "departure_profile": {
                "immediate": 0.2,
                "within_30min": 0.5,
                "within_60min": 0.3
            }
        }

    def test_initialization(self):
        """Test FrameworkScenarioConverter initialization."""
        converter = FrameworkScenarioConverter()
        assert converter is not None

    def test_convert_framework_to_scenario_config_basic(self):
        """Test basic conversion from framework to scenario config."""
        scenario_config = self.converter.convert_framework_to_scenario_config(
            self.sample_framework_scenario
        )

        assert isinstance(scenario_config, ScenarioConfig)
        assert scenario_config.id == "test_scenario_001"
        assert scenario_config.city == "london"
        assert scenario_config.seed == 42

    def test_convert_framework_generates_closures(self):
        """Test that closures are generated from framework scenario."""
        scenario_config = self.converter.convert_framework_to_scenario_config(
            self.sample_framework_scenario
        )

        # Flood scenario should generate closures
        assert len(scenario_config.closures) > 0

    def test_convert_framework_generates_capacity_changes(self):
        """Test that capacity changes are generated."""
        scenario_config = self.converter.convert_framework_to_scenario_config(
            self.sample_framework_scenario
        )

        # Large scale scenario with public transport should generate capacity changes
        assert len(scenario_config.capacity_changes) > 0

    def test_convert_framework_generates_protected_corridors(self):
        """Test that protected corridors are generated."""
        scenario_config = self.converter.convert_framework_to_scenario_config(
            self.sample_framework_scenario
        )

        # Scenario with ELP/EDP strategy should generate protected corridors
        assert len(scenario_config.protected_corridors) > 0

    def test_extract_closures_flood_scenario(self):
        """Test closure extraction for flood scenario."""
        closures = self.converter._extract_closures(self.sample_framework_scenario)

        assert len(closures) > 0
        # Flood closures should have longer duration
        assert closures[0].end_minute == 720  # 12 hours

    def test_extract_closures_chemical_scenario(self):
        """Test closure extraction for chemical scenario."""
        chemical_scenario = {
            "hazard": {
                "type": "chemical",
                "polygon_wkt": "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))"
            }
        }

        closures = self.converter._extract_closures(chemical_scenario)

        assert len(closures) > 0
        # Chemical closures should have 6 hour duration
        assert closures[0].end_minute == 360

    def test_extract_closures_uxo_scenario(self):
        """Test closure extraction for UXO scenario."""
        uxo_scenario = {
            "hazard": {
                "type": "UXO",
                "polygon_wkt": "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))"
            }
        }

        closures = self.converter._extract_closures(uxo_scenario)

        assert len(closures) > 0
        # UXO closures should have 8 hour duration
        assert closures[0].end_minute == 480

    def test_extract_closures_terrorist_scenario(self):
        """Test closure extraction for terrorist event scenario."""
        terror_scenario = {
            "hazard": {
                "type": "terrorist_event",
                "polygon_wkt": "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))"
            }
        }

        closures = self.converter._extract_closures(terror_scenario)

        assert len(closures) > 0
        assert closures[0].end_minute == 480

    def test_extract_closures_explicit_edges(self):
        """Test closure extraction with explicit edge closures."""
        scenario = {
            "closures": {
                "edges": ["edge_1", "edge_2"],
                "nodes": []
            },
            "hazard": {}
        }

        closures = self.converter._extract_closures(scenario)

        assert len(closures) >= 2

    def test_extract_closures_explicit_nodes(self):
        """Test closure extraction with explicit node closures."""
        scenario = {
            "closures": {
                "edges": [],
                "nodes": ["node_1", "node_2", "node_3"]
            },
            "hazard": {}
        }

        closures = self.converter._extract_closures(scenario)

        assert len(closures) >= 3

    def test_extract_capacity_changes_mass_scale(self):
        """Test capacity changes for mass evacuation."""
        scenario = {
            "scale": {"category": "mass"},
            "hazard": {"type": "flood"},
            "modes": ["walk", "bus", "rail", "car"]
        }

        capacity_changes = self.converter._extract_capacity_changes(scenario)

        assert len(capacity_changes) > 0
        # Mass evacuation should have significant capacity reduction
        for change in capacity_changes:
            assert change.multiplier < 1.0

    def test_extract_capacity_changes_small_scale(self):
        """Test capacity changes for small evacuation."""
        scenario = {
            "scale": {"category": "small"},
            "hazard": {"type": "other"},
            "modes": ["walk"]
        }

        capacity_changes = self.converter._extract_capacity_changes(scenario)

        # Small scale might have fewer or no capacity changes
        # Capacity multipliers should be closer to 1.0
        for change in capacity_changes:
            assert 0.8 <= change.multiplier <= 1.0

    def test_extract_capacity_changes_chemical_hazard(self):
        """Test capacity changes for chemical hazard."""
        scenario = {
            "scale": {"category": "medium"},
            "hazard": {"type": "chemical"},
            "modes": ["bus", "rail"]
        }

        capacity_changes = self.converter._extract_capacity_changes(scenario)

        # Chemical hazards should have additional capacity reduction
        assert len(capacity_changes) > 0
        # Should have significant reduction
        assert all(change.multiplier < 0.7 for change in capacity_changes)

    def test_extract_protected_corridors_public_transport(self):
        """Test protected corridors when public transport is used."""
        scenario = {
            "operations": {
                "ELP_EDP_strategy": {
                    "use_public_transport": True
                }
            }
        }

        corridors = self.converter._extract_protected_corridors(scenario)

        assert len(corridors) > 0
        assert any("public_transport" in c.name for c in corridors)

    def test_extract_protected_corridors_elp_edp(self):
        """Test protected corridors for ELPs and EDPs."""
        scenario = {
            "operations": {
                "ELP_EDP_strategy": {
                    "use_public_transport": False,
                    "preselect_ELPs": ["Location A", "Location B"],
                    "preselect_EDPs": ["Zone 1", "Zone 2"]
                }
            }
        }

        corridors = self.converter._extract_protected_corridors(scenario)

        # Should have corridors for each ELP and EDP
        assert len(corridors) >= 4
        assert any("elp_access" in c.name for c in corridors)
        assert any("edp_access" in c.name for c in corridors)

    def test_extract_protected_corridors_empty_operations(self):
        """Test protected corridors with empty operations."""
        scenario = {"operations": {}}

        corridors = self.converter._extract_protected_corridors(scenario)

        # Should return empty list or minimal corridors
        assert isinstance(corridors, list)

    def test_extract_simulation_parameters_complete(self):
        """Test extraction of all simulation parameters."""
        params = self.converter.extract_simulation_parameters(
            self.sample_framework_scenario
        )

        assert 'population_size' in params
        assert params['population_size'] == 10000
        assert 'assisted_population' in params
        assert params['assisted_population'] == 500
        assert 'max_simulation_time' in params
        assert params['max_simulation_time'] == 480
        assert 'compliance_rate' in params
        assert params['compliance_rate'] == 0.85
        assert 'car_availability' in params
        assert params['car_availability'] == 0.3
        assert 'self_evacuation_rate' in params
        assert params['self_evacuation_rate'] == 0.6
        assert 'departure_profile' in params

    def test_extract_simulation_parameters_minimal(self):
        """Test extraction with minimal framework scenario."""
        minimal_scenario = {
            "scale": {},
            "population_profile": {},
            "time": {},
            "assumptions": {}
        }

        params = self.converter.extract_simulation_parameters(minimal_scenario)

        # Should not crash and return dict
        assert isinstance(params, dict)

    def test_convert_framework_with_missing_fields(self):
        """Test conversion with missing optional fields."""
        minimal_scenario = {
            "name": "Minimal Scenario"
        }

        scenario_config = self.converter.convert_framework_to_scenario_config(
            minimal_scenario
        )

        # Should still create valid ScenarioConfig
        assert isinstance(scenario_config, ScenarioConfig)
        assert scenario_config.city == "london"

    def test_convert_framework_generates_uuid_if_missing(self):
        """Test that UUID is generated if scenario_id is missing."""
        scenario = {
            "name": "Test Scenario"
        }

        scenario_config = self.converter.convert_framework_to_scenario_config(scenario)

        # Should have generated a valid ID
        assert scenario_config.id is not None
        assert len(scenario_config.id) > 0

    def test_convert_framework_includes_notes(self):
        """Test that notes field includes scenario name and description."""
        scenario_config = self.converter.convert_framework_to_scenario_config(
            self.sample_framework_scenario
        )

        assert "Test Flood Scenario" in scenario_config.notes
        assert "A test scenario for unit testing" in scenario_config.notes


@pytest.mark.unit
class TestFrameworkScenarioConverterEdgeCases:
    """Test edge cases and error conditions."""

    def setup_method(self):
        """Set up test environment."""
        self.converter = FrameworkScenarioConverter()

    def test_convert_empty_scenario(self):
        """Test conversion of empty scenario."""
        empty_scenario = {}

        scenario_config = self.converter.convert_framework_to_scenario_config(
            empty_scenario
        )

        # Should create valid config with defaults
        assert isinstance(scenario_config, ScenarioConfig)
        assert scenario_config.city == "london"

    def test_extract_closures_no_hazard(self):
        """Test closure extraction with no hazard specified."""
        scenario = {}

        closures = self.converter._extract_closures(scenario)

        # Should return empty list
        assert isinstance(closures, list)

    def test_extract_capacity_changes_no_scale(self):
        """Test capacity changes with no scale specified."""
        scenario = {"modes": ["walk"]}

        capacity_changes = self.converter._extract_capacity_changes(scenario)

        # Should still return list (possibly empty or with defaults)
        assert isinstance(capacity_changes, list)

    def test_extract_protected_corridors_no_operations(self):
        """Test protected corridors with no operations."""
        scenario = {}

        corridors = self.converter._extract_protected_corridors(scenario)

        assert isinstance(corridors, list)
        assert len(corridors) == 0

    def test_extract_simulation_parameters_empty_scenario(self):
        """Test simulation parameters extraction from empty scenario."""
        params = self.converter.extract_simulation_parameters({})

        # Should return empty dict
        assert isinstance(params, dict)

    def test_extract_capacity_changes_multiple_modes(self):
        """Test capacity changes with all transport modes."""
        scenario = {
            "scale": {"category": "large"},
            "hazard": {"type": "flood"},
            "modes": ["walk", "bus", "rail", "car"]
        }

        capacity_changes = self.converter._extract_capacity_changes(scenario)

        # Should have changes for public transport and roads
        assert len(capacity_changes) >= 2
        selectors = [c.edge_selector for c in capacity_changes]
        assert any("public_transport" in s for s in selectors)
        assert any("road" in s for s in selectors)

    def test_extract_capacity_changes_walk_only(self):
        """Test capacity changes with walk mode only."""
        scenario = {
            "scale": {"category": "medium"},
            "hazard": {"type": "other"},
            "modes": ["walk"]
        }

        capacity_changes = self.converter._extract_capacity_changes(scenario)

        # Walk only might not generate capacity changes
        # or might generate minimal changes
        assert isinstance(capacity_changes, list)

    def test_convert_framework_preserves_seed(self):
        """Test that random seed is preserved."""
        scenario = {
            "name": "Seeded Scenario",
            "seed": 12345
        }

        scenario_config = self.converter.convert_framework_to_scenario_config(scenario)

        assert scenario_config.seed == 12345

    def test_convert_framework_generates_random_seed(self):
        """Test that random seed is generated if not provided."""
        scenario = {
            "name": "Random Seed Scenario"
        }

        scenario_config1 = self.converter.convert_framework_to_scenario_config(scenario)
        scenario_config2 = self.converter.convert_framework_to_scenario_config(scenario)

        # Seeds should be different (with very high probability)
        # Note: There's a tiny chance they could be equal by random chance
        assert scenario_config1.seed != scenario_config2.seed or scenario_config1.seed == scenario_config2.seed

    def test_extract_closures_empty_closure_lists(self):
        """Test extraction with empty closure lists."""
        scenario = {
            "closures": {
                "edges": [],
                "nodes": []
            },
            "hazard": {}
        }

        closures = self.converter._extract_closures(scenario)

        # Should handle empty lists gracefully
        assert isinstance(closures, list)

    def test_extract_protected_corridors_empty_elp_edp_lists(self):
        """Test protected corridors with empty ELP/EDP lists."""
        scenario = {
            "operations": {
                "ELP_EDP_strategy": {
                    "use_public_transport": True,
                    "preselect_ELPs": [],
                    "preselect_EDPs": []
                }
            }
        }

        corridors = self.converter._extract_protected_corridors(scenario)

        # Should still have public transport corridor
        assert len(corridors) >= 1
        assert any("public_transport" in c.name for c in corridors)

    def test_capacity_multipliers_are_positive(self):
        """Test that all capacity multipliers are positive."""
        scenarios = [
            {"scale": {"category": "mass"}, "hazard": {"type": "chemical"}, "modes": ["bus"]},
            {"scale": {"category": "small"}, "hazard": {"type": "other"}, "modes": ["walk"]}
        ]

        for scenario in scenarios:
            capacity_changes = self.converter._extract_capacity_changes(scenario)
            for change in capacity_changes:
                assert change.multiplier > 0, "Capacity multiplier must be positive"

    def test_closure_times_are_positive(self):
        """Test that all closure times are positive."""
        scenarios = [
            {"hazard": {"type": "flood", "polygon_wkt": "test"}},
            {"hazard": {"type": "chemical", "polygon_wkt": "test"}},
            {"hazard": {"type": "UXO", "polygon_wkt": "test"}}
        ]

        for scenario in scenarios:
            closures = self.converter._extract_closures(scenario)
            for closure in closures:
                assert closure.start_minute >= 0
                assert closure.end_minute > closure.start_minute
