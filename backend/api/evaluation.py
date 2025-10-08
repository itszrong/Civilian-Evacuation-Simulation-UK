"""
Evaluation API endpoints for framework compliance and golden standards.
"""

import structlog
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import json
from pathlib import Path

logger = structlog.get_logger(__name__)

router = APIRouter()

@router.get("/evaluation/goldens")
async def get_golden_standards() -> Dict[str, Any]:
    """
    Get golden standards and evaluation metrics derived from the London Mass Evacuation Framework.
    
    Returns information about available metrics, their sources, and evaluation criteria.
    """
    try:
        # Load golden standards
        goldens_path = Path(__file__).parent.parent / "evaluation" / "goldens.json"
        
        if goldens_path.exists():
            with open(goldens_path, 'r') as f:
                goldens_data = json.load(f)
        else:
            # Fallback data if file doesn't exist
            goldens_data = {
                "version": 1,
                "scenarios": {
                    "mass_flood_rwc": {"targets": {}},
                    "chemical_sudden": {"targets": {}},
                    "uxo_medium": {"targets": {}},
                    "local_gas_small": {"targets": {}},
                    "central_terror_large": {"targets": {}}
                }
            }
        
        # Extract all unique metrics from scenarios
        framework_metrics = set()
        for scenario_data in goldens_data.get("scenarios", {}).values():
            framework_metrics.update(scenario_data.get("targets", {}).keys())
        
        # Load evidence register data
        evidence_path = Path(__file__).parent.parent.parent / "research" / "evidence_register.csv"
        evidence_sources = []
        
        if evidence_path.exists():
            try:
                with open(evidence_path, 'r') as f:
                    lines = f.readlines()
                    for line in lines[1:]:  # Skip header
                        if line.strip():
                            parts = line.strip().split(',')
                            if len(parts) >= 6:
                                evidence_sources.append({
                                    "scenario": parts[0],
                                    "metric": parts[1],
                                    "evidence_title": parts[5],
                                    "publisher": parts[6] if len(parts) > 6 else "Unknown",
                                    "confidence": parts[9] if len(parts) > 9 else "medium"
                                })
            except Exception as e:
                logger.warning("Failed to load evidence register", error=str(e))
        
        return {
            "success": True,
            "framework_metrics": sorted(list(framework_metrics)),
            "source": "London Resilience Partnership - Mass Evacuation Framework v3.0 (June 2018)",
            "evidence_sources": [
                "Exercise Unified Response (2016) - London Fire Brigade",
                "7 July Review Committee Report (2006) - Greater London Authority", 
                "Grenfell Inquiry Phase 2 Report (2024) - UK Government",
                "National Flood Resilience Review (2016) - UK Government (DEFRA/Cabinet Office)"
            ],
            "golden_standards": goldens_data,
            "evidence_register": evidence_sources,
            "evaluation_available": True,
            "compliance_note": "Metrics evaluated against evidence-based thresholds from UK emergency planning exercises and historical incidents"
        }
        
    except Exception as e:
        logger.error("Failed to get golden standards", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get golden standards: {str(e)}")

@router.get("/evaluation/metrics/{scenario_type}")
async def get_scenario_metrics(scenario_type: str) -> Dict[str, Any]:
    """
    Get specific metrics and evaluation criteria for a scenario type.
    """
    try:
        goldens_path = Path(__file__).parent.parent / "evaluation" / "goldens.json"
        
        if not goldens_path.exists():
            raise HTTPException(status_code=404, detail="Golden standards not found")
        
        with open(goldens_path, 'r') as f:
            goldens_data = json.load(f)
        
        if scenario_type not in goldens_data.get("scenarios", {}):
            available_types = list(goldens_data.get("scenarios", {}).keys())
            raise HTTPException(
                status_code=404, 
                detail=f"Scenario type '{scenario_type}' not found. Available: {available_types}"
            )
        
        scenario_data = goldens_data["scenarios"][scenario_type]
        
        return {
            "success": True,
            "scenario_type": scenario_type,
            "description": scenario_data.get("description", ""),
            "targets": scenario_data.get("targets", {}),
            "rationale": scenario_data.get("rationale", ""),
            "source": "London Resilience Partnership - Mass Evacuation Framework v3.0 (June 2018)"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get scenario metrics", scenario_type=scenario_type, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get scenario metrics: {str(e)}")
