"""
Simple Scenario Builder

Creates and manages evacuation scenarios for agent-driven simulations.
Focuses on practical scenario generation without complex dependencies.
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import yaml

from .framework_templates import FrameworkScenarioTemplates


class ScenarioBuilder:
    """Simple scenario builder for evacuation simulations."""
    
    def __init__(self, scenarios_path: Optional[str] = None):
        """
        Initialize scenario builder.
        
        Args:
            scenarios_path: Optional path to save scenarios
        """
        self.scenarios_path = Path(scenarios_path) if scenarios_path else Path("local_s3/scenarios")
        self.scenarios_path.mkdir(parents=True, exist_ok=True)
        
        # Predefined scenario templates (legacy)
        self.legacy_templates = self._load_templates()
        
        # Framework-compliant templates
        self.framework_templates = FrameworkScenarioTemplates.get_templates()
    
    def _load_templates(self) -> Dict[str, Any]:
        """Load predefined scenario templates."""
        return {
            "flood_central": {
                "name": "Central London Flood",
                "description": "Major flooding in central London affecting transport hubs",
                "hazard_type": "flood",
                "affected_areas": ["Westminster", "City of London", "Southwark"],
                "severity": "high",
                "duration_minutes": 240,
                "population_affected": 50000,
                "transport_disruption": 0.8,
                "parameters": {
                    "compliance_rate": 0.7,
                    "car_availability": 0.3,
                    "walking_speed_reduction": 0.6
                }
            },
            "fire_building": {
                "name": "High-Rise Building Fire",
                "description": "Fire in major office building requiring local evacuation",
                "hazard_type": "fire",
                "affected_areas": ["Canary Wharf"],
                "severity": "medium",
                "duration_minutes": 120,
                "population_affected": 5000,
                "transport_disruption": 0.3,
                "parameters": {
                    "compliance_rate": 0.9,
                    "car_availability": 0.4,
                    "walking_speed_reduction": 0.2
                }
            },
            "terrorist_threat": {
                "name": "Security Threat",
                "description": "Security threat requiring area evacuation",
                "hazard_type": "security",
                "affected_areas": ["Westminster"],
                "severity": "high",
                "duration_minutes": 180,
                "population_affected": 25000,
                "transport_disruption": 0.9,
                "parameters": {
                    "compliance_rate": 0.8,
                    "car_availability": 0.2,
                    "walking_speed_reduction": 0.1
                }
            },
            "chemical_spill": {
                "name": "Chemical Incident",
                "description": "Chemical spill requiring evacuation of industrial area",
                "hazard_type": "chemical",
                "affected_areas": ["Greenwich", "Lewisham"],
                "severity": "medium",
                "duration_minutes": 300,
                "population_affected": 15000,
                "transport_disruption": 0.5,
                "parameters": {
                    "compliance_rate": 0.6,
                    "car_availability": 0.5,
                    "walking_speed_reduction": 0.4
                }
            }
        }
    
    def create_scenario(
        self,
        template_name: Optional[str] = None,
        custom_params: Optional[Dict[str, Any]] = None,
        scenario_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new evacuation scenario.
        
        Args:
            template_name: Name of template to use (optional)
            custom_params: Custom parameters to override template
            scenario_name: Custom name for the scenario
            
        Returns:
            Complete scenario definition
        """
        scenario_id = str(uuid.uuid4())
        
        if template_name and template_name in self.framework_templates:
            # Start with framework template (preferred)
            scenario = self.framework_templates[template_name].copy()
        elif template_name and template_name in self.legacy_templates:
            # Start with legacy template
            scenario = self.legacy_templates[template_name].copy()
        else:
            # Create basic scenario
            scenario = {
                "name": "Custom Scenario",
                "description": "Custom evacuation scenario",
                "hazard_type": "general",
                "affected_areas": ["Central London"],
                "severity": "medium",
                "duration_minutes": 180,
                "population_affected": 10000,
                "transport_disruption": 0.5,
                "parameters": {
                    "compliance_rate": 0.7,
                    "car_availability": 0.4,
                    "walking_speed_reduction": 0.3
                }
            }
        
        # Override with custom parameters
        if custom_params:
            scenario.update(custom_params)
        
        # Override name if provided
        if scenario_name:
            scenario["name"] = scenario_name
        
        # Add metadata
        scenario.update({
            "scenario_id": scenario_id,
            "created_at": datetime.now().isoformat(),
            "version": "1.0",
            "status": "draft"
        })
        
        return scenario
    
    def save_scenario(self, scenario: Dict[str, Any]) -> str:
        """
        Save a scenario to disk.
        
        Args:
            scenario: Scenario definition
            
        Returns:
            Path to saved scenario file
        """
        scenario_id = scenario["scenario_id"]
        filename = f"scenario_{scenario_id}.yaml"
        filepath = self.scenarios_path / filename
        
        with open(filepath, 'w') as f:
            yaml.dump(scenario, f, default_flow_style=False, indent=2)
        
        return str(filepath)
    
    def load_scenario(self, scenario_id: str) -> Dict[str, Any]:
        """
        Load a scenario from disk.
        
        Args:
            scenario_id: Scenario ID
            
        Returns:
            Scenario definition
        """
        filename = f"scenario_{scenario_id}.yaml"
        filepath = self.scenarios_path / filename
        
        if not filepath.exists():
            raise FileNotFoundError(f"Scenario not found: {scenario_id}")
        
        with open(filepath, 'r') as f:
            return yaml.safe_load(f)
    
    def list_scenarios(self) -> List[Dict[str, Any]]:
        """
        List all saved scenarios.
        
        Returns:
            List of scenario summaries
        """
        scenarios = []
        
        for filepath in self.scenarios_path.glob("scenario_*.yaml"):
            try:
                with open(filepath, 'r') as f:
                    scenario = yaml.safe_load(f)
                    
                scenarios.append({
                    "scenario_id": scenario.get("scenario_id"),
                    "name": scenario.get("name"),
                    "description": scenario.get("description"),
                    "hazard_type": scenario.get("hazard_type"),
                    "severity": scenario.get("severity"),
                    "created_at": scenario.get("created_at"),
                    "status": scenario.get("status", "draft")
                })
            except Exception as e:
                print(f"Error loading scenario {filepath}: {e}")
        
        return scenarios
    
    def generate_scenario_variants(
        self,
        base_scenario: Dict[str, Any],
        variations: Dict[str, List[Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate multiple scenario variants from a base scenario.
        
        Args:
            base_scenario: Base scenario to vary
            variations: Dictionary of parameters to vary
            
        Returns:
            List of scenario variants
        """
        variants = []
        
        # Generate all combinations of variations
        import itertools
        
        keys = list(variations.keys())
        values = list(variations.values())
        
        for combination in itertools.product(*values):
            variant = base_scenario.copy()
            variant["scenario_id"] = str(uuid.uuid4())
            variant["created_at"] = datetime.now().isoformat()
            
            # Apply variations
            for key, value in zip(keys, combination):
                if "." in key:
                    # Handle nested parameters like "parameters.compliance_rate"
                    parts = key.split(".")
                    current = variant
                    for part in parts[:-1]:
                        if part not in current:
                            current[part] = {}
                        current = current[part]
                    current[parts[-1]] = value
                else:
                    variant[key] = value
            
            # Update name to reflect variation
            variant["name"] = f"{base_scenario['name']} (Variant {len(variants) + 1})"
            
            variants.append(variant)
        
        return variants
    
    def create_comparison_study(
        self,
        base_template: str,
        study_name: str,
        parameter_ranges: Dict[str, List[Any]]
    ) -> Dict[str, Any]:
        """
        Create a comparison study with multiple scenario variants.
        
        Args:
            base_template: Template to use as base
            study_name: Name of the study
            parameter_ranges: Parameters to vary across scenarios
            
        Returns:
            Study definition with all scenarios
        """
        if base_template not in self.templates:
            raise ValueError(f"Unknown template: {base_template}")
        
        base_scenario = self.create_scenario(base_template)
        variants = self.generate_scenario_variants(base_scenario, parameter_ranges)
        
        study = {
            "study_id": str(uuid.uuid4()),
            "name": study_name,
            "description": f"Comparison study based on {base_template} template",
            "base_template": base_template,
            "created_at": datetime.now().isoformat(),
            "scenarios": variants,
            "parameter_ranges": parameter_ranges
        }
        
        return study
    
    def get_template_info(self) -> Dict[str, Any]:
        """Get information about available templates."""
        framework_details = {
            name: {
                "name": template.get("name", "Unknown"),
                "description": template.get("description", "No description"),
                "hazard_type": template.get("hazard", {}).get("type", "unknown"),
                "scale": template.get("scale", {}).get("category", "unknown"),
                "compliance_level": template.get("provenance", {}).get("compliance_level", "unknown"),
                "source": template.get("provenance", {}).get("source", "unknown")
            }
            for name, template in self.framework_templates.items()
        }
        
        legacy_details = {
            name: {
                "name": template.get("name", "Unknown"),
                "description": template.get("description", "No description"),
                "hazard_type": template.get("hazard_type", "unknown"),
                "severity": template.get("severity", "unknown"),
                "compliance_level": "legacy"
            }
            for name, template in self.legacy_templates.items()
        }
        
        return {
            "framework_templates": list(self.framework_templates.keys()),
            "legacy_templates": list(self.legacy_templates.keys()),
            "framework_details": framework_details,
            "legacy_details": legacy_details,
            "recommended": "framework_templates"
        }
    
    def validate_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a scenario definition.
        
        Args:
            scenario: Scenario to validate
            
        Returns:
            Validation results
        """
        errors = []
        warnings = []
        
        # Required fields
        required_fields = ["name", "hazard_type", "duration_minutes", "population_affected"]
        for field in required_fields:
            if field not in scenario:
                errors.append(f"Missing required field: {field}")
        
        # Validate parameters
        if "parameters" in scenario:
            params = scenario["parameters"]
            
            if "compliance_rate" in params:
                rate = params["compliance_rate"]
                if not (0 <= rate <= 1):
                    errors.append("compliance_rate must be between 0 and 1")
            
            if "car_availability" in params:
                rate = params["car_availability"]
                if not (0 <= rate <= 1):
                    errors.append("car_availability must be between 0 and 1")
        
        # Validate duration
        if "duration_minutes" in scenario:
            duration = scenario["duration_minutes"]
            if duration <= 0:
                errors.append("duration_minutes must be positive")
            elif duration > 1440:  # 24 hours
                warnings.append("duration_minutes is very long (>24 hours)")
        
        # Validate population
        if "population_affected" in scenario:
            pop = scenario["population_affected"]
            if pop <= 0:
                errors.append("population_affected must be positive")
            elif pop > 1000000:  # 1 million
                warnings.append("population_affected is very large (>1M people)")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def create_framework_scenario(
        self,
        template_name: str,
        custom_params: Optional[Dict[str, Any]] = None,
        scenario_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a framework-compliant scenario.
        
        Args:
            template_name: Name of framework template to use
            custom_params: Custom parameters to override template
            scenario_name: Custom name for the scenario
            
        Returns:
            Complete framework-compliant scenario definition
        """
        if template_name not in self.framework_templates:
            raise ValueError(f"Framework template '{template_name}' not found. Available: {list(self.framework_templates.keys())}")
        
        # Start with framework template
        scenario = self.framework_templates[template_name].copy()
        
        # Override with custom parameters (deep merge for nested dicts)
        if custom_params:
            scenario = self._deep_merge(scenario, custom_params)
        
        # Override name if provided
        if scenario_name:
            scenario["name"] = scenario_name
        
        # Update metadata
        scenario.update({
            "scenario_id": str(uuid.uuid4()),
            "created_at": datetime.now().isoformat(),
            "version": "2.0",  # Framework version
            "status": "draft"
        })
        
        return scenario
    
    def get_scenarios_by_scale(self, scale: str) -> List[str]:
        """Get framework scenario templates by scale category."""
        return FrameworkScenarioTemplates.get_scenario_by_scale(scale)
    
    def get_scenarios_by_hazard(self, hazard_type: str) -> List[str]:
        """Get framework scenario templates by hazard type."""
        return FrameworkScenarioTemplates.get_scenario_by_hazard(hazard_type)
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries."""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result


def demo_scenario_builder():
    """Demonstrate scenario builder capabilities."""
    builder = ScenarioBuilder()
    
    print("🏗️  Scenario Builder Demo")
    print("=" * 50)
    
    # Show available templates
    print("\n📋 Available Templates:")
    template_info = builder.get_template_info()
    for name, details in template_info["template_details"].items():
        print(f"  - {name}: {details['name']} ({details['hazard_type']}, {details['severity']} severity)")
    
    # Create a scenario from template
    print("\n🔥 Creating fire scenario...")
    fire_scenario = builder.create_scenario("fire_building", scenario_name="Office Tower Fire")
    print(f"  ✓ Created scenario: {fire_scenario['name']}")
    print(f"  ✓ Scenario ID: {fire_scenario['scenario_id']}")
    print(f"  ✓ Population affected: {fire_scenario['population_affected']:,}")
    
    # Create scenario variants
    print("\n🔄 Creating scenario variants...")
    variations = {
        "parameters.compliance_rate": [0.6, 0.8, 0.9],
        "severity": ["medium", "high"]
    }
    
    variants = builder.generate_scenario_variants(fire_scenario, variations)
    print(f"  ✓ Generated {len(variants)} variants")
    
    for i, variant in enumerate(variants, 1):
        compliance = variant["parameters"]["compliance_rate"]
        severity = variant["severity"]
        print(f"    - Variant {i}: {compliance} compliance, {severity} severity")
    
    # Create a comparison study
    print("\n📊 Creating comparison study...")
    study = builder.create_comparison_study(
        "flood_central",
        "Flood Response Comparison",
        {
            "parameters.compliance_rate": [0.6, 0.7, 0.8],
            "transport_disruption": [0.7, 0.8, 0.9]
        }
    )
    
    print(f"  ✓ Created study: {study['name']}")
    print(f"  ✓ Study ID: {study['study_id']}")
    print(f"  ✓ Number of scenarios: {len(study['scenarios'])}")
    
    # Validate a scenario
    print("\n✅ Validating scenario...")
    validation = builder.validate_scenario(fire_scenario)
    print(f"  ✓ Valid: {validation['valid']}")
    if validation['errors']:
        print(f"  ✗ Errors: {validation['errors']}")
    if validation['warnings']:
        print(f"  ⚠️  Warnings: {validation['warnings']}")
    
    print("\n" + "=" * 50)
    print("✅ Scenario builder demo completed!")


if __name__ == "__main__":
    demo_scenario_builder()
