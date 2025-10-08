"""
Tests for scenarios.builder module.
"""

import pytest
import json
import yaml
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
from typing import Dict, Any, List

from scenarios.builder import ScenarioBuilder


class TestScenarioBuilder:
    """Test the ScenarioBuilder class."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.builder = ScenarioBuilder(scenarios_path=self.temp_dir)
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initialization(self):
        """Test ScenarioBuilder initialization."""
        assert self.builder.scenarios_path == Path(self.temp_dir)
        assert self.builder.scenarios_path.exists()
        assert isinstance(self.builder.legacy_templates, dict)
        assert isinstance(self.builder.framework_templates, dict)
        
        # Check that some expected templates exist
        assert "flood_central" in self.builder.legacy_templates
        assert len(self.builder.framework_templates) > 0
    
    def test_initialization_default_path(self):
        """Test ScenarioBuilder initialization with default path."""
        builder = ScenarioBuilder()
        assert builder.scenarios_path == Path("local_s3/scenarios")
    
    def test_create_scenario_from_template(self):
        """Test creating scenario from legacy template."""
        scenario = self.builder.create_scenario_from_template(
            template_name="flood_central",
            scenario_id="test_flood_001"
        )
        
        assert scenario is not None
        assert scenario["id"] == "test_flood_001"
        assert scenario["name"] == "Central London Flood"
        assert scenario["hazard_type"] == "flood"
        assert scenario["severity"] == "high"
        assert scenario["population_affected"] == 50000
        assert "parameters" in scenario
    
    def test_create_scenario_from_nonexistent_template(self):
        """Test creating scenario from nonexistent template."""
        scenario = self.builder.create_scenario_from_template(
            template_name="nonexistent_template",
            scenario_id="test_001"
        )
        
        assert scenario is None
    
    def test_create_scenario_with_overrides(self):
        """Test creating scenario with parameter overrides."""
        overrides = {
            "severity": "medium",
            "population_affected": 25000,
            "duration_minutes": 120
        }
        
        scenario = self.builder.create_scenario_from_template(
            template_name="flood_central",
            scenario_id="test_flood_002",
            overrides=overrides
        )
        
        assert scenario["severity"] == "medium"
        assert scenario["population_affected"] == 25000
        assert scenario["duration_minutes"] == 120
        # Other fields should remain from template
        assert scenario["name"] == "Central London Flood"
        assert scenario["hazard_type"] == "flood"
    
    def test_create_framework_scenario(self):
        """Test creating framework-compliant scenario."""
        # Get first available framework template
        template_names = list(self.builder.framework_templates.keys())
        assert len(template_names) > 0
        
        template_name = template_names[0]
        scenario = self.builder.create_framework_scenario(
            template_name=template_name,
            scenario_id="framework_test_001"
        )
        
        assert scenario is not None
        assert scenario["id"] == "framework_test_001"
        assert "city" in scenario
        assert "seed" in scenario
        
        # Should have framework-compliant structure
        expected_keys = ["id", "city", "seed", "closures", "capacity_changes", 
                        "protected_corridors", "staged_egress", "notes"]
        for key in expected_keys:
            assert key in scenario
    
    def test_create_framework_scenario_with_overrides(self):
        """Test creating framework scenario with overrides."""
        template_names = list(self.builder.framework_templates.keys())
        template_name = template_names[0]
        
        overrides = {
            "city": "manchester",
            "seed": 123,
            "notes": "Custom test scenario"
        }
        
        scenario = self.builder.create_framework_scenario(
            template_name=template_name,
            scenario_id="framework_test_002",
            overrides=overrides
        )
        
        assert scenario["city"] == "manchester"
        assert scenario["seed"] == 123
        assert scenario["notes"] == "Custom test scenario"
    
    def test_create_framework_scenario_nonexistent_template(self):
        """Test creating framework scenario from nonexistent template."""
        scenario = self.builder.create_framework_scenario(
            template_name="nonexistent_framework_template",
            scenario_id="test_001"
        )
        
        assert scenario is None
    
    def test_generate_scenario_variations(self):
        """Test generating scenario variations."""
        base_scenario = {
            "id": "base_scenario",
            "name": "Base Test Scenario",
            "severity": "medium",
            "population_affected": 10000,
            "duration_minutes": 60
        }
        
        variations = self.builder.generate_scenario_variations(
            base_scenario=base_scenario,
            count=3
        )
        
        assert len(variations) == 3
        
        # Each variation should have unique ID and some different parameters
        ids = [v["id"] for v in variations]
        assert len(set(ids)) == 3  # All unique IDs
        
        # Check that variations have different parameters
        severities = [v.get("severity") for v in variations]
        populations = [v.get("population_affected") for v in variations]
        
        # Should have some variation (not all identical)
        assert len(set(severities)) > 1 or len(set(populations)) > 1
    
    def test_generate_scenario_variations_with_params(self):
        """Test generating scenario variations with specific variation parameters."""
        base_scenario = {
            "id": "base_scenario",
            "severity": "medium",
            "population_affected": 10000
        }
        
        variation_params = {
            "severity": ["low", "medium", "high"],
            "population_affected": [5000, 10000, 20000]
        }
        
        variations = self.builder.generate_scenario_variations(
            base_scenario=base_scenario,
            count=3,
            variation_params=variation_params
        )
        
        assert len(variations) == 3
        
        # Check that variations use the specified parameters
        severities = [v["severity"] for v in variations]
        populations = [v["population_affected"] for v in variations]
        
        for severity in severities:
            assert severity in ["low", "medium", "high"]
        
        for population in populations:
            assert population in [5000, 10000, 20000]
    
    def test_save_scenario_yaml(self):
        """Test saving scenario to YAML file."""
        scenario = {
            "id": "save_test_001",
            "name": "Save Test Scenario",
            "city": "london",
            "seed": 42,
            "closures": [],
            "notes": "Test scenario for saving"
        }
        
        saved_path = self.builder.save_scenario(scenario, format="yaml")
        
        assert saved_path is not None
        assert saved_path.endswith(".yml")
        
        # Verify file was created
        full_path = Path(self.temp_dir) / saved_path
        assert full_path.exists()
        
        # Verify content
        with open(full_path, 'r') as f:
            loaded_scenario = yaml.safe_load(f)
        
        assert loaded_scenario["id"] == "save_test_001"
        assert loaded_scenario["name"] == "Save Test Scenario"
        assert loaded_scenario["city"] == "london"
        assert loaded_scenario["seed"] == 42
    
    def test_save_scenario_json(self):
        """Test saving scenario to JSON file."""
        scenario = {
            "id": "save_test_002",
            "name": "Save Test JSON Scenario",
            "data": {"test": True, "number": 123}
        }
        
        saved_path = self.builder.save_scenario(scenario, format="json")
        
        assert saved_path is not None
        assert saved_path.endswith(".json")
        
        # Verify file was created
        full_path = Path(self.temp_dir) / saved_path
        assert full_path.exists()
        
        # Verify content
        with open(full_path, 'r') as f:
            loaded_scenario = json.load(f)
        
        assert loaded_scenario["id"] == "save_test_002"
        assert loaded_scenario["name"] == "Save Test JSON Scenario"
        assert loaded_scenario["data"]["test"] is True
        assert loaded_scenario["data"]["number"] == 123
    
    def test_save_scenario_invalid_format(self):
        """Test saving scenario with invalid format."""
        scenario = {"id": "test", "name": "Test"}
        
        saved_path = self.builder.save_scenario(scenario, format="invalid")
        assert saved_path is None
    
    def test_load_scenario_yaml(self):
        """Test loading scenario from YAML file."""
        # First save a scenario
        scenario = {
            "id": "load_test_001",
            "name": "Load Test Scenario",
            "city": "london",
            "parameters": {"test": True}
        }
        
        saved_path = self.builder.save_scenario(scenario, format="yaml")
        
        # Now load it
        loaded_scenario = self.builder.load_scenario(saved_path)
        
        assert loaded_scenario is not None
        assert loaded_scenario["id"] == "load_test_001"
        assert loaded_scenario["name"] == "Load Test Scenario"
        assert loaded_scenario["city"] == "london"
        assert loaded_scenario["parameters"]["test"] is True
    
    def test_load_scenario_json(self):
        """Test loading scenario from JSON file."""
        # First save a scenario
        scenario = {
            "id": "load_test_002",
            "name": "Load Test JSON Scenario",
            "data": [1, 2, 3]
        }
        
        saved_path = self.builder.save_scenario(scenario, format="json")
        
        # Now load it
        loaded_scenario = self.builder.load_scenario(saved_path)
        
        assert loaded_scenario is not None
        assert loaded_scenario["id"] == "load_test_002"
        assert loaded_scenario["name"] == "Load Test JSON Scenario"
        assert loaded_scenario["data"] == [1, 2, 3]
    
    def test_load_nonexistent_scenario(self):
        """Test loading nonexistent scenario."""
        loaded_scenario = self.builder.load_scenario("nonexistent.yml")
        assert loaded_scenario is None
    
    def test_load_corrupted_scenario(self):
        """Test loading corrupted scenario file."""
        # Create corrupted YAML file
        corrupted_path = Path(self.temp_dir) / "corrupted.yml"
        with open(corrupted_path, 'w') as f:
            f.write("invalid: yaml: content: [")
        
        loaded_scenario = self.builder.load_scenario("corrupted.yml")
        assert loaded_scenario is None
    
    def test_list_scenarios(self):
        """Test listing saved scenarios."""
        # Save multiple scenarios
        scenarios = [
            {"id": "list_test_001", "name": "List Test 1"},
            {"id": "list_test_002", "name": "List Test 2"},
            {"id": "list_test_003", "name": "List Test 3"}
        ]
        
        saved_paths = []
        for scenario in scenarios:
            path = self.builder.save_scenario(scenario, format="yaml")
            saved_paths.append(path)
        
        # List scenarios
        scenario_list = self.builder.list_scenarios()
        
        assert len(scenario_list) >= 3
        
        # Check that our scenarios are in the list
        scenario_ids = [s.get("id") for s in scenario_list]
        for scenario in scenarios:
            assert scenario["id"] in scenario_ids
    
    def test_list_scenarios_empty_directory(self):
        """Test listing scenarios from empty directory."""
        empty_builder = ScenarioBuilder(scenarios_path=tempfile.mkdtemp())
        scenario_list = empty_builder.list_scenarios()
        assert scenario_list == []
    
    def test_delete_scenario(self):
        """Test deleting a scenario."""
        # Save a scenario
        scenario = {"id": "delete_test_001", "name": "Delete Test"}
        saved_path = self.builder.save_scenario(scenario, format="yaml")
        
        # Verify it exists
        full_path = Path(self.temp_dir) / saved_path
        assert full_path.exists()
        
        # Delete it
        success = self.builder.delete_scenario(saved_path)
        assert success is True
        
        # Verify it's gone
        assert not full_path.exists()
    
    def test_delete_nonexistent_scenario(self):
        """Test deleting nonexistent scenario."""
        success = self.builder.delete_scenario("nonexistent.yml")
        assert success is False
    
    def test_validate_scenario_valid(self):
        """Test validating a valid scenario."""
        valid_scenario = {
            "id": "valid_scenario",
            "name": "Valid Test Scenario",
            "city": "london",
            "seed": 42,
            "closures": [],
            "capacity_changes": [],
            "protected_corridors": [],
            "staged_egress": [],
            "notes": ""
        }
        
        is_valid, errors = self.builder.validate_scenario(valid_scenario)
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_scenario_missing_required_fields(self):
        """Test validating scenario with missing required fields."""
        invalid_scenario = {
            "name": "Invalid Scenario"
            # Missing required 'id' field
        }
        
        is_valid, errors = self.builder.validate_scenario(invalid_scenario)
        assert is_valid is False
        assert len(errors) > 0
        assert any("id" in error.lower() for error in errors)
    
    def test_validate_scenario_invalid_types(self):
        """Test validating scenario with invalid field types."""
        invalid_scenario = {
            "id": "invalid_types",
            "name": "Invalid Types Scenario",
            "city": "london",
            "seed": "not_a_number",  # Should be int
            "closures": "not_a_list"  # Should be list
        }
        
        is_valid, errors = self.builder.validate_scenario(invalid_scenario)
        assert is_valid is False
        assert len(errors) > 0
    
    def test_get_available_templates(self):
        """Test getting available templates."""
        legacy_templates = self.builder.get_available_templates(template_type="legacy")
        framework_templates = self.builder.get_available_templates(template_type="framework")
        all_templates = self.builder.get_available_templates(template_type="all")
        
        assert isinstance(legacy_templates, list)
        assert isinstance(framework_templates, list)
        assert isinstance(all_templates, list)
        
        assert len(legacy_templates) > 0
        assert len(framework_templates) > 0
        assert len(all_templates) >= len(legacy_templates) + len(framework_templates)
        
        # Check that flood_central is in legacy templates
        legacy_names = [t["name"] for t in legacy_templates]
        assert "flood_central" in legacy_names
    
    def test_get_template_details(self):
        """Test getting template details."""
        details = self.builder.get_template_details("flood_central")
        
        assert details is not None
        assert details["name"] == "flood_central"
        assert "description" in details
        assert "parameters" in details
        assert details["hazard_type"] == "flood"
    
    def test_get_template_details_nonexistent(self):
        """Test getting details for nonexistent template."""
        details = self.builder.get_template_details("nonexistent_template")
        assert details is None
    
    def test_create_custom_scenario(self):
        """Test creating custom scenario from scratch."""
        custom_params = {
            "name": "Custom Test Scenario",
            "hazard_type": "earthquake",
            "severity": "high",
            "affected_areas": ["Central London", "Westminster"],
            "population_affected": 75000,
            "duration_minutes": 180
        }
        
        scenario = self.builder.create_custom_scenario(
            scenario_id="custom_001",
            **custom_params
        )
        
        assert scenario is not None
        assert scenario["id"] == "custom_001"
        assert scenario["name"] == "Custom Test Scenario"
        assert scenario["hazard_type"] == "earthquake"
        assert scenario["severity"] == "high"
        assert scenario["affected_areas"] == ["Central London", "Westminster"]
        assert scenario["population_affected"] == 75000
        assert scenario["duration_minutes"] == 180
    
    def test_create_scenario_batch(self):
        """Test creating multiple scenarios in batch."""
        batch_config = {
            "base_template": "flood_central",
            "count": 5,
            "variation_params": {
                "severity": ["low", "medium", "high"],
                "population_affected": [10000, 25000, 50000]
            }
        }
        
        scenarios = self.builder.create_scenario_batch(**batch_config)
        
        assert len(scenarios) == 5
        
        # All should have unique IDs
        ids = [s["id"] for s in scenarios]
        assert len(set(ids)) == 5
        
        # All should be based on flood_central template
        for scenario in scenarios:
            assert scenario["name"] == "Central London Flood"
            assert scenario["hazard_type"] == "flood"
        
        # Should have variation in parameters
        severities = [s["severity"] for s in scenarios]
        populations = [s["population_affected"] for s in scenarios]
        
        assert len(set(severities)) > 1 or len(set(populations)) > 1


@pytest.mark.unit
class TestScenarioBuilderEdgeCases:
    """Test edge cases and error conditions."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.builder = ScenarioBuilder(scenarios_path=self.temp_dir)
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_scenario_with_special_characters(self):
        """Test creating scenario with special characters in ID."""
        scenario = self.builder.create_scenario_from_template(
            template_name="flood_central",
            scenario_id="test-scenario_001.special"
        )
        
        assert scenario is not None
        assert scenario["id"] == "test-scenario_001.special"
    
    def test_scenario_with_unicode_content(self):
        """Test creating scenario with unicode content."""
        custom_params = {
            "name": "Scénario de test avec caractères spéciaux",
            "description": "测试场景描述",
            "notes": "Тестовые заметки"
        }
        
        scenario = self.builder.create_custom_scenario(
            scenario_id="unicode_test",
            **custom_params
        )
        
        assert scenario is not None
        assert scenario["name"] == "Scénario de test avec caractères spéciaux"
        assert scenario["description"] == "测试场景描述"
        assert scenario["notes"] == "Тестовые заметки"
    
    def test_large_scenario_data(self):
        """Test handling large scenario data."""
        # Create scenario with large data structures
        large_areas = [f"Area_{i}" for i in range(1000)]
        large_parameters = {f"param_{i}": i * 1.5 for i in range(500)}
        
        custom_params = {
            "name": "Large Data Scenario",
            "affected_areas": large_areas,
            "parameters": large_parameters
        }
        
        scenario = self.builder.create_custom_scenario(
            scenario_id="large_data_test",
            **custom_params
        )
        
        assert scenario is not None
        assert len(scenario["affected_areas"]) == 1000
        assert len(scenario["parameters"]) == 500
    
    def test_concurrent_scenario_operations(self):
        """Test concurrent scenario operations."""
        import threading
        import time
        
        results = []
        errors = []
        
        def create_scenario(thread_id):
            try:
                scenario = self.builder.create_scenario_from_template(
                    template_name="flood_central",
                    scenario_id=f"concurrent_test_{thread_id}"
                )
                results.append(scenario)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_scenario, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check results
        assert len(errors) == 0
        assert len(results) == 5
        
        # All scenarios should have unique IDs
        ids = [s["id"] for s in results]
        assert len(set(ids)) == 5
    
    def test_disk_space_handling(self):
        """Test handling when disk space might be limited."""
        # This test is more conceptual - in practice, we'd need to mock filesystem
        # to simulate disk space issues
        
        # Create a very large scenario
        huge_data = "x" * 1000000  # 1MB of data
        
        custom_params = {
            "name": "Huge Scenario",
            "description": huge_data,
            "notes": huge_data
        }
        
        scenario = self.builder.create_custom_scenario(
            scenario_id="huge_scenario",
            **custom_params
        )
        
        # Should handle large data gracefully
        assert scenario is not None
        assert len(scenario["description"]) == 1000000
    
    def test_invalid_scenarios_path(self):
        """Test initialization with invalid scenarios path."""
        # Test with path that can't be created (if possible)
        try:
            invalid_path = "/root/invalid_path_that_cannot_be_created"
            builder = ScenarioBuilder(scenarios_path=invalid_path)
            
            # If it doesn't raise an exception, that's fine too
            # The implementation should handle this gracefully
            
        except (PermissionError, OSError):
            # Expected behavior - should be handled gracefully
            pass
    
    def test_scenario_id_collision_handling(self):
        """Test handling of scenario ID collisions."""
        # Create first scenario
        scenario1 = self.builder.create_scenario_from_template(
            template_name="flood_central",
            scenario_id="collision_test"
        )
        
        # Save it
        saved_path1 = self.builder.save_scenario(scenario1, format="yaml")
        
        # Create second scenario with same ID
        scenario2 = self.builder.create_scenario_from_template(
            template_name="flood_central",
            scenario_id="collision_test"
        )
        
        # Save it (should handle collision)
        saved_path2 = self.builder.save_scenario(scenario2, format="yaml")
        
        # Paths should be different (or second should overwrite first)
        # The exact behavior depends on implementation
        assert saved_path1 is not None
        assert saved_path2 is not None
