"""
Framework Scenarios API

Provides access to London Mass Evacuation Framework compliant scenarios
for No.10 presentations and exercises.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import structlog

from scenarios.builder import ScenarioBuilder
from scenarios.framework_templates import FrameworkScenarioTemplates

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/framework-scenarios", tags=["Framework Scenarios"])

class ScenarioRequest(BaseModel):
    template_name: str
    custom_params: Optional[Dict[str, Any]] = None
    scenario_name: Optional[str] = None

class ScenarioFilter(BaseModel):
    scale: Optional[str] = None
    hazard_type: Optional[str] = None

@router.get("/templates")
async def list_framework_templates():
    """List all available framework-compliant scenario templates."""
    try:
        builder = ScenarioBuilder()
        template_info = builder.get_template_info()
        
        return {
            "framework_templates": template_info["framework_templates"],
            "template_details": template_info["framework_details"],
            "source": "London Mass Evacuation Framework v3.0 (June 2018)",
            "compliance_note": "All framework templates are compliant with official guidance"
        }
    except Exception as e:
        logger.error("Failed to list framework templates", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list templates: {str(e)}")

@router.get("/templates/{template_name}")
async def get_framework_template(template_name: str):
    """Get details of a specific framework template."""
    try:
        templates = FrameworkScenarioTemplates.get_templates()
        
        if template_name not in templates:
            raise HTTPException(
                status_code=404, 
                detail=f"Template '{template_name}' not found. Available: {list(templates.keys())}"
            )
        
        template = templates[template_name]
        
        return {
            "template_name": template_name,
            "template": template,
            "compliance_level": template.get("provenance", {}).get("compliance_level", "unknown"),
            "source": template.get("provenance", {}).get("source", "unknown")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get framework template", template=template_name, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get template: {str(e)}")

@router.post("/create")
async def create_framework_scenario(request: ScenarioRequest):
    """Create a new scenario from a framework template."""
    try:
        builder = ScenarioBuilder()
        
        scenario = builder.create_framework_scenario(
            template_name=request.template_name,
            custom_params=request.custom_params,
            scenario_name=request.scenario_name
        )
        
        # Save the scenario
        scenario_path = builder.save_scenario(scenario)
        
        logger.info(
            "Created framework scenario",
            template=request.template_name,
            scenario_id=scenario["scenario_id"],
            path=scenario_path
        )
        
        return {
            "scenario": scenario,
            "saved_path": scenario_path,
            "compliance_level": scenario.get("provenance", {}).get("compliance_level", "unknown")
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to create framework scenario", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to create scenario: {str(e)}")

@router.get("/filter")
async def filter_scenarios(
    scale: Optional[str] = Query(None, description="Filter by scale: small, medium, large, mass"),
    hazard_type: Optional[str] = Query(None, description="Filter by hazard: flood, chemical, terrorist, uxo, gas")
):
    """Filter framework scenarios by scale or hazard type."""
    try:
        builder = ScenarioBuilder()
        
        matching_templates = []
        
        if scale:
            matching_templates.extend(builder.get_scenarios_by_scale(scale))
        
        if hazard_type:
            hazard_templates = builder.get_scenarios_by_hazard(hazard_type)
            if scale:
                # Intersection of both filters
                matching_templates = list(set(matching_templates) & set(hazard_templates))
            else:
                matching_templates.extend(hazard_templates)
        
        if not scale and not hazard_type:
            # Return all if no filters
            matching_templates = list(FrameworkScenarioTemplates.get_templates().keys())
        
        # Remove duplicates and get template details
        matching_templates = list(set(matching_templates))
        templates = FrameworkScenarioTemplates.get_templates()
        
        template_details = {
            name: {
                "name": templates[name]["name"],
                "description": templates[name]["description"],
                "scale": templates[name].get("scale", {}).get("category", "unknown"),
                "hazard_type": templates[name].get("hazard", {}).get("type", "unknown"),
                "compliance_level": templates[name].get("provenance", {}).get("compliance_level", "unknown")
            }
            for name in matching_templates if name in templates
        }
        
        return {
            "filters": {"scale": scale, "hazard_type": hazard_type},
            "matching_templates": matching_templates,
            "template_details": template_details,
            "count": len(matching_templates)
        }
        
    except Exception as e:
        logger.error("Failed to filter scenarios", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to filter scenarios: {str(e)}")

@router.get("/scales")
async def list_scales():
    """List available scale categories."""
    return {
        "scales": ["small", "medium", "large", "mass"],
        "descriptions": {
            "small": "Up to ~1,000 people - local control, no pan-London coordination",
            "medium": "1k-25k people - borough/multi-borough coordination",
            "large": "25k-100k people - pan-London coordination required",
            "mass": "100k+ people - full framework activation with all phases"
        }
    }

@router.get("/hazard-types")
async def list_hazard_types():
    """List available hazard types."""
    return {
        "hazard_types": ["flood", "chemical", "terrorist", "uxo", "gas"],
        "descriptions": {
            "flood": "Fluvial or tidal flooding scenarios",
            "chemical": "Chemical release requiring CBRN protocols",
            "terrorist": "Terrorist incidents with sudden impact",
            "uxo": "Unexploded ordnance requiring planned evacuation",
            "gas": "Gas leak incidents typically handled locally"
        }
    }

@router.get("/compliance-info")
async def get_compliance_info():
    """Get information about framework compliance levels."""
    return {
        "compliance_levels": {
            "framework_exact": "Exactly matches framework specifications and numbers",
            "framework_compliant": "Compliant with framework structure and principles",
            "legacy": "Pre-framework templates for comparison"
        },
        "source_document": "London Mass Evacuation Framework v3.0 (June 2018)",
        "key_features": [
            "Scale-based categorization (Small/Medium/Large/Mass)",
            "Governance structures (SCG/ESCG/LLACC)",
            "Five-phase approach for planned evacuations",
            "Sudden impact vs rising tide handling",
            "CBRN contamination protocols",
            "ELP/EDP (Evacuation Loading/Discharge Points) strategy",
            "LRCG communications coordination"
        ],
        "validation_note": "All scenarios reviewed against framework requirements for No.10 presentation accuracy"
    }
