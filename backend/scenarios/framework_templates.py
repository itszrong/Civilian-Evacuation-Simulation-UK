"""
London Mass Evacuation Framework Compliant Scenario Templates

Based on the London Mass Evacuation Framework (June 2018, v3.0)
These scenarios are designed for No.10 presentations and exercises.
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List

class FrameworkScenarioTemplates:
    """Framework-compliant scenario templates for London evacuation planning."""
    
    @staticmethod
    def get_templates() -> Dict[str, Dict[str, Any]]:
        """Get all framework-compliant scenario templates."""
        return {
            "mass_fluvial_flood_rwc": FrameworkScenarioTemplates.mass_fluvial_flood_rwc(),
            "large_chemical_release": FrameworkScenarioTemplates.large_chemical_release(),
            "medium_uxo_planned": FrameworkScenarioTemplates.medium_uxo_planned(),
            "small_gas_leak": FrameworkScenarioTemplates.small_gas_leak(),
            "terrorist_sudden_impact": FrameworkScenarioTemplates.terrorist_sudden_impact(),
            "rising_tide_flood": FrameworkScenarioTemplates.rising_tide_flood()
        }
    
    @staticmethod
    def mass_fluvial_flood_rwc() -> Dict[str, Any]:
        """Thames fluvial flood – pan-London Reasonable Worst Case scenario."""
        return {
            "scenario_id": str(uuid.uuid4()),
            "name": "Thames fluvial flood – pan-London RWC",
            "description": "Mass evacuation scenario based on Thames fluvial flooding affecting 150,000 people",
            "time": {
                "start": "2025-11-12T11:00:00Z",
                "duration_min": 1440
            },
            "hazard": {
                "type": "flood",
                "subtype": "fluvial",
                "polygon_wkt": "POLYGON((-0.3 51.45, -0.05 51.45, -0.05 51.55, -0.3 51.55, -0.3 51.45))",
                "buffer_m": 100
            },
            "scale": {
                "category": "mass",
                "people_affected_est": 150000,
                "properties_flooded_est": 50000
            },
            "population_profile": {
                "assisted_evacuation_needed": 55000,
                "stranded_needing_rescue": 4500,
                "stranded_assisted_in_situ": 1500
            },
            "assumptions": {
                "compliance": 0.7,
                "car_availability": 0.45,
                "self_evacuation_prop": 0.6,
                "reroute_period_s": 300,
                "note": "Modelling assumptions - not framework mandates"
            },
            "modes": ["walk", "bus", "rail", "car", "river"],
            "closures": {"edges": [], "nodes": []},
            "departure_profile": {
                "type": "logistic",
                "params": {"t50_min": 180, "steepness": 0.07}
            },
            "governance": {
                "coordination": {
                    "SCG": True,
                    "ESCG": True,
                    "LLACC": True,
                    "interlinks": ["GLT/DLUHC RED", "TfL", "BTP", "Met Police", "NHS", "EA"]
                },
                "activation_basis": ["risk_to_life_gt_risk_of_evac", "pan_london_coord_required"]
            },
            "operations": {
                "phases": ["initiate", "alert", "move", "shelter", "return"],
                "ELP_EDP_strategy": {
                    "use_public_transport": True,
                    "ELPs": "to_be_determined_on_day",
                    "EDPs": "to_be_determined_on_day",
                    "note": "Final confirmation on the day per SCG/ESCG/TfL/BTP"
                }
            },
            "comms": {
                "strategy_tier": ["inform", "reassure"],
                "channels": ["broadcast", "VMS", "rail/bus PA", "social"],
                "notes": "Messaging focused on safe routes and self-evac support. Content/clearance per LRCG/SCG",
                "authority": "LRCG coordinates strategic comms"
            },
            "kpis": ["clearance_p95", "borough_median_clearance", "platform_overcap_minutes"],
            "provenance": {
                "source": "London Mass Evacuation Framework v3.0 (June 2018)",
                "section": "Section 9.1 - Reasonable Worst Case",
                "compliance_level": "framework_exact"
            },
            "seed": 42
        }
    
    @staticmethod
    def large_chemical_release() -> Dict[str, Any]:
        """Central London chemical release – sudden impact scenario."""
        return {
            "scenario_id": str(uuid.uuid4()),
            "name": "Central London chemical release – sudden impact",
            "description": "Large-scale chemical incident requiring immediate evacuation with CBRN protocols",
            "time": {
                "start": "2025-10-05T14:10:00Z",
                "duration_min": 480
            },
            "hazard": {
                "type": "chemical",
                "subtype": "toxic_release",
                "polygon_wkt": "POLYGON((-0.15 51.5, -0.05 51.5, -0.05 51.52, -0.15 51.52, -0.15 51.5))",
                "buffer_m": 200
            },
            "scale": {
                "category": "large",
                "people_affected_est": 60000
            },
            "population_profile": {
                "assisted_evacuation_needed": 18000
            },
            "assumptions": {
                "compliance": 0.6,
                "car_availability": 0.35,
                "self_evacuation_prop": 0.7,
                "reroute_period_s": 180,
                "note": "Modelling assumptions - not framework mandates"
            },
            "modes": ["walk", "bus", "rail", "car"],
            "closures": {"edges": [], "nodes": []},
            "cbrn_policy": {
                "decon_required_prior_to_transport": True,
                "shelter_in_place_if_contaminated": True,
                "note": "Transport operators will not knowingly convey contaminated people"
            },
            "decision_context": {
                "police_strategic_pre_SCG": True,
                "consultation": "Police Strategic in consultation with LLAG"
            },
            "operations": {
                "phases": ["alert", "move", "shelter", "return"],
                "sudden_impact_constraints": ["no_pre_warning", "fragmented_self_evac"],
                "ELP_EDP_strategy": {"use_public_transport": True}
            },
            "comms": {
                "strategy_tier": ["be_ready_to_act"],
                "notes": "Do not convey contaminated people; prioritise route guidance. Content/clearance per LRCG/SCG",
                "authority": "LRCG coordinates strategic comms"
            },
            "kpis": ["clearance_p95", "max_queue_length_top5", "platform_overcap_minutes"],
            "provenance": {
                "source": "London Mass Evacuation Framework v3.0 (June 2018)",
                "section": "Large-scale scenarios with CBRN protocols",
                "compliance_level": "framework_compliant"
            },
            "seed": 73
        }
    
    @staticmethod
    def medium_uxo_planned() -> Dict[str, Any]:
        """Docklands UXO cordon – planned lift and evacuate scenario."""
        return {
            "scenario_id": str(uuid.uuid4()),
            "name": "Docklands UXO cordon – planned lift and evacuate",
            "description": "Medium-scale planned evacuation for unexploded ordnance disposal",
            "time": {
                "start": "2025-10-06T08:00:00Z",
                "duration_min": 360
            },
            "hazard": {
                "type": "UXO",
                "subtype": "unexploded_ordnance",
                "polygon_wkt": "POLYGON((0.0 51.5, 0.05 51.5, 0.05 51.52, 0.0 51.52, 0.0 51.5))",
                "buffer_m": 150
            },
            "scale": {
                "category": "medium",
                "people_affected_est": 18000
            },
            "assumptions": {
                "compliance": 0.85,
                "car_availability": 0.3,
                "self_evacuation_prop": 0.8,
                "reroute_period_s": 600,
                "note": "Modelling assumptions - not framework mandates"
            },
            "modes": ["walk", "bus", "rail"],
            "closures": {"edges": [], "nodes": []},
            "operations": {
                "phases": ["initiate", "alert", "move", "shelter", "return"],
                "ELP_EDP_strategy": {
                    "preselect_ELPs": ["Canary Wharf", "Canning Town"],
                    "preselect_EDPs": ["Stratford", "Lewisham"],
                    "note": "Exercise injects - final confirmation on the day per SCG/ESCG/TfL/BTP"
                }
            },
            "governance": {"SCG": True, "ESCG": True, "LLACC": True},
            "comms": {
                "strategy_tier": ["inform"],
                "notes": "Day-before messaging; staggered departure to avoid peak crush. Content/clearance per LRCG/SCG",
                "authority": "LRCG coordinates strategic comms"
            },
            "kpis": ["clearance_p95", "borough_median_clearance"],
            "provenance": {
                "source": "London Mass Evacuation Framework v3.0 (June 2018)",
                "section": "Medium-scale scenarios with UXO example",
                "compliance_level": "framework_compliant"
            },
            "seed": 9
        }
    
    @staticmethod
    def small_gas_leak() -> Dict[str, Any]:
        """Local gas leak – Southwark high street scenario."""
        return {
            "scenario_id": str(uuid.uuid4()),
            "name": "Local gas leak – Southwark high street",
            "description": "Small-scale local incident managed at borough level",
            "time": {
                "start": "2025-10-05T09:30:00Z",
                "duration_min": 180
            },
            "hazard": {
                "type": "gas_leak",
                "subtype": "natural_gas",
                "polygon_wkt": "POLYGON((-0.1 51.5, -0.09 51.5, -0.09 51.505, -0.1 51.505, -0.1 51.5))",
                "buffer_m": 30
            },
            "scale": {
                "category": "small",
                "people_affected_est": 800
            },
            "assumptions": {
                "compliance": 0.9,
                "car_availability": 0.25,
                "self_evacuation_prop": 0.9,
                "reroute_period_s": 900,
                "note": "Modelling assumptions - not framework mandates"
            },
            "modes": ["walk", "bus"],
            "closures": {"edges": [], "nodes": []},
            "governance": {
                "SCG": False,
                "ESCG": False,
                "local_control": True,
                "decision_authority": "Incident Controller / Operational/Tactical Commander"
            },
            "operations": {
                "phases": ["initiate", "alert", "move", "return"],
                "ELP_EDP_strategy": {"use_public_transport": True}
            },
            "comms": {
                "strategy_tier": ["be_ready_to_act"],
                "notes": "Local PA and SMS; shelter-in-shops if short duration. Local responders handle face-to-face advice",
                "authority": "Local responders coordinate"
            },
            "kpis": ["clearance_p95", "max_queue_length_top5"],
            "provenance": {
                "source": "London Mass Evacuation Framework v3.0 (June 2018)",
                "section": "Small-scale scenarios with local control",
                "compliance_level": "framework_compliant"
            },
            "seed": 100
        }
    
    @staticmethod
    def terrorist_sudden_impact() -> Dict[str, Any]:
        """Central sudden impact – multi-site cordons scenario."""
        return {
            "scenario_id": str(uuid.uuid4()),
            "name": "Central sudden impact – multi-site cordons",
            "description": "Large-scale terrorist incident with multiple cordons and transport dependencies",
            "time": {
                "start": "2025-10-05T18:40:00Z",
                "duration_min": 720
            },
            "hazard": {
                "type": "terrorist_event",
                "subtype": "multi_site",
                "polygon_wkt": "MULTIPOLYGON(((-0.15 51.5, -0.1 51.5, -0.1 51.52, -0.15 51.52, -0.15 51.5)), ((-0.05 51.49, 0.0 51.49, 0.0 51.51, -0.05 51.51, -0.05 51.49)))",
                "buffer_m": 100
            },
            "scale": {
                "category": "large",
                "people_affected_est": 80000
            },
            "assumptions": {
                "compliance": 0.55,
                "car_availability": 0.25,
                "self_evacuation_prop": 0.75,
                "reroute_period_s": 180,
                "responder_absenteeism_prop": 0.15,
                "note": "Modelling assumptions - not framework mandates"
            },
            "modes": ["walk", "bus", "rail", "car"],
            "closures": {"edges": [], "nodes": []},
            "decision_context": {
                "police_strategic_pre_SCG": True,
                "consultation": "Police Strategic in consultation with LLAG"
            },
            "operations": {
                "phases": ["alert", "move", "shelter", "return"],
                "sudden_impact_constraints": ["no_pre_warning", "self_evac_started"],
                "ELP_EDP_strategy": {
                    "use_public_transport": True,
                    "crowd_control_measures": "at stations led by operators with Police/BTP support (e.g., metering/queuing)"
                }
            },
            "governance": {"SCG": True, "ESCG": True, "LLACC": True},
            "comms": {
                "strategy_tier": ["be_ready_to_act", "reassure"],
                "notes": "Control self-evac flows; route to safe corridors; avoid overloading key hubs. Content/clearance per LRCG/SCG",
                "authority": "LRCG coordinates strategic comms"
            },
            "kpis": ["clearance_p95", "platform_overcap_minutes", "max_queue_length_top5"],
            "provenance": {
                "source": "London Mass Evacuation Framework v3.0 (June 2018)",
                "section": "Large-scale sudden impact scenarios",
                "compliance_level": "framework_compliant"
            },
            "seed": 21
        }
    
    @staticmethod
    def rising_tide_flood() -> Dict[str, Any]:
        """Rising-tide flood – Greenwich/Deptford reception scenario."""
        return {
            "scenario_id": str(uuid.uuid4()),
            "name": "Rising-tide flood – Greenwich/Deptford reception",
            "description": "Mass evacuation with explicit ELP/EDP coordination and borough reception",
            "time": {
                "start": "2025-11-20T06:00:00Z",
                "duration_min": 720
            },
            "hazard": {
                "type": "flood",
                "subtype": "rising_tide",
                "polygon_wkt": "POLYGON((0.0 51.47, 0.1 51.47, 0.1 51.52, 0.0 51.52, 0.0 51.47))",
                "buffer_m": 80
            },
            "scale": {
                "category": "mass",
                "people_affected_est": 110000
            },
            "assumptions": {
                "compliance": 0.75,
                "car_availability": 0.4,
                "self_evacuation_prop": 0.65,
                "reroute_period_s": 300,
                "note": "Modelling assumptions - not framework mandates"
            },
            "modes": ["walk", "bus", "rail", "river"],
            "river_mode_note": "River services may be used tactically for short movements; longer-distance lift is constrained by turnaround and safety",
            "closures": {"edges": [], "nodes": []},
            "operations": {
                "phases": ["initiate", "alert", "move", "shelter", "return"],
                "ELP_EDP_strategy": {
                    "preselect_ELPs": ["Greenwich", "Lewisham", "Canada Water"],
                    "preselect_EDPs": ["Bromley", "Croydon", "Bexleyheath"],
                    "notes": "Exercise injects - align with LLACC reception capacity. Final confirmation on the day per SCG/ESCG/TfL/BTP",
                    "shelter_framework_ref": "Shelter specifics per Mass Shelter Framework"
                }
            },
            "governance": {"SCG": True, "ESCG": True, "LLACC": True},
            "comms": {
                "strategy_tier": ["inform"],
                "notes": "Advance warnings; push safe corridors; emphasise self-evac where possible. Content/clearance per LRCG/SCG",
                "authority": "LRCG coordinates strategic comms"
            },
            "kpis": ["clearance_p95", "borough_median_clearance", "platform_overcap_minutes"],
            "provenance": {
                "source": "London Mass Evacuation Framework v3.0 (June 2018)",
                "section": "Rising tide scenarios with full five-phase handling",
                "compliance_level": "framework_compliant"
            },
            "seed": 314
        }
    
    @staticmethod
    def get_scenario_by_scale(scale: str) -> List[str]:
        """Get scenario template names by scale category."""
        scale_mapping = {
            "small": ["small_gas_leak"],
            "medium": ["medium_uxo_planned"],
            "large": ["large_chemical_release", "terrorist_sudden_impact"],
            "mass": ["mass_fluvial_flood_rwc", "rising_tide_flood"]
        }
        return scale_mapping.get(scale.lower(), [])
    
    @staticmethod
    def get_scenario_by_hazard(hazard_type: str) -> List[str]:
        """Get scenario template names by hazard type."""
        hazard_mapping = {
            "flood": ["mass_fluvial_flood_rwc", "rising_tide_flood"],
            "chemical": ["large_chemical_release"],
            "terrorist": ["terrorist_sudden_impact"],
            "uxo": ["medium_uxo_planned"],
            "gas": ["small_gas_leak"]
        }
        return hazard_mapping.get(hazard_type.lower(), [])
