"""
Framework Scenario Converter

Converts framework-compliant scenarios (JSON) to executable ScenarioConfig objects
that can be run by the simulation engine.
"""

import uuid
import random
from typing import Dict, Any, List
from models.schemas import ScenarioConfig, PolygonCordon, CapacityChange, ProtectedCorridor
import structlog

logger = structlog.get_logger(__name__)

class FrameworkScenarioConverter:
    """Converts framework scenarios to executable simulation configs."""
    
    def __init__(self):
        pass
    
    def convert_framework_to_scenario_config(self, framework_scenario: Dict[str, Any]) -> ScenarioConfig:
        """
        Convert a framework-compliant scenario to a ScenarioConfig.
        
        Args:
            framework_scenario: Framework scenario JSON
            
        Returns:
            ScenarioConfig object ready for simulation
        """
        logger.info("Converting framework scenario to simulation config", 
                   scenario_name=framework_scenario.get("name", "unknown"))
        
        # Extract basic info
        scenario_id = framework_scenario.get("scenario_id", str(uuid.uuid4()))
        scenario_name = framework_scenario.get("name", "Framework Scenario")
        
        # Convert framework fields to simulation parameters
        closures = self._extract_closures(framework_scenario)
        capacity_changes = self._extract_capacity_changes(framework_scenario)
        protected_corridors = self._extract_protected_corridors(framework_scenario)
        
        # Create ScenarioConfig
        scenario_config = ScenarioConfig(
            id=scenario_id,
            city="london",  # Framework scenarios are London-based
            seed=framework_scenario.get("seed", random.randint(1, 10000)),
            closures=closures,
            capacity_changes=capacity_changes,
            protected_corridors=protected_corridors,
            staged_egress=[],  # Framework doesn't specify staged egress
            notes=f"Framework scenario: {scenario_name}. {framework_scenario.get('description', '')}"
        )
        
        logger.info("Framework scenario converted successfully", 
                   scenario_id=scenario_id,
                   closures_count=len(closures),
                   capacity_changes_count=len(capacity_changes))
        
        return scenario_config
    
    def _extract_closures(self, framework_scenario: Dict[str, Any]) -> List[PolygonCordon]:
        """Extract closures from framework scenario."""
        closures = []
        
        # Check for explicit closures
        if "closures" in framework_scenario:
            closure_data = framework_scenario["closures"]
            
            # Handle edge closures
            if "edges" in closure_data and closure_data["edges"]:
                for edge in closure_data["edges"]:
                    closures.append(PolygonCordon(
                        type="polygon_cordon",
                        area=str(edge),
                        start_minute=0,
                        end_minute=480  # 8 hours default
                    ))
            
            # Handle node closures
            if "nodes" in closure_data and closure_data["nodes"]:
                for node in closure_data["nodes"]:
                    closures.append(PolygonCordon(
                        type="polygon_cordon", 
                        area=str(node),
                        start_minute=0,
                        end_minute=480  # 8 hours default
                    ))
        
        # Infer closures from hazard type and scale
        hazard = framework_scenario.get("hazard", {})
        scale = framework_scenario.get("scale", {})
        
        if hazard.get("type") == "flood":
            # For flood scenarios, create area closures based on polygon
            if hazard.get("polygon_wkt"):
                closures.append(PolygonCordon(
                    type="polygon_cordon",
                    area=hazard["polygon_wkt"],
                    start_minute=0,
                    end_minute=720  # 12 hours for flood
                ))
        
        elif hazard.get("type") == "chemical":
            # For chemical scenarios, create buffer zones
            if hazard.get("polygon_wkt"):
                closures.append(PolygonCordon(
                    type="polygon_cordon",
                    area=hazard["polygon_wkt"], 
                    start_minute=0,
                    end_minute=360  # 6 hours for chemical
                ))
        
        elif hazard.get("type") in ["UXO", "terrorist_event"]:
            # For UXO/terrorist scenarios, create cordons
            if hazard.get("polygon_wkt"):
                closures.append(PolygonCordon(
                    type="polygon_cordon",
                    area=hazard["polygon_wkt"],
                    start_minute=0,
                    end_minute=480  # 8 hours for UXO/terror
                ))
        
        return closures
    
    def _extract_capacity_changes(self, framework_scenario: Dict[str, Any]) -> List[CapacityChange]:
        """Extract capacity changes from framework scenario."""
        capacity_changes = []
        
        # Check assumptions for transport disruption
        assumptions = framework_scenario.get("assumptions", {})
        
        # Apply general capacity reduction based on scenario severity
        scale = framework_scenario.get("scale", {})
        hazard = framework_scenario.get("hazard", {})
        
        # Determine capacity multiplier based on scenario type and scale
        if scale.get("category") == "mass":
            # Mass evacuations have significant capacity reduction
            multiplier = 0.6  # 40% reduction
        elif scale.get("category") == "large":
            multiplier = 0.7  # 30% reduction  
        elif scale.get("category") == "medium":
            multiplier = 0.8  # 20% reduction
        else:  # small
            multiplier = 0.9  # 10% reduction
        
        # Additional reductions for specific hazard types
        if hazard.get("type") == "flood":
            multiplier *= 0.8  # Additional 20% reduction for flooding
        elif hazard.get("type") == "chemical":
            multiplier *= 0.7  # Additional 30% reduction for chemical hazards
        
        # Apply capacity change to all transport modes
        modes = framework_scenario.get("modes", ["walk", "bus", "rail", "car"])
        
        if "bus" in modes or "rail" in modes:
            capacity_changes.append(CapacityChange(
                edge_selector="public_transport",
                multiplier=multiplier
            ))
        
        if "car" in modes:
            capacity_changes.append(CapacityChange(
                edge_selector="road_network", 
                multiplier=multiplier * 0.9  # Cars more affected by congestion
            ))
        
        return capacity_changes
    
    def _extract_protected_corridors(self, framework_scenario: Dict[str, Any]) -> List[ProtectedCorridor]:
        """Extract protected corridors from framework scenario."""
        protected_corridors = []
        
        # Check operations for ELP/EDP strategy
        operations = framework_scenario.get("operations", {})
        elp_edp = operations.get("ELP_EDP_strategy", {})
        
        # If public transport is used, protect those corridors
        if elp_edp.get("use_public_transport"):
            protected_corridors.append(ProtectedCorridor(
                name="public_transport_corridors",
                rule="increase_capacity",
                multiplier=1.2  # 20% increase for protected routes
            ))
        
        # Check for pre-selected ELPs and EDPs
        if "preselect_ELPs" in elp_edp:
            for elp in elp_edp["preselect_ELPs"]:
                protected_corridors.append(ProtectedCorridor(
                    name=f"elp_access_{elp.lower().replace(' ', '_')}",
                    rule="increase_capacity", 
                    multiplier=1.3
                ))
        
        if "preselect_EDPs" in elp_edp:
            for edp in elp_edp["preselect_EDPs"]:
                protected_corridors.append(ProtectedCorridor(
                    name=f"edp_access_{edp.lower().replace(' ', '_')}",
                    rule="increase_capacity",
                    multiplier=1.3
                ))
        
        return protected_corridors
    
    def extract_simulation_parameters(self, framework_scenario: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract simulation parameters from framework scenario.
        
        Returns additional parameters for the simulation engine.
        """
        params = {}
        
        # Extract population parameters
        scale = framework_scenario.get("scale", {})
        population_profile = framework_scenario.get("population_profile", {})
        
        if "people_affected_est" in scale:
            params["population_size"] = scale["people_affected_est"]
        
        if "assisted_evacuation_needed" in population_profile:
            params["assisted_population"] = population_profile["assisted_evacuation_needed"]
        
        # Extract timing parameters
        time_config = framework_scenario.get("time", {})
        if "duration_min" in time_config:
            params["max_simulation_time"] = time_config["duration_min"]
        
        # Extract behavioral parameters
        assumptions = framework_scenario.get("assumptions", {})
        if "compliance" in assumptions:
            params["compliance_rate"] = assumptions["compliance"]
        
        if "car_availability" in assumptions:
            params["car_availability"] = assumptions["car_availability"]
        
        if "self_evacuation_prop" in assumptions:
            params["self_evacuation_rate"] = assumptions["self_evacuation_prop"]
        
        # Extract departure profile
        departure_profile = framework_scenario.get("departure_profile", {})
        if departure_profile:
            params["departure_profile"] = departure_profile
        
        return params
