"""
Framework Evaluator

Evaluates simulation results against golden standards derived from
UK Mass Evacuation Framework and historical exercises.
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)

class EvalStatus(Enum):
    """Evaluation status levels."""
    OK = "ok"
    AMBER = "amber" 
    FAIL = "fail"
    UNKNOWN = "unknown"

class FrameworkEvaluator:
    """Evaluator for framework-compliant scenarios."""
    
    def __init__(self, goldens_path: Optional[str] = None):
        """
        Initialize evaluator with golden standards.
        
        Args:
            goldens_path: Path to goldens.json file
        """
        if goldens_path:
            self.goldens_path = Path(goldens_path)
        else:
            self.goldens_path = Path(__file__).parent / "goldens.json"
        
        self.goldens = self._load_goldens()
        
    def _load_goldens(self) -> Dict[str, Any]:
        """Load golden standards from JSON file."""
        try:
            with open(self.goldens_path, 'r') as f:
                goldens = json.load(f)
            logger.info("Loaded golden standards", version=goldens.get("version", "unknown"))
            return goldens
        except Exception as e:
            logger.error("Failed to load golden standards", error=str(e))
            return {"version": 0, "scenarios": {}, "common_metrics": {}}
    
    def evaluate_scenario_result(
        self, 
        scenario_template: str,
        metrics: Dict[str, Union[float, int, List[float]]],
        scenario_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a scenario result against golden standards.
        Now supports Mesa simulation metrics.
        
        Args:
            scenario_template: Template name (e.g., 'mass_fluvial_flood_rwc')
            metrics: Computed metrics from simulation
            scenario_data: Optional scenario configuration data
            
        Returns:
            Evaluation results with status per metric
        """
        # Check if metrics are from Mesa (real) or heuristic (estimate)
        is_mesa_simulation = metrics.get('simulation_engine') == 'mesa_agent_based'
        confidence_level = 'MEDIUM' if is_mesa_simulation else 'VERY_LOW'
        
        # Map Mesa metric names to framework metric names
        mesa_to_framework = {
            'clearance_time_p50': 'clearance_p50_minutes',
            'clearance_time_p95': 'clearance_p95_minutes',
            'max_queue_length': 'queue_len_p95',
            'total_evacuated': 'evacuees_total',
        }
        
        # Convert Mesa metrics to framework format if needed
        framework_metrics = dict(metrics)
        for mesa_name, framework_name in mesa_to_framework.items():
            if mesa_name in metrics and framework_name not in metrics:
                framework_metrics[framework_name] = metrics[mesa_name]
        
        # Use converted metrics for evaluation
        metrics = framework_metrics
        
        # Map template names to golden scenario keys
        template_mapping = {
            "mass_fluvial_flood_rwc": "mass_flood_rwc",
            "large_chemical_release": "chemical_sudden", 
            "medium_uxo_planned": "uxo_medium",
            "small_gas_leak": "local_gas_small",
            "terrorist_sudden_impact": "central_terror_large",
            "rising_tide_flood": "mass_flood_rwc"  # Similar to mass flood
        }
        
        golden_key = template_mapping.get(scenario_template, scenario_template)
        
        if golden_key not in self.goldens["scenarios"]:
            logger.warning("No golden standards for scenario", scenario=scenario_template)
            return {
                "scenario_template": scenario_template,
                "golden_key": golden_key,
                "status": EvalStatus.UNKNOWN.value,
                "message": f"No golden standards available for {scenario_template}",
                "evaluations": {}
            }
        
        golden_targets = self.goldens["scenarios"][golden_key]["targets"]
        common_targets = self.goldens["common_metrics"]
        
        evaluations = {}
        overall_status = EvalStatus.OK
        
        # Evaluate each metric
        for metric_name, target in golden_targets.items():
            if metric_name in metrics:
                eval_result = self._evaluate_metric(
                    metric_name, 
                    metrics[metric_name], 
                    target,
                    scenario_data
                )
                evaluations[metric_name] = eval_result
                
                # Update overall status
                if eval_result["status"] == EvalStatus.FAIL.value:
                    overall_status = EvalStatus.FAIL
                elif eval_result["status"] == EvalStatus.AMBER.value and overall_status == EvalStatus.OK:
                    overall_status = EvalStatus.AMBER
        
        # Evaluate common metrics
        for metric_name, target in common_targets.items():
            if metric_name in metrics:
                eval_result = self._evaluate_metric(
                    metric_name,
                    metrics[metric_name],
                    target,
                    scenario_data
                )
                evaluations[metric_name] = eval_result
                
                if eval_result["status"] == EvalStatus.FAIL.value:
                    overall_status = EvalStatus.FAIL
                elif eval_result["status"] == EvalStatus.AMBER.value and overall_status == EvalStatus.OK:
                    overall_status = EvalStatus.AMBER
        
        return {
            "scenario_template": scenario_template,
            "golden_key": golden_key,
            "status": overall_status.value,
            "evaluations": evaluations,
            "golden_rationale": self.goldens["scenarios"][golden_key].get("rationale", ""),
            "evidence_sources": self._get_evidence_sources(golden_key),
            "evaluation_timestamp": self._get_timestamp()
        }
    
    def _evaluate_metric(
        self, 
        metric_name: str, 
        actual_value: Union[float, int, List[float]], 
        target: Union[float, int, List[Union[float, int]]],
        scenario_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Evaluate a single metric against its target."""
        
        # Handle list targets (ranges)
        if isinstance(target, list) and len(target) == 2:
            min_val, max_val = target
            
            if isinstance(actual_value, (list, np.ndarray)):
                # For array metrics, use appropriate aggregation
                if "p95" in metric_name:
                    actual = np.percentile(actual_value, 95)
                elif "p50" in metric_name:
                    actual = np.percentile(actual_value, 50)
                elif "max" in metric_name:
                    actual = np.max(actual_value)
                elif "mean" in metric_name or "avg" in metric_name:
                    actual = np.mean(actual_value)
                else:
                    actual = np.mean(actual_value)  # Default
            else:
                actual = actual_value
            
            # Evaluate against range
            if min_val <= actual <= max_val:
                status = EvalStatus.OK
                message = f"Within target range [{min_val}, {max_val}]"
            elif actual < min_val:
                # Below minimum - could be good or bad depending on metric
                if self._is_lower_better(metric_name):
                    status = EvalStatus.OK
                    message = f"Below target range (better): {actual} < {min_val}"
                else:
                    status = EvalStatus.AMBER
                    message = f"Below target range: {actual} < {min_val}"
            else:  # actual > max_val
                if self._is_lower_better(metric_name):
                    status = EvalStatus.FAIL
                    message = f"Above target range (worse): {actual} > {max_val}"
                else:
                    status = EvalStatus.AMBER
                    message = f"Above target range: {actual} > {max_val}"
        
        # Handle single value targets (maximums)
        else:
            if isinstance(actual_value, (list, np.ndarray)):
                if "p95" in metric_name:
                    actual = np.percentile(actual_value, 95)
                elif "max" in metric_name:
                    actual = np.max(actual_value)
                else:
                    actual = np.mean(actual_value)
            else:
                actual = actual_value
            
            if actual <= target:
                status = EvalStatus.OK
                message = f"Within limit: {actual} <= {target}"
            else:
                # Determine severity based on how far over
                overage_ratio = actual / target
                if overage_ratio <= 1.2:  # 20% over
                    status = EvalStatus.AMBER
                    message = f"Slightly over limit: {actual} > {target} ({overage_ratio:.1%})"
                else:
                    status = EvalStatus.FAIL
                    message = f"Significantly over limit: {actual} > {target} ({overage_ratio:.1%})"
        
        # Determine confidence based on simulation source
        is_mesa = scenario_data and scenario_data.get('simulation_engine') == 'mesa_agent_based'
        base_confidence = self._get_metric_confidence(metric_name)
        
        # Upgrade confidence for Mesa simulations
        if is_mesa:
            if base_confidence == "low":
                confidence = "medium"
            elif base_confidence == "medium":
                confidence = "medium"  # Can't go higher than medium for now
            else:
                confidence = base_confidence
            source = "mesa_simulation"
        else:
            confidence = "very_low" if base_confidence in ["low", "medium"] else base_confidence
            source = "heuristic_estimate"
        
        return {
            "metric": metric_name,
            "actual_value": float(actual) if not isinstance(actual_value, list) else actual_value,
            "target": target,
            "status": status.value,
            "message": message,
            "confidence": confidence,
            "source": source
        }
    
    def _is_lower_better(self, metric_name: str) -> bool:
        """Determine if lower values are better for a metric."""
        lower_better_metrics = [
            "clearance_p95_minutes", "clearance_p50_minutes", "decision_latency_minutes",
            "scg_established_minutes", "queue_len_p95", "platform_overcap_minutes",
            "self_evac_started_within_minutes"
        ]
        return any(pattern in metric_name for pattern in lower_better_metrics)
    
    def _get_metric_confidence(self, metric_name: str) -> str:
        """Get confidence level for a metric based on evidence quality."""
        # Queue and platform metrics are operational comfort bands
        if "queue_len" in metric_name or "platform_overcap" in metric_name:
            return "low"
        
        # Framework-derived metrics have higher confidence
        if any(pattern in metric_name for pattern in [
            "evacuees_total", "assisted_evacuees", "people_affected",
            "clearance_p95", "clearance_p50"
        ]):
            return "medium"
        
        # Decision timing from policy/exercises
        if "decision_latency" in metric_name or "scg_established" in metric_name:
            return "medium"
        
        return "medium"
    
    def _get_evidence_sources(self, golden_key: str) -> List[str]:
        """Get evidence sources for a golden scenario."""
        source_mapping = {
            "mass_flood_rwc": [
                "London Resilience Partnership - Mass Evacuation Framework v3.0 (June 2018)",
                "National Flood Resilience Review (2016) - UK Government (DEFRA/Cabinet Office)",
                "GLA flood risk assessments (2014)"
            ],
            "chemical_sudden": [
                "London Resilience Partnership - Mass Evacuation Framework v3.0 (June 2018)",
                "Exercise Unified Response (2016) - London Fire Brigade",
                "CBRN response protocols"
            ],
            "uxo_medium": [
                "London Resilience Partnership - Mass Evacuation Framework v3.0 (June 2018)",
                "Medium-scale evacuation case studies"
            ],
            "local_gas_small": [
                "London Resilience Partnership - Mass Evacuation Framework v3.0 (June 2018)",
                "Local emergency response protocols"
            ],
            "central_terror_large": [
                "London Resilience Partnership - Mass Evacuation Framework v3.0 (June 2018)",
                "7 July Review Committee Report (2006) - Greater London Authority",
                "Exercise Unified Response (2016) - London Fire Brigade"
            ]
        }
        return source_mapping.get(golden_key, ["London Resilience Partnership - Mass Evacuation Framework v3.0 (June 2018)"])
    
    def _get_timestamp(self) -> str:
        """Get current timestamp for evaluation."""
        from datetime import datetime
        return datetime.utcnow().isoformat()
    
    def create_evaluation_manifest(
        self,
        run_id: str,
        scenario_evaluations: List[Dict[str, Any]],
        run_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create an evaluation manifest for a complete run.
        
        Args:
            run_id: Simulation run ID
            scenario_evaluations: List of scenario evaluation results
            run_metadata: Optional run metadata
            
        Returns:
            Complete evaluation manifest
        """
        overall_status = EvalStatus.OK
        total_metrics = 0
        passed_metrics = 0
        amber_metrics = 0
        failed_metrics = 0
        
        for eval_result in scenario_evaluations:
            for metric_eval in eval_result["evaluations"].values():
                total_metrics += 1
                if metric_eval["status"] == EvalStatus.OK.value:
                    passed_metrics += 1
                elif metric_eval["status"] == EvalStatus.AMBER.value:
                    amber_metrics += 1
                    if overall_status == EvalStatus.OK:
                        overall_status = EvalStatus.AMBER
                elif metric_eval["status"] == EvalStatus.FAIL.value:
                    failed_metrics += 1
                    overall_status = EvalStatus.FAIL
        
        return {
            "run_id": run_id,
            "evaluation_timestamp": self._get_timestamp(),
            "goldens_version": self.goldens.get("version", 0),
            "overall_status": overall_status.value,
            "summary": {
                "total_metrics": total_metrics,
                "passed_metrics": passed_metrics,
                "amber_metrics": amber_metrics,
                "failed_metrics": failed_metrics,
                "pass_rate": passed_metrics / total_metrics if total_metrics > 0 else 0
            },
            "scenario_evaluations": scenario_evaluations,
            "run_metadata": run_metadata or {},
            "evidence_note": "Evaluation bands derived from UK Mass Evacuation Framework + historical exercises"
        }
