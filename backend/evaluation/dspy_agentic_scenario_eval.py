"""
DSPy Evaluation System for Agentic Scenario Creation

This self-contained script evaluates the quality of AI-generated evacuation scenarios
using DSPy optimization and a dataset derived from UK Mass Evacuation Framework templates.

FUTURE IMPLEMENTATION:
- Currently evaluates scenario generation quality
- Will be expanded to include:
  * Multi-metric optimization across all evaluation layers
  * Integration with statistical validation and network evaluation
  * Automated feedback loops for scenario improvement
  * Cross-validation with historical incidents (7/7, Grenfell, EUR 2016)
  * Sensitivity analysis for parameter robustness
  * Real-time evaluation during scenario generation

Dataset Generation:
- Derives from 6 framework-compliant templates in backend/scenarios/framework_templates.py
- Uses golden standards from research/evals_notes.md
- Incorporates Mass Evacuation Framework v3.0 (June 2018) criteria
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import dspy
    from dspy.evaluate import Evaluate
    from dspy.teleprompt import BootstrapFewShot
    DSPY_AVAILABLE = True
except ImportError:
    DSPY_AVAILABLE = False
    print("WARNING: DSPy not available. Install with: pip install dspy-ai")

try:
    import structlog
    logger = structlog.get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


# ============================================================================
# PART 1: DATASET GENERATION FROM FRAMEWORK SCENARIOS
# ============================================================================

class FrameworkScenarioDataset:
    """
    Generates evaluation dataset from UK Mass Evacuation Framework scenarios.
    
    Dataset includes:
    - 6 base framework scenarios (flood, chemical, UXO, gas, terrorist, rising tide)
    - Golden standards for each scenario type
    - Realistic parameter ranges
    - Expected metrics bounds
    """
    
    def __init__(self):
        self.golden_standards = self._load_golden_standards()
        self.framework_scenarios = self._load_framework_scenarios()
        self.dataset = self._generate_dataset()
    
    def _load_golden_standards(self) -> Dict[str, Any]:
        """Load golden standards from evaluation framework."""
        return {
            "mass_flood_rwc": {
                "description": "Reasonable worst-case fluvial flood affecting multiple boroughs",
                "expected_metrics": {
                    "evacuees_total": [130000, 170000],
                    "assisted_evacuees": [50000, 60000],
                    "clearance_p95_minutes": [360, 480],
                    "clearance_p50_minutes": [180, 300],
                    "assisted_completion_rate": [0.90, 1.0],
                    "decision_latency_minutes_max": 60,
                    "queue_len_p95_max": 200,
                    "platform_overcap_minutes_max": 120
                },
                "scenario_properties": {
                    "scale": "mass",
                    "hazard_type": "flood",
                    "warning_time": "rising_tide",
                    "governance": ["SCG", "ESCG", "LLACC"],
                    "phases": ["initiate", "alert", "move", "shelter", "return"]
                }
            },
            "chemical_sudden": {
                "description": "Large sudden-impact chemical release with immediate cordons",
                "expected_metrics": {
                    "people_affected": [40000, 80000],
                    "clearance_p95_minutes": [240, 420],
                    "decision_latency_minutes_max": 30,
                    "self_evac_started_within_minutes_max": 15,
                    "queue_len_p95_max": 200,
                    "platform_overcap_minutes_max": 90
                },
                "scenario_properties": {
                    "scale": "large",
                    "hazard_type": "chemical",
                    "warning_time": "sudden_impact",
                    "cbrn_protocols": True,
                    "decision_context": "police_strategic_pre_SCG"
                }
            },
            "uxo_medium": {
                "description": "Medium-scale planned UXO evacuation (rising-tide style)",
                "expected_metrics": {
                    "people_affected": [10000, 25000],
                    "clearance_p95_minutes": [180, 360],
                    "scg_established_minutes_max": 120,
                    "queue_len_p95_max": 150,
                    "platform_overcap_minutes_max": 60
                },
                "scenario_properties": {
                    "scale": "medium",
                    "hazard_type": "UXO",
                    "warning_time": "planned",
                    "governance": ["SCG", "ESCG", "LLACC"]
                }
            },
            "local_gas_small": {
                "description": "Small, borough-led local gas leak evacuation",
                "expected_metrics": {
                    "people_affected": [200, 1000],
                    "clearance_p95_minutes": [60, 180],
                    "queue_len_p95_max": 80,
                    "platform_overcap_minutes_max": 30
                },
                "scenario_properties": {
                    "scale": "small",
                    "hazard_type": "gas_leak",
                    "warning_time": "immediate",
                    "governance": ["local_control"],
                    "scg_required": False
                }
            },
            "central_terror_large": {
                "description": "Large sudden-impact, multi-site cordons in central area",
                "expected_metrics": {
                    "people_affected": [60000, 100000],
                    "clearance_p95_minutes": [300, 540],
                    "decision_latency_minutes_max": 30,
                    "responder_absenteeism_prop": [0.1, 0.2],
                    "queue_len_p95_max": 220,
                    "platform_overcap_minutes_max": 120
                },
                "scenario_properties": {
                    "scale": "large",
                    "hazard_type": "terrorist_event",
                    "warning_time": "sudden_impact",
                    "multi_site": True,
                    "decision_context": "police_strategic_pre_SCG"
                }
            }
        }
    
    def _load_framework_scenarios(self) -> Dict[str, Dict]:
        """Load framework scenario templates."""
        return {
            "mass_fluvial_flood_rwc": {
                "name": "Thames fluvial flood – pan-London RWC",
                "hazard_type": "flood",
                "subtype": "fluvial",
                "scale": "mass",
                "people_affected": 150000,
                "assisted_evacuation": 55000,
                "duration_minutes": 1440,
                "governance": {"SCG": True, "ESCG": True, "LLACC": True},
                "warning_time": "rising_tide",
                "compliance": 0.7,
                "modes": ["walk", "bus", "rail", "car", "river"]
            },
            "large_chemical_release": {
                "name": "Central London chemical release – sudden impact",
                "hazard_type": "chemical",
                "subtype": "toxic_release",
                "scale": "large",
                "people_affected": 60000,
                "assisted_evacuation": 18000,
                "duration_minutes": 480,
                "warning_time": "sudden_impact",
                "cbrn_required": True,
                "compliance": 0.6,
                "modes": ["walk", "bus", "rail", "car"]
            },
            "medium_uxo_planned": {
                "name": "Docklands UXO cordon – planned lift and evacuate",
                "hazard_type": "UXO",
                "subtype": "unexploded_ordnance",
                "scale": "medium",
                "people_affected": 18000,
                "duration_minutes": 360,
                "warning_time": "planned",
                "compliance": 0.85,
                "modes": ["walk", "bus", "rail"]
            },
            "small_gas_leak": {
                "name": "Local gas leak – Southwark high street",
                "hazard_type": "gas_leak",
                "subtype": "natural_gas",
                "scale": "small",
                "people_affected": 800,
                "duration_minutes": 180,
                "warning_time": "immediate",
                "governance": {"local_control": True},
                "compliance": 0.9,
                "modes": ["walk", "bus"]
            },
            "terrorist_sudden_impact": {
                "name": "Central sudden impact – multi-site cordons",
                "hazard_type": "terrorist_event",
                "subtype": "multi_site",
                "scale": "large",
                "people_affected": 80000,
                "duration_minutes": 720,
                "warning_time": "sudden_impact",
                "multi_site": True,
                "compliance": 0.55,
                "modes": ["walk", "bus", "rail", "car"]
            },
            "rising_tide_flood": {
                "name": "Rising-tide flood – Greenwich/Deptford reception",
                "hazard_type": "flood",
                "subtype": "rising_tide",
                "scale": "mass",
                "people_affected": 110000,
                "duration_minutes": 720,
                "warning_time": "rising_tide",
                "governance": {"SCG": True, "ESCG": True, "LLACC": True},
                "compliance": 0.75,
                "modes": ["walk", "bus", "rail", "river"]
            }
        }
    
    def _generate_dataset(self) -> List[Dict[str, Any]]:
        """
        Generate evaluation dataset with input-output pairs.
        
        Each example contains:
        - input: scenario intent/description
        - output: expected scenario properties
        - golden_metrics: expected performance bounds
        """
        dataset = []
        
        for scenario_key, scenario_data in self.framework_scenarios.items():
            # Match to golden standards
            golden_key = self._match_to_golden(scenario_key)
            golden = self.golden_standards.get(golden_key, {})
            
            # Create training example
            example = {
                "scenario_intent": scenario_data["name"],
                "hazard_type": scenario_data["hazard_type"],
                "expected_properties": {
                    "scale": scenario_data["scale"],
                    "people_affected_range": self._get_realistic_range(
                        scenario_data["people_affected"]
                    ),
                    "duration_minutes_range": self._get_time_range(
                        scenario_data["duration_minutes"]
                    ),
                    "warning_time": scenario_data["warning_time"],
                    "compliance_range": self._get_compliance_range(
                        scenario_data["compliance"]
                    ),
                    "modes_required": scenario_data["modes"]
                },
                "golden_metrics": golden.get("expected_metrics", {}),
                "framework_compliance": {
                    "governance_correct": scenario_data.get("governance", {}),
                    "phases_required": golden.get("scenario_properties", {}).get(
                        "phases", []
                    ),
                    "cbrn_protocols": scenario_data.get("cbrn_required", False)
                },
                "source": "framework_template",
                "template_name": scenario_key
            }
            
            dataset.append(example)
            
            # Add variations for robustness
            variations = self._generate_variations(example)
            dataset.extend(variations)
        
        return dataset
    
    def _match_to_golden(self, scenario_key: str) -> str:
        """Match scenario template to golden standard key."""
        mapping = {
            "mass_fluvial_flood_rwc": "mass_flood_rwc",
            "large_chemical_release": "chemical_sudden",
            "medium_uxo_planned": "uxo_medium",
            "small_gas_leak": "local_gas_small",
            "terrorist_sudden_impact": "central_terror_large",
            "rising_tide_flood": "mass_flood_rwc"  # Similar to mass flood
        }
        return mapping.get(scenario_key, scenario_key)
    
    def _get_realistic_range(self, value: int) -> List[int]:
        """Get realistic range for population."""
        return [int(value * 0.8), int(value * 1.2)]
    
    def _get_time_range(self, minutes: int) -> List[int]:
        """Get realistic time range."""
        return [int(minutes * 0.7), int(minutes * 1.3)]
    
    def _get_compliance_range(self, compliance: float) -> List[float]:
        """Get realistic compliance range."""
        return [max(0.5, compliance - 0.1), min(1.0, compliance + 0.1)]
    
    def _generate_variations(self, base_example: Dict) -> List[Dict]:
        """Generate variations of a scenario for robustness testing."""
        variations = []
        
        # Variation 1: Different severity
        if base_example["expected_properties"]["scale"] == "large":
            severe = base_example.copy()
            severe["scenario_intent"] = severe["scenario_intent"] + " (increased severity)"
            severe["expected_properties"]["people_affected_range"] = [
                int(x * 1.3) for x in severe["expected_properties"]["people_affected_range"]
            ]
            variations.append(severe)
        
        # Variation 2: Different compliance
        low_compliance = base_example.copy()
        low_compliance["scenario_intent"] = low_compliance["scenario_intent"] + " (low compliance)"
        low_compliance["expected_properties"]["compliance_range"] = [0.4, 0.6]
        variations.append(low_compliance)
        
        return variations
    
    def get_train_test_split(self, test_size: float = 0.2) -> Tuple[List, List]:
        """Split dataset into train and test sets."""
        np.random.seed(42)
        indices = np.random.permutation(len(self.dataset))
        split_idx = int(len(self.dataset) * (1 - test_size))
        
        train_indices = indices[:split_idx]
        test_indices = indices[split_idx:]
        
        train = [self.dataset[i] for i in train_indices]
        test = [self.dataset[i] for i in test_indices]
        
        return train, test
    
    def save_dataset(self, output_path: str):
        """Save dataset to JSON file."""
        output = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "source": "UK Mass Evacuation Framework v3.0 (June 2018)",
                "num_examples": len(self.dataset),
                "num_base_scenarios": len(self.framework_scenarios),
                "golden_standards_count": len(self.golden_standards)
            },
            "golden_standards": self.golden_standards,
            "framework_scenarios": self.framework_scenarios,
            "dataset": self.dataset
        }
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"Dataset saved to {output_path}")
        print(f"  - {len(self.dataset)} total examples")
        print(f"  - {len(self.framework_scenarios)} base scenarios")
        print(f"  - {len(self.golden_standards)} golden standards")


# ============================================================================
# PART 2: DSPY SIGNATURES FOR SCENARIO EVALUATION
# ============================================================================

if DSPY_AVAILABLE:
    class ScenarioQualityEvaluator(dspy.Signature):
        """Evaluate the quality and realism of a generated evacuation scenario."""
        
        scenario_intent = dspy.InputField(desc="Original intent for the scenario")
        generated_scenario = dspy.InputField(desc="AI-generated scenario specification (JSON)")
        framework_standards = dspy.InputField(desc="Relevant framework standards and golden metrics")
        
        is_realistic = dspy.OutputField(desc="Boolean: Is the scenario realistic? (True/False)")
        framework_compliant = dspy.OutputField(desc="Boolean: Does it follow framework guidelines? (True/False)")
        quality_score = dspy.OutputField(desc="Integer 1-10: Overall quality score")
        issues = dspy.OutputField(desc="List of specific issues or concerns (comma-separated)")
        recommendations = dspy.OutputField(desc="Suggested improvements (comma-separated)")
    
    
    class ScenarioParameterValidator(dspy.Signature):
        """Validate that scenario parameters are within realistic bounds."""
        
        scenario_properties = dspy.InputField(desc="Generated scenario properties (JSON)")
        expected_ranges = dspy.InputField(desc="Expected parameter ranges from golden standards")
        
        parameters_valid = dspy.OutputField(desc="Boolean: Are all parameters within realistic bounds?")
        out_of_bounds = dspy.OutputField(desc="List of parameters outside realistic bounds (comma-separated)")
        severity_assessment = dspy.OutputField(desc="Assessment of how severe the issues are (none/minor/major/critical)")


# ============================================================================
# PART 3: EVALUATION METRICS
# ============================================================================

class ScenarioEvaluationMetrics:
    """Metrics for evaluating scenario generation quality."""
    
    @staticmethod
    def evaluate_realism(generated: Dict, expected: Dict) -> float:
        """
        Evaluate how realistic the scenario is.
        
        Checks:
        - Population size within expected range
        - Duration appropriate for hazard type
        - Compliance rate realistic
        - Transport modes appropriate
        """
        score = 0.0
        max_score = 5.0
        
        # Check population range
        if "people_affected_range" in expected:
            gen_pop = generated.get("people_affected", 0)
            exp_range = expected["people_affected_range"]
            if exp_range[0] <= gen_pop <= exp_range[1]:
                score += 1.0
            elif exp_range[0] * 0.5 <= gen_pop <= exp_range[1] * 1.5:
                score += 0.5
        
        # Check duration
        if "duration_minutes_range" in expected:
            gen_dur = generated.get("duration_minutes", 0)
            exp_range = expected["duration_minutes_range"]
            if exp_range[0] <= gen_dur <= exp_range[1]:
                score += 1.0
            elif exp_range[0] * 0.5 <= gen_dur <= exp_range[1] * 1.5:
                score += 0.5
        
        # Check compliance
        if "compliance_range" in expected:
            gen_comp = generated.get("compliance", 0)
            exp_range = expected["compliance_range"]
            if exp_range[0] <= gen_comp <= exp_range[1]:
                score += 1.0
            elif 0.4 <= gen_comp <= 1.0:  # At least plausible
                score += 0.5
        
        # Check scale consistency
        gen_scale = generated.get("scale", "unknown")
        exp_scale = expected.get("scale", "unknown")
        if gen_scale == exp_scale:
            score += 1.0
        
        # Check hazard type consistency
        gen_hazard = generated.get("hazard_type", "unknown")
        exp_hazard = expected.get("hazard_type", "unknown")
        if gen_hazard == exp_hazard:
            score += 1.0
        
        return score / max_score
    
    @staticmethod
    def evaluate_framework_compliance(generated: Dict, framework_reqs: Dict) -> float:
        """
        Evaluate compliance with UK Mass Evacuation Framework.
        
        Checks:
        - Governance structures appropriate for scale
        - CBRN protocols if needed
        - Warning time classification correct
        - Phases included
        """
        score = 0.0
        max_score = 4.0
        
        # Check governance
        if "governance_correct" in framework_reqs:
            gen_gov = generated.get("governance", {})
            exp_gov = framework_reqs["governance_correct"]
            if isinstance(exp_gov, dict):
                # Check for required governance elements
                if exp_gov.get("SCG") and gen_gov.get("SCG"):
                    score += 0.5
                if exp_gov.get("ESCG") and gen_gov.get("ESCG"):
                    score += 0.5
                if exp_gov.get("local_control") and gen_gov.get("local_control"):
                    score += 0.5
            else:
                score += 0.5  # Basic governance present
        
        # Check CBRN protocols
        if "cbrn_protocols" in framework_reqs:
            gen_cbrn = generated.get("cbrn_required", False)
            exp_cbrn = framework_reqs["cbrn_protocols"]
            if gen_cbrn == exp_cbrn:
                score += 1.0
            elif not exp_cbrn:  # OK if not required and not included
                score += 1.0
        
        # Check warning time classification
        gen_warning = generated.get("warning_time", "unknown")
        exp_warning = framework_reqs.get("warning_time", "unknown")
        if gen_warning == exp_warning:
            score += 1.0
        elif gen_warning in ["sudden_impact", "immediate", "rising_tide", "planned"]:
            score += 0.5  # At least has a valid classification
        
        # Check phases (if specified)
        if "phases_required" in framework_reqs:
            gen_phases = generated.get("phases", [])
            exp_phases = framework_reqs["phases_required"]
            if isinstance(gen_phases, list) and isinstance(exp_phases, list):
                overlap = len(set(gen_phases) & set(exp_phases))
                if overlap >= len(exp_phases) * 0.8:  # 80% overlap
                    score += 1.0
                elif overlap > 0:
                    score += 0.5
        
        return score / max_score
    
    @staticmethod
    def evaluate_completeness(generated: Dict) -> float:
        """
        Evaluate completeness of scenario specification.
        
        Required fields:
        - name, hazard_type, scale, people_affected
        - duration_minutes, compliance
        - modes, warning_time
        """
        required_fields = [
            "name", "hazard_type", "scale", "people_affected",
            "duration_minutes", "compliance", "modes", "warning_time"
        ]
        
        present = sum(1 for field in required_fields if field in generated)
        return present / len(required_fields)
    
    @staticmethod
    def combined_metric(
        realism: float,
        compliance: float,
        completeness: float,
        weights: Tuple[float, float, float] = (0.4, 0.4, 0.2)
    ) -> float:
        """Combine metrics with weights."""
        return (
            realism * weights[0] +
            compliance * weights[1] +
            completeness * weights[2]
        )


# ============================================================================
# PART 4: DSPY EVALUATION PROGRAM
# ============================================================================

if DSPY_AVAILABLE:
    class AgenticScenarioEvaluator(dspy.Module):
        """DSPy module for evaluating agentic scenario generation."""
        
        def __init__(self):
            super().__init__()
            self.quality_eval = dspy.ChainOfThought(ScenarioQualityEvaluator)
            self.param_validator = dspy.ChainOfThought(ScenarioParameterValidator)
        
        def forward(self, scenario_intent: str, generated_scenario: str, framework_standards: str):
            """
            Evaluate a generated scenario.
            
            Args:
                scenario_intent: Original intent
                generated_scenario: Generated scenario (JSON string)
                framework_standards: Relevant standards (JSON string)
            
            Returns:
                Evaluation results
            """
            # Quality evaluation
            quality = self.quality_eval(
                scenario_intent=scenario_intent,
                generated_scenario=generated_scenario,
                framework_standards=framework_standards
            )
            
            # Parameter validation
            try:
                scenario_dict = json.loads(generated_scenario) if isinstance(generated_scenario, str) else generated_scenario
                standards_dict = json.loads(framework_standards) if isinstance(framework_standards, str) else framework_standards
                
                validation = self.param_validator(
                    scenario_properties=json.dumps(scenario_dict.get("expected_properties", {})),
                    expected_ranges=json.dumps(standards_dict.get("golden_metrics", {}))
                )
            except:
                validation = None
            
            return {
                "quality": quality,
                "validation": validation,
                "is_realistic": quality.is_realistic,
                "framework_compliant": quality.framework_compliant,
                "quality_score": quality.quality_score,
                "issues": quality.issues,
                "recommendations": quality.recommendations
            }


# ============================================================================
# PART 5: EVALUATION PIPELINE
# ============================================================================

class DSPyScenarioEvaluationPipeline:
    """Complete evaluation pipeline for agentic scenario generation."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "openai/gpt-4o-mini"):
        """
        Initialize evaluation pipeline.
        
        Args:
            api_key: API key for LLM (OpenAI or Anthropic)
            model: Model to use (default: gpt-4o-mini)
        """
        self.dataset_generator = FrameworkScenarioDataset()
        self.metrics = ScenarioEvaluationMetrics()
        
        if DSPY_AVAILABLE and api_key:
            # Configure DSPy
            lm = dspy.LM(model=model, api_key=api_key, max_tokens=2000)
            dspy.configure(lm=lm)
            self.evaluator = AgenticScenarioEvaluator()
            self.dspy_enabled = True
            print(f"DSPy evaluation enabled with {model}")
        else:
            self.evaluator = None
            self.dspy_enabled = False
            print("DSPy evaluation disabled (no API key or DSPy not installed)")
    
    def generate_and_save_dataset(self, output_path: str = "backend/evaluation/scenario_eval_dataset.json"):
        """Generate and save the evaluation dataset."""
        print("\n" + "=" * 80)
        print("GENERATING EVALUATION DATASET FROM FRAMEWORK SCENARIOS")
        print("=" * 80)
        
        self.dataset_generator.save_dataset(output_path)
        
        # Print summary
        print("\nDataset Summary:")
        print(f"  Base Scenarios: {len(self.dataset_generator.framework_scenarios)}")
        for name, scenario in self.dataset_generator.framework_scenarios.items():
            print(f"    - {scenario['name']}")
            print(f"      Scale: {scenario['scale']}, Hazard: {scenario['hazard_type']}")
            print(f"      People: {scenario['people_affected']:,}, Duration: {scenario['duration_minutes']} min")
        
        print(f"\n  Total Examples (with variations): {len(self.dataset_generator.dataset)}")
        print(f"  Golden Standards: {len(self.dataset_generator.golden_standards)}")
        
        return output_path
    
    def evaluate_scenario(self, example: Dict) -> Dict[str, Any]:
        """
        Evaluate a single scenario example.
        
        Args:
            example: Dataset example with scenario_intent, expected_properties, etc.
        
        Returns:
            Evaluation results with scores and metrics
        """
        # Generate a mock scenario for evaluation (in real use, this would be from LLM)
        generated_scenario = {
            "name": example["scenario_intent"],
            "hazard_type": example["hazard_type"],
            "scale": example["expected_properties"]["scale"],
            "people_affected": np.mean(example["expected_properties"]["people_affected_range"]),
            "duration_minutes": np.mean(example["expected_properties"]["duration_minutes_range"]),
            "compliance": np.mean(example["expected_properties"]["compliance_range"]),
            "modes": example["expected_properties"]["modes_required"],
            "warning_time": example["expected_properties"]["warning_time"],
            "governance": example["framework_compliance"]["governance_correct"]
        }
        
        # Calculate metrics
        realism_score = self.metrics.evaluate_realism(
            generated_scenario,
            example["expected_properties"]
        )
        
        compliance_score = self.metrics.evaluate_framework_compliance(
            generated_scenario,
            example["framework_compliance"]
        )
        
        completeness_score = self.metrics.evaluate_completeness(generated_scenario)
        
        combined_score = self.metrics.combined_metric(
            realism_score,
            compliance_score,
            completeness_score
        )
        
        result = {
            "scenario_intent": example["scenario_intent"],
            "scores": {
                "realism": round(realism_score, 3),
                "framework_compliance": round(compliance_score, 3),
                "completeness": round(completeness_score, 3),
                "combined": round(combined_score, 3)
            },
            "generated_scenario": generated_scenario,
            "expected_properties": example["expected_properties"]
        }
        
        # Add DSPy evaluation if available
        if self.dspy_enabled and self.evaluator:
            try:
                dspy_result = self.evaluator(
                    scenario_intent=example["scenario_intent"],
                    generated_scenario=json.dumps(generated_scenario, indent=2),
                    framework_standards=json.dumps({
                        "expected_properties": example["expected_properties"],
                        "golden_metrics": example["golden_metrics"],
                        "framework_compliance": example["framework_compliance"]
                    }, indent=2)
                )
                
                result["dspy_evaluation"] = {
                    "is_realistic": dspy_result.get("is_realistic"),
                    "framework_compliant": dspy_result.get("framework_compliant"),
                    "quality_score": dspy_result.get("quality_score"),
                    "issues": dspy_result.get("issues"),
                    "recommendations": dspy_result.get("recommendations")
                }
            except Exception as e:
                logger.warning(f"DSPy evaluation failed: {e}")
                result["dspy_evaluation"] = {"error": str(e)}
        
        return result
    
    def run_evaluation(self, num_examples: int = None) -> Dict[str, Any]:
        """
        Run evaluation on dataset examples.
        
        Args:
            num_examples: Number of examples to evaluate (None = all)
        
        Returns:
            Evaluation results summary
        """
        print("\n" + "=" * 80)
        print("RUNNING SCENARIO EVALUATION")
        print("=" * 80)
        
        dataset = self.dataset_generator.dataset
        if num_examples:
            dataset = dataset[:num_examples]
        
        results = []
        for i, example in enumerate(dataset):
            print(f"\nEvaluating {i+1}/{len(dataset)}: {example['scenario_intent']}")
            result = self.evaluate_scenario(example)
            results.append(result)
            
            # Print summary
            print(f"  Realism: {result['scores']['realism']:.2f}")
            print(f"  Framework Compliance: {result['scores']['framework_compliance']:.2f}")
            print(f"  Completeness: {result['scores']['completeness']:.2f}")
            print(f"  Combined Score: {result['scores']['combined']:.2f}")
        
        # Calculate aggregate statistics
        all_scores = {
            "realism": [r["scores"]["realism"] for r in results],
            "framework_compliance": [r["scores"]["framework_compliance"] for r in results],
            "completeness": [r["scores"]["completeness"] for r in results],
            "combined": [r["scores"]["combined"] for r in results]
        }
        
        summary = {
            "num_evaluated": len(results),
            "aggregate_scores": {
                metric: {
                    "mean": round(np.mean(scores), 3),
                    "std": round(np.std(scores), 3),
                    "min": round(np.min(scores), 3),
                    "max": round(np.max(scores), 3)
                }
                for metric, scores in all_scores.items()
            },
            "pass_rate": {
                metric: round(sum(1 for s in scores if s >= 0.7) / len(scores), 3)
                for metric, scores in all_scores.items()
            },
            "detailed_results": results
        }
        
        print("\n" + "=" * 80)
        print("EVALUATION SUMMARY")
        print("=" * 80)
        print(f"\nEvaluated {summary['num_evaluated']} scenarios")
        print("\nAggregate Scores (mean ± std):")
        for metric, stats in summary["aggregate_scores"].items():
            print(f"  {metric.replace('_', ' ').title()}: {stats['mean']:.3f} ± {stats['std']:.3f}")
        
        print("\nPass Rates (score >= 0.7):")
        for metric, rate in summary["pass_rate"].items():
            print(f"  {metric.replace('_', ' ').title()}: {rate:.1%}")
        
        return summary
    
    def save_evaluation_results(self, results: Dict, output_path: str):
        """Save evaluation results to JSON file."""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {output_path}")


# ============================================================================
# PART 6: MAIN EXECUTION
# ============================================================================

def main():
    """Main execution function."""
    print("\n" + "=" * 80)
    print("DSPy AGENTIC SCENARIO EVALUATION SYSTEM")
    print("=" * 80)
    print("\nThis system evaluates AI-generated evacuation scenarios against")
    print("UK Mass Evacuation Framework standards and golden metrics.")
    print("\nFUTURE ENHANCEMENTS:")
    print("  - Integration with multi-layer evaluation framework")
    print("  - Statistical validation and network evaluation")
    print("  - Cross-validation with historical incidents (7/7, Grenfell, EUR)")
    print("  - Automated feedback loops for scenario improvement")
    print("  - Real-time evaluation during scenario generation")
    
    # Get API key from environment
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    model = "openai/gpt-4o-mini" if os.getenv("OPENAI_API_KEY") else "anthropic/claude-3-5-sonnet-20241022"
    
    # Initialize pipeline
    pipeline = DSPyScenarioEvaluationPipeline(api_key=api_key, model=model)
    
    # Generate and save dataset
    dataset_path = pipeline.generate_and_save_dataset()
    
    # Run evaluation on a subset
    print("\n" + "=" * 80)
    print("Running evaluation on sample scenarios...")
    print("=" * 80)
    
    results = pipeline.run_evaluation(num_examples=6)  # Evaluate base scenarios
    
    # Save results
    results_path = "backend/evaluation/scenario_eval_results.json"
    pipeline.save_evaluation_results(results, results_path)
    
    print("\n" + "=" * 80)
    print("EVALUATION COMPLETE")
    print("=" * 80)
    print(f"\nDataset: {dataset_path}")
    print(f"Results: {results_path}")
    print("\nTo use this evaluation system:")
    print("  1. Import the DSPyScenarioEvaluationPipeline class")
    print("  2. Initialize with your API key")
    print("  3. Call evaluate_scenario() with generated scenarios")
    print("  4. Use the metrics for optimization and feedback")
    
    print("\nFuture integration points:")
    print("  - backend/agents/agentic_builders.py (scenario generation)")
    print("  - backend/evaluation/evaluator.py (framework compliance)")
    print("  - backend/evaluation/network_evaluator.py (network validation)")
    print("  - backend/evaluation/statistical_validator.py (statistical checks)")


if __name__ == "__main__":
    main()
