"""
Agentic Builders for Metrics and Scenarios

LLM-powered builders that allow AI agents to create custom metrics and scenarios
for evacuation simulations using DSPy patterns and context engineering.

REFACTORED: Now uses stateless services with dependency injection.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import structlog
import threading

try:
    import dspy
    DSPY_AVAILABLE = True
except ImportError:
    DSPY_AVAILABLE = False
    dspy = None

from core.config import get_settings
from services.metrics.metrics_service import MetricsService
from services.scenarios.scenario_service import ScenarioService
from scenarios.framework_templates import FrameworkScenarioTemplates
from scenarios.framework_converter import FrameworkScenarioConverter
from services.llm_service import get_llm_service

logger = structlog.get_logger(__name__)

# Global lock for DSPy configuration (thread-safe)
_dspy_config_lock = threading.Lock()
_dspy_configured = False


# DSPy Signatures for Agentic Builders
class GenerateMetricsSpec(dspy.Signature):
    """Generate a metrics specification for evacuation analysis."""
    
    analysis_goal = dspy.InputField(desc="What the user wants to analyze (e.g., 'evacuation efficiency', 'bottleneck analysis', 'safety metrics')")
    available_data = dspy.InputField(desc="Available data sources and metrics keys (timeseries: clearance_pct, queue_len, density; events: various types)")
    context = dspy.InputField(desc="Additional context about the simulation or requirements")
    
    metrics_specification = dspy.OutputField(desc="Complete YAML metrics specification with multiple relevant metrics")
    reasoning = dspy.OutputField(desc="Explanation of why these metrics were chosen and how they address the analysis goal")


class GenerateScenarioSpec(dspy.Signature):
    """Generate an evacuation scenario specification."""
    
    scenario_intent = dspy.InputField(desc="Intent for the scenario (e.g., 'test flood response', 'analyze terrorist threat evacuation', 'compare different hazard types')")
    city_context = dspy.InputField(desc="City and geographical context")
    constraints = dspy.InputField(desc="Any constraints or requirements (population size, duration, severity levels, etc.)")
    
    scenario_specification = dspy.OutputField(desc="Complete scenario specification with hazard type, parameters, affected areas, and realistic constraints")
    variants_suggestion = dspy.OutputField(desc="Suggested parameter variations for comparison studies")
    reasoning = dspy.OutputField(desc="Explanation of scenario design choices and expected outcomes")


class OptimizeMetricsForScenario(dspy.Signature):
    """Optimize metrics selection for a specific scenario type."""
    
    scenario_details = dspy.InputField(desc="Scenario specification including hazard type, affected areas, and parameters")
    analysis_objectives = dspy.InputField(desc="What aspects of the scenario should be measured and analyzed")
    
    optimized_metrics = dspy.OutputField(desc="Metrics specification optimized for this specific scenario type")
    key_insights = dspy.OutputField(desc="Key insights these metrics will reveal about the scenario")


class SelectFrameworkScenario(dspy.Signature):
    """Select and customize a framework-compliant scenario template."""
    
    scenario_intent = dspy.InputField(desc="User's intent for the scenario")
    available_templates = dspy.InputField(desc="Available framework scenario templates with descriptions")
    constraints = dspy.InputField(desc="Any specific constraints or requirements")
    
    selected_template = dspy.OutputField(desc="Best matching framework template name")
    customizations = dspy.OutputField(desc="JSON of parameter customizations to apply to the template")
    reasoning = dspy.OutputField(desc="Why this template was selected and what customizations were made")


class AgenticMetricsBuilder:
    """LLM-powered metrics builder that generates custom metrics specifications."""

    def __init__(
        self,
        data_path: Optional[str] = None,
        metrics_service: Optional[MetricsService] = None
    ):
        """
        Initialize with dependency injection.

        Args:
            data_path: Optional data path for metrics
            metrics_service: Optional MetricsService instance
        """
        self.settings = get_settings()
        self.data_path = data_path
        self.metrics_service = metrics_service or MetricsService()
        self.llm_generator = None
        self.llm_optimizer = None
        self._initialize_dspy()
    
    def _initialize_dspy(self):
        """Initialize DSPy with LLM configuration."""
        if not DSPY_AVAILABLE:
            logger.warning("DSPy not available, using mock generators")
            return
            
        try:
            # Try OpenAI first, fall back to Anthropic
            if self.settings.OPENAI_API_KEY:
                logger.info("Initializing Agentic Metrics Builder with OpenAI")
                lm = dspy.LM(
                    model='openai/gpt-4o-mini',
                    api_key=self.settings.OPENAI_API_KEY,
                    max_tokens=3000
                )
                logger.info("Successfully initialized DSPy for metrics builder")
            elif self.settings.ANTHROPIC_API_KEY:
                logger.info("Initializing Agentic Metrics Builder with Anthropic Claude")
                lm = dspy.LM(
                    model='anthropic/claude-3-5-sonnet-20241022',
                    api_key=self.settings.ANTHROPIC_API_KEY,
                    max_tokens=3000
                )
                logger.info("Successfully initialized DSPy for metrics builder")
            else:
                logger.warning("No LLM API key found, using mock generators")
                return

            dspy.configure(lm=lm)
            self.llm_generator = dspy.ChainOfThought(GenerateMetricsSpec)
            self.llm_optimizer = dspy.ChainOfThought(OptimizeMetricsForScenario)
            logger.info("Agentic metrics builder ready")

        except Exception as e:
            logger.error(f"Failed to initialize DSPy for metrics builder: {e}", exc_info=True)
            self.llm_generator = None
            self.llm_optimizer = None
    
    async def generate_metrics_for_goal(
        self,
        analysis_goal: str,
        run_id: Optional[str] = None,
        context: str = ""
    ) -> Dict[str, Any]:
        """
        Generate metrics specification based on analysis goal.
        
        Args:
            analysis_goal: What the user wants to analyze
            run_id: Optional run ID to get available data info
            context: Additional context
            
        Returns:
            Generated metrics specification and metadata
        """
        logger.info("Generating metrics for goal", goal=analysis_goal, run_id=run_id)
        
        # Get available data information
        available_data = self._get_available_data_description(run_id)
        
        if self.llm_generator:
            try:
                # Use LLM to generate metrics
                result = self.llm_generator(
                    analysis_goal=analysis_goal,
                    available_data=available_data,
                    context=context
                )
                
                # Parse the generated YAML specification
                metrics_spec = self._parse_metrics_specification(result.metrics_specification)
                
                return {
                    "specification": metrics_spec,
                    "reasoning": result.reasoning,
                    "generated_by": "llm",
                    "analysis_goal": analysis_goal,
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error(f"LLM metrics generation failed: {e}")
                # Fall back to template-based generation
                return self._generate_template_metrics(analysis_goal, context)
        else:
            # Use template-based generation
            return self._generate_template_metrics(analysis_goal, context)
    
    async def optimize_metrics_for_scenario(
        self,
        scenario_spec: Dict[str, Any],
        analysis_objectives: str
    ) -> Dict[str, Any]:
        """
        Optimize metrics selection for a specific scenario.
        
        Args:
            scenario_spec: Scenario specification
            analysis_objectives: What to measure
            
        Returns:
            Optimized metrics specification
        """
        if self.llm_optimizer:
            try:
                result = self.llm_optimizer(
                    scenario_details=json.dumps(scenario_spec, indent=2),
                    analysis_objectives=analysis_objectives
                )
                
                metrics_spec = self._parse_metrics_specification(result.optimized_metrics)
                
                return {
                    "specification": metrics_spec,
                    "key_insights": result.key_insights,
                    "optimized_for": scenario_spec.get("name", "scenario"),
                    "generated_by": "llm_optimizer",
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error(f"LLM metrics optimization failed: {e}")
                return self._generate_default_scenario_metrics(scenario_spec)
        else:
            return self._generate_default_scenario_metrics(scenario_spec)
    
    def _get_available_data_description(self, run_id: Optional[str] = None) -> str:
        """Get description of available data for context."""
        if run_id:
            try:
                info = self.metrics_service.get_available_metrics(
                    run_id=run_id,
                    data_path=self.data_path
                )
                return f"""
Available data for run {run_id}:
- Timeseries: {info['timeseries']['row_count']} records, metrics: {info['timeseries']['metric_keys']}
- Events: {info['events']['row_count']} records, types: {info['events']['event_types']}
- Scopes: {info['timeseries']['scopes']}
- Time range: {info['timeseries']['time_range']['min']}-{info['timeseries']['time_range']['max']} seconds
"""
            except Exception:
                pass
        
        return """
Standard evacuation simulation data:
- Timeseries metrics: clearance_pct (evacuation completion %), queue_len (congestion), density (people/m²)
- Event types: simulation_start, emergency_alert, route_closure, capacity_warning, route_reopened, simulation_end
- Scopes: city (overall), edge:* (road segments), node:station_* (transport stations)
- Typical duration: 30-60 minutes (1800-3600 seconds)
"""
    
    def _parse_metrics_specification(self, spec_text: str) -> Dict[str, Any]:
        """Parse LLM-generated metrics specification."""
        try:
            # Try to extract YAML from the response
            import yaml
            
            # Look for YAML code blocks
            if "```yaml" in spec_text:
                yaml_start = spec_text.find("```yaml") + 7
                yaml_end = spec_text.find("```", yaml_start)
                yaml_content = spec_text[yaml_start:yaml_end].strip()
            elif "```" in spec_text:
                yaml_start = spec_text.find("```") + 3
                yaml_end = spec_text.find("```", yaml_start)
                yaml_content = spec_text[yaml_start:yaml_end].strip()
            else:
                yaml_content = spec_text
            
            parsed = yaml.safe_load(yaml_content)
            
            # Ensure it's a dictionary with metrics
            if isinstance(parsed, dict):
                return parsed
            else:
                logger.warning(f"Parsed YAML is not a dict: {type(parsed)}")
                return self._get_basic_metrics_spec()
            
        except Exception as e:
            logger.error(f"Failed to parse metrics specification: {e}")
            logger.debug(f"Spec text was: {spec_text[:200]}...")
            # Return a basic specification
            return self._get_basic_metrics_spec()
    
    def _generate_template_metrics(self, analysis_goal: str, context: str) -> Dict[str, Any]:
        """Generate metrics using templates when LLM is not available."""
        goal_lower = analysis_goal.lower()
        
        if "efficiency" in goal_lower or "performance" in goal_lower:
            spec = {
                "metrics": {
                    "clearance_p50": {
                        "source": "timeseries",
                        "metric_key": "clearance_pct",
                        "operation": "percentile_time_to_threshold",
                        "args": {"threshold_pct": 50},
                        "post_process": {"divide_by": 60, "round_to": 1}
                    },
                    "clearance_p95": {
                        "source": "timeseries",
                        "metric_key": "clearance_pct",
                        "operation": "percentile_time_to_threshold",
                        "args": {"threshold_pct": 95},
                        "post_process": {"divide_by": 60, "round_to": 1}
                    },
                    "avg_evacuation_rate": {
                        "source": "timeseries",
                        "metric_key": "clearance_pct",
                        "operation": "area_under_curve",
                        "post_process": {"divide_by": 60}
                    }
                }
            }
        elif "bottleneck" in goal_lower or "congestion" in goal_lower:
            spec = {
                "metrics": {
                    "max_queue_by_edge": {
                        "source": "timeseries",
                        "metric_key": "queue_len",
                        "operation": "max_value",
                        "group_by": "scope",
                        "filters": {"scope_contains": "edge:"}
                    },
                    "avg_queue_length": {
                        "source": "timeseries",
                        "metric_key": "queue_len",
                        "operation": "mean_value",
                        "filters": {"scope_contains": "edge:"}
                    },
                    "congestion_duration": {
                        "source": "timeseries",
                        "metric_key": "queue_len",
                        "operation": "time_above_threshold",
                        "args": {"threshold": 20},
                        "post_process": {"divide_by": 60}
                    }
                }
            }
        elif "safety" in goal_lower or "density" in goal_lower:
            spec = {
                "metrics": {
                    "max_platform_density": {
                        "source": "timeseries",
                        "metric_key": "density",
                        "operation": "max_value",
                        "filters": {"scope_contains": "station"}
                    },
                    "overcrowding_time": {
                        "source": "timeseries",
                        "metric_key": "density",
                        "operation": "time_above_threshold",
                        "args": {"threshold": 4.0},
                        "post_process": {"divide_by": 60}
                    },
                    "safety_events": {
                        "source": "events",
                        "operation": "count_events",
                        "filters": {"type": "capacity_warning"}
                    }
                }
            }
        else:
            spec = self._get_basic_metrics_spec()
        
        return {
            "specification": spec,
            "reasoning": f"Template-based metrics for {analysis_goal}",
            "generated_by": "template",
            "analysis_goal": analysis_goal,
            "timestamp": datetime.now().isoformat()
        }
    
    def _get_basic_metrics_spec(self) -> Dict[str, Any]:
        """Get basic metrics specification."""
        return {
            "metrics": {
                "clearance_p95": {
                    "source": "timeseries",
                    "metric_key": "clearance_pct",
                    "operation": "percentile_time_to_threshold",
                    "args": {"threshold_pct": 95},
                    "post_process": {"divide_by": 60, "round_to": 1}
                },
                "max_queue": {
                    "source": "timeseries",
                    "metric_key": "queue_len",
                    "operation": "max_value"
                },
                "total_events": {
                    "source": "events",
                    "operation": "count_events"
                }
            }
        }
    
    def _generate_default_scenario_metrics(self, scenario_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Generate default metrics for a scenario."""
        hazard_type = scenario_spec.get("hazard_type", "general")
        
        if hazard_type == "flood":
            spec = {
                "metrics": {
                    "flood_clearance_time": {
                        "source": "timeseries",
                        "metric_key": "clearance_pct",
                        "operation": "percentile_time_to_threshold",
                        "args": {"threshold_pct": 90},
                        "post_process": {"divide_by": 60}
                    },
                    "water_affected_routes": {
                        "source": "events",
                        "operation": "count_events",
                        "filters": {"type": "route_closure"}
                    }
                }
            }
        elif hazard_type == "fire":
            spec = {
                "metrics": {
                    "fire_evacuation_speed": {
                        "source": "timeseries",
                        "metric_key": "clearance_pct",
                        "operation": "percentile_time_to_threshold",
                        "args": {"threshold_pct": 95},
                        "post_process": {"divide_by": 60}
                    },
                    "smoke_affected_density": {
                        "source": "timeseries",
                        "metric_key": "density",
                        "operation": "max_value",
                        "filters": {"scope_contains": "station"}
                    }
                }
            }
        else:
            spec = self._get_basic_metrics_spec()
        
        return {
            "specification": spec,
            "key_insights": f"Default metrics for {hazard_type} scenarios",
            "optimized_for": scenario_spec.get("name", "scenario"),
            "generated_by": "template",
            "timestamp": datetime.now().isoformat()
        }


class AgenticScenarioBuilder:
    """LLM-powered scenario builder that generates custom evacuation scenarios."""

    def __init__(
        self,
        scenarios_path: Optional[str] = None,
        scenario_service: Optional[ScenarioService] = None
    ):
        """
        Initialize with dependency injection.

        Args:
            scenarios_path: Optional scenarios path
            scenario_service: Optional ScenarioService instance
        """
        self.settings = get_settings()
        self.scenarios_path = scenarios_path
        self.scenario_service = scenario_service or ScenarioService()
        self.framework_templates = FrameworkScenarioTemplates.get_templates()
        self.llm_generator = None
        self.llm_selector = None
        self._initialize_dspy()
    
    def _initialize_dspy(self):
        """Initialize DSPy with LLM configuration (thread-safe)."""
        global _dspy_configured
        
        if not DSPY_AVAILABLE:
            logger.warning("DSPy not available for scenario builder, using mock generators")
            return
            
        try:
            # Use lock to ensure only one thread configures DSPy
            with _dspy_config_lock:
                if not _dspy_configured:
                    # Try OpenAI first, fall back to Anthropic
                    if self.settings.OPENAI_API_KEY:
                        logger.info("Initializing Agentic Scenario Builder with OpenAI (first time)")
                        lm = dspy.LM(
                            model='openai/gpt-4o-mini',
                            api_key=self.settings.OPENAI_API_KEY,
                            max_tokens=3000
                        )
                        dspy.configure(lm=lm)
                        _dspy_configured = True
                        logger.info("Successfully initialized DSPy globally")
                    elif self.settings.ANTHROPIC_API_KEY:
                        logger.info("Initializing Agentic Scenario Builder with Anthropic Claude (first time)")
                        lm = dspy.LM(
                            model='anthropic/claude-3-5-sonnet-20241022',
                            api_key=self.settings.ANTHROPIC_API_KEY,
                            max_tokens=3000
                        )
                        dspy.configure(lm=lm)
                        _dspy_configured = True
                        logger.info("Successfully initialized DSPy globally")
                    else:
                        logger.warning("No LLM API key found for scenario builder, using mock generators")
                        return
                else:
                    logger.info("DSPy already configured, reusing existing configuration")
            
            # Create modules after configuration is set
            self.llm_generator = dspy.ChainOfThought(GenerateScenarioSpec)
            self.llm_selector = dspy.ChainOfThought(SelectFrameworkScenario)
            logger.info("Agentic scenario builder ready")

        except Exception as e:
            logger.error(f"Failed to initialize DSPy for scenario builder: {e}", exc_info=True)
            self.llm_generator = None
            self.llm_selector = None
    
    
    async def generate_scenario_from_intent(
        self,
        scenario_intent: str,
        city_context: str = "London",
        constraints: str = ""
    ) -> Dict[str, Any]:
        """
        Generate scenario specification from natural language intent.
        
        Args:
            scenario_intent: Natural language description of desired scenario
            city_context: City and geographical context
            constraints: Any constraints or requirements
            
        Returns:
            Generated scenario specification and metadata
        """
        logger.info("Generating scenario from intent", intent=scenario_intent, city=city_context)
        
        if self.llm_generator:
            try:
                # Use LLM to generate scenario
                result = self.llm_generator(
                    scenario_intent=scenario_intent,
                    city_context=city_context,
                    constraints=constraints
                )
                
                # Parse the generated specification
                scenario_spec = self._parse_scenario_specification(result.scenario_specification)
                variants = self._parse_variants_suggestion(result.variants_suggestion)
                
                return {
                    "specification": scenario_spec,
                    "variants_suggestion": variants,
                    "reasoning": result.reasoning,
                    "generated_by": "llm",
                    "intent": scenario_intent,
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error(f"LLM scenario generation failed: {e}")
                # Fall back to template-based generation
                return self._generate_template_scenario(scenario_intent, city_context, constraints)
        else:
            # Use template-based generation
            return self._generate_template_scenario(scenario_intent, city_context, constraints)
    
    async def generate_framework_scenario(
        self,
        scenario_intent: str,
        city_context: str = "London",
        constraints: str = "",
        prefer_framework: bool = True
    ) -> Dict[str, Any]:
        """
        Generate a scenario using framework-compliant templates.
        
        Args:
            scenario_intent: Intent for the scenario
            city_context: City context
            constraints: Any constraints
            prefer_framework: Whether to prefer framework templates
            
        Returns:
            Framework-compliant scenario specification
        """
        logger.info("Generating framework scenario", intent=scenario_intent, city=city_context)
        
        if self.llm_selector and prefer_framework:
            try:
                # Get template descriptions for LLM
                template_descriptions = self._get_template_descriptions()
                
                result = self.llm_selector(
                    scenario_intent=scenario_intent,
                    available_templates=template_descriptions,
                    constraints=f"City: {city_context}. {constraints}"
                )
                
                selected_template = result.selected_template.strip()
                
                # Parse customizations
                try:
                    customizations = json.loads(result.customizations) if result.customizations else {}
                except json.JSONDecodeError:
                    logger.warning("Failed to parse LLM customizations, using defaults")
                    customizations = {}
                
                # Create framework scenario using service
                if selected_template in self.framework_templates:
                    scenario = self.scenario_service.create_framework_scenario(
                        template_name=selected_template,
                        custom_params=customizations,
                        scenarios_path=self.scenarios_path
                    )
                    
                    return {
                        "specification": scenario,
                        "template_used": selected_template,
                        "customizations": customizations,
                        "reasoning": result.reasoning,
                        "generated_by": "llm_framework_selector",
                        "framework_compliant": True,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    logger.warning(f"LLM selected unknown template: {selected_template}")
                    return self._generate_fallback_framework_scenario(scenario_intent, city_context)
                
            except Exception as e:
                logger.error(f"LLM framework selection failed: {e}")
                return self._generate_fallback_framework_scenario(scenario_intent, city_context)
        
        else:
            # Use rule-based framework selection
            return self._generate_fallback_framework_scenario(scenario_intent, city_context)
    
    def _get_template_descriptions(self) -> str:
        """Get formatted descriptions of framework templates for LLM."""
        descriptions = []
        
        for template_name, template_data in self.framework_templates.items():
            scale = template_data.get("scale", {}).get("category", "unknown")
            hazard = template_data.get("hazard", {}).get("type", "unknown")
            people = template_data.get("scale", {}).get("people_affected_est", "unknown")
            
            desc = f"- {template_name}: {template_data['name']}\n"
            desc += f"  Scale: {scale.upper()}, Hazard: {hazard}, People: {people:,}\n"
            desc += f"  Description: {template_data['description']}\n"
            
            descriptions.append(desc)
        
        return "\n".join(descriptions)
    
    def _generate_fallback_framework_scenario(
        self, 
        scenario_intent: str, 
        city_context: str
    ) -> Dict[str, Any]:
        """Generate framework scenario using rule-based selection."""
        
        # Simple keyword matching for template selection
        intent_lower = scenario_intent.lower()
        
        if any(word in intent_lower for word in ["flood", "water", "river", "thames"]):
            if "mass" in intent_lower or "major" in intent_lower:
                template_name = "mass_fluvial_flood_rwc"
            else:
                template_name = "rising_tide_flood"
        elif any(word in intent_lower for word in ["chemical", "toxic", "cbrn"]):
            template_name = "large_chemical_release"
        elif any(word in intent_lower for word in ["terror", "attack", "bomb", "sudden"]):
            template_name = "terrorist_sudden_impact"
        elif any(word in intent_lower for word in ["uxo", "ordnance", "bomb", "planned"]):
            template_name = "medium_uxo_planned"
        elif any(word in intent_lower for word in ["gas", "leak", "small", "local"]):
            template_name = "small_gas_leak"
        else:
            # Default to medium UXO for general scenarios
            template_name = "medium_uxo_planned"
        
        try:
            scenario = self.scenario_service.create_framework_scenario(
                template_name=template_name,
                scenarios_path=self.scenarios_path
            )
            
            return {
                "specification": scenario,
                "template_used": template_name,
                "customizations": {},
                "reasoning": f"Selected {template_name} based on keywords in intent: {scenario_intent}",
                "generated_by": "rule_based_framework_selector",
                "framework_compliant": True,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Framework scenario generation failed: {e}")
            # Fall back to basic scenario generation
            return self._generate_template_scenario(scenario_intent, city_context, "")
    
    async def generate_comparison_study(
        self,
        study_intent: str,
        base_scenario_intent: str,
        city_context: str = "London"
    ) -> Dict[str, Any]:
        """
        Generate a comparison study with multiple scenario variants.
        
        Args:
            study_intent: Intent for the comparison study
            base_scenario_intent: Base scenario to vary
            city_context: City context
            
        Returns:
            Complete study with multiple scenarios
        """
        # Generate base scenario
        base_result = await self.generate_scenario_from_intent(
            base_scenario_intent, city_context
        )
        
        base_scenario = base_result["specification"]
        
        # Create variants based on suggestions
        variants_suggestion = base_result.get("variants_suggestion", {})
        
        # Create study structure manually since we have a custom scenario
        study = {
            "study_id": str(uuid.uuid4()),
            "name": study_intent,
            "description": f"Comparison study based on generated scenario",
            "base_template": "custom",
            "created_at": datetime.now().isoformat(),
            "scenarios": [base_scenario],  # Start with base
            "parameter_ranges": variants_suggestion
        }
        
        # Generate variants using service
        if variants_suggestion:
            variants = self.scenario_service.generate_scenario_variants(
                base_scenario=base_scenario,
                variations=variants_suggestion,
                scenarios_path=self.scenarios_path
            )
            study["scenarios"].extend(variants)
        
        return {
            "study": study,
            "base_reasoning": base_result["reasoning"],
            "generated_by": "agentic_study_builder",
            "timestamp": datetime.now().isoformat()
        }
    
    def _parse_scenario_specification(self, spec_text: str) -> Dict[str, Any]:
        """Parse LLM-generated scenario specification."""
        try:
            # Try to extract JSON from the response
            if "```json" in spec_text:
                json_start = spec_text.find("```json") + 7
                json_end = spec_text.find("```", json_start)
                json_content = spec_text[json_start:json_end].strip()
            elif "{" in spec_text and "}" in spec_text:
                # Find the JSON object
                start = spec_text.find("{")
                end = spec_text.rfind("}") + 1
                json_content = spec_text[start:end]
            else:
                # Parse as key-value pairs
                return self._parse_key_value_scenario(spec_text)
            
            return json.loads(json_content)
            
        except Exception as e:
            logger.error(f"Failed to parse scenario specification: {e}")
            return self._get_basic_scenario_spec()
    
    def _parse_variants_suggestion(self, variants_text: str) -> Dict[str, List[Any]]:
        """Parse LLM-generated variants suggestion."""
        try:
            # Simple parsing of parameter variations
            variants = {}
            
            # Look for common parameter patterns
            if "compliance" in variants_text.lower():
                variants["parameters.compliance_rate"] = [0.6, 0.7, 0.8, 0.9]
            
            if "severity" in variants_text.lower():
                variants["severity"] = ["low", "medium", "high"]
            
            if "population" in variants_text.lower():
                variants["population_affected"] = [5000, 10000, 25000, 50000]
            
            if "duration" in variants_text.lower():
                variants["duration_minutes"] = [120, 180, 240, 360]
            
            return variants
            
        except Exception as e:
            logger.error(f"Failed to parse variants suggestion: {e}")
            return {
                "parameters.compliance_rate": [0.6, 0.8],
                "severity": ["medium", "high"]
            }
    
    def _parse_key_value_scenario(self, text: str) -> Dict[str, Any]:
        """Parse scenario from key-value text format."""
        scenario = self._get_basic_scenario_spec()
        
        lines = text.split('\n')
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if 'name' in key:
                    scenario['name'] = value
                elif 'hazard' in key or 'type' in key:
                    scenario['hazard_type'] = value.lower()
                elif 'severity' in key:
                    scenario['severity'] = value.lower()
                elif 'population' in key:
                    try:
                        scenario['population_affected'] = int(value.replace(',', ''))
                    except:
                        pass
                elif 'duration' in key:
                    try:
                        scenario['duration_minutes'] = int(value.split()[0])
                    except:
                        pass
        
        return scenario
    
    def _generate_template_scenario(self, intent: str, city_context: str, constraints: str) -> Dict[str, Any]:
        """Generate scenario using templates when LLM is not available."""
        intent_lower = intent.lower()
        
        # Determine scenario type from intent
        if "flood" in intent_lower:
            template_name = "flood_central"
        elif "fire" in intent_lower:
            template_name = "fire_building"
        elif "terror" in intent_lower or "security" in intent_lower:
            template_name = "terrorist_threat"
        elif "chemical" in intent_lower:
            template_name = "chemical_spill"
        else:
            template_name = "flood_central"  # Default
        
        # Create scenario from template using service
        scenario = self.scenario_service.create_scenario(
            template_name=template_name,
            scenario_name=f"Generated: {intent[:50]}",
            scenarios_path=self.scenarios_path
        )
        
        # Apply constraints if specified
        if "high severity" in constraints.lower():
            scenario["severity"] = "high"
        elif "low severity" in constraints.lower():
            scenario["severity"] = "low"
        
        return {
            "specification": scenario,
            "variants_suggestion": {
                "parameters.compliance_rate": [0.6, 0.7, 0.8],
                "severity": ["medium", "high"]
            },
            "reasoning": f"Template-based scenario for {intent}",
            "generated_by": "template",
            "intent": intent,
            "timestamp": datetime.now().isoformat()
        }
    
    def _get_basic_scenario_spec(self) -> Dict[str, Any]:
        """Get basic scenario specification."""
        return {
            "scenario_id": str(uuid.uuid4()),
            "name": "Generated Scenario",
            "description": "AI-generated evacuation scenario",
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
            },
            "created_at": datetime.now().isoformat(),
            "version": "1.0",
            "status": "draft"
        }


class AgenticBuilderService:
    """Main service orchestrating agentic builders."""

    def __init__(
        self,
        data_path: Optional[str] = None,
        scenarios_path: Optional[str] = None
    ):
        """
        Initialize with dependency injection.

        Args:
            data_path: Optional data path for metrics
            scenarios_path: Optional scenarios path
        """
        self.data_path = data_path
        self.scenarios_path = scenarios_path
        self.metrics_builder = AgenticMetricsBuilder(data_path=data_path)
        self.scenario_builder = AgenticScenarioBuilder(scenarios_path=scenarios_path)
        self.framework_converter = FrameworkScenarioConverter()
        logger.info("Agentic builder service initialized")
    
    async def create_analysis_package(
        self,
        analysis_goal: str,
        scenario_intent: str,
        city_context: str = "London",
        run_id: Optional[str] = None,
        use_framework: bool = True
    ) -> Dict[str, Any]:
        """
        Create a complete analysis package with both scenarios and metrics.
        
        Args:
            analysis_goal: What to analyze
            scenario_intent: What scenario to create
            city_context: City context
            run_id: Optional existing run to analyze
            use_framework: Whether to use framework-compliant scenarios
            
        Returns:
            Complete package with scenarios and optimized metrics
        """
        logger.info("Creating analysis package", goal=analysis_goal, scenario=scenario_intent, framework=use_framework)
        
        # Generate scenario (framework-compliant if requested)
        if use_framework:
            scenario_result = await self.scenario_builder.generate_framework_scenario(
                scenario_intent, city_context
            )
        else:
            scenario_result = await self.scenario_builder.generate_scenario_from_intent(
                scenario_intent, city_context
            )
        
        # Generate metrics optimized for this scenario
        metrics_result = await self.metrics_builder.optimize_metrics_for_scenario(
            scenario_result["specification"],
            analysis_goal
        )
        
        # Add framework evaluation info if using framework scenarios
        evaluation_info = None
        if use_framework and scenario_result.get("framework_compliant"):
            evaluation_info = {
                "template_used": scenario_result.get("template_used"),
                "compliance_level": scenario_result["specification"].get("provenance", {}).get("compliance_level"),
                "golden_standards_available": True,
                "evaluation_ready": True
            }
        
        # Convert framework scenario to executable config if needed
        executable_scenarios = []
        if use_framework and scenario_result.get("framework_compliant"):
            try:
                scenario_config = self.framework_converter.convert_framework_to_scenario_config(
                    scenario_result["specification"]
                )
                simulation_params = self.framework_converter.extract_simulation_parameters(
                    scenario_result["specification"]
                )
                
                executable_scenarios.append({
                    "config": scenario_config.dict(),
                    "simulation_params": simulation_params,
                    "framework_template": scenario_result.get("template_used"),
                    "source": "framework_conversion"
                })
                
                logger.info("Framework scenario converted to executable config", 
                           scenario_id=scenario_config.id,
                           template=scenario_result.get("template_used"))
                
            except Exception as e:
                logger.error("Failed to convert framework scenario", error=str(e))
                # Fall back to basic scenario generation
                executable_scenarios = []

        return {
            "analysis_goal": analysis_goal,
            "scenario": scenario_result,
            "metrics": metrics_result,
            "evaluation_info": evaluation_info,
            "executable_scenarios": executable_scenarios,
            "package_id": str(uuid.uuid4()),
            "created_at": datetime.now().isoformat(),
            "city_context": city_context,
            "framework_compliant": use_framework and scenario_result.get("framework_compliant", False)
        }
    
    async def create_framework_evaluation_package(
        self,
        template_name: str,
        analysis_goal: str = "Evaluate scenario against framework standards",
        city_context: str = "London"
    ) -> Dict[str, Any]:
        """
        Create an analysis package specifically for framework evaluation.
        
        Args:
            template_name: Framework template to use
            analysis_goal: Analysis objective
            city_context: City context
            
        Returns:
            Framework evaluation package
        """
        logger.info("Creating framework evaluation package", template=template_name)
        
        try:
            # Create framework scenario directly using service
            scenario = self.scenario_builder.scenario_service.create_framework_scenario(
                template_name=template_name,
                scenarios_path=self.scenarios_path
            )
            
            scenario_result = {
                "specification": scenario,
                "template_used": template_name,
                "framework_compliant": True,
                "generated_by": "direct_framework_selection",
                "timestamp": datetime.now().isoformat()
            }
            
            # Generate framework-optimized metrics
            metrics_result = await self.metrics_builder.optimize_metrics_for_scenario(
                scenario,
                f"{analysis_goal} - Framework compliance evaluation"
            )
            
            return {
                "analysis_goal": analysis_goal,
                "scenario": scenario_result,
                "metrics": metrics_result,
                "evaluation_info": {
                    "template_used": template_name,
                    "compliance_level": scenario.get("provenance", {}).get("compliance_level"),
                    "golden_standards_available": True,
                    "evaluation_ready": True,
                    "framework_source": scenario.get("provenance", {}).get("source")
                },
                "package_id": str(uuid.uuid4()),
                "created_at": datetime.now().isoformat(),
                "city_context": city_context,
                "framework_compliant": True,
                "package_type": "framework_evaluation"
            }
            
        except Exception as e:
            logger.error(f"Failed to create framework evaluation package: {e}")
            raise


# Mock implementations for when DSPy is not available
def mock_generate_metrics_spec(analysis_goal: str, available_data: str, context: str) -> Dict[str, str]:
    """Mock metrics generation."""
    return {
        "metrics_specification": """
metrics:
  clearance_p95:
    source: timeseries
    metric_key: clearance_pct
    operation: percentile_time_to_threshold
    args: {threshold_pct: 95}
    post_process: {divide_by: 60, round_to: 1}
""",
        "reasoning": f"Mock metrics generated for: {analysis_goal}"
    }


def mock_generate_scenario_spec(scenario_intent: str, city_context: str, constraints: str) -> Dict[str, str]:
    """Mock scenario generation."""
    return {
        "scenario_specification": json.dumps({
            "name": f"Mock scenario for {scenario_intent}",
            "hazard_type": "flood",
            "severity": "medium",
            "duration_minutes": 180,
            "population_affected": 10000
        }),
        "variants_suggestion": "Try different compliance rates: 0.6, 0.7, 0.8",
        "reasoning": f"Mock scenario generated for: {scenario_intent}"
    }


# Patch DSPy signatures if not available
if not DSPY_AVAILABLE:
    class MockSignature:
        def __init__(self, func):
            self.func = func
        
        def __call__(self, *args, **kwargs):
            return self.func(*args, **kwargs)
    
    GenerateMetricsSpec = MockSignature(mock_generate_metrics_spec)
    GenerateScenarioSpec = MockSignature(mock_generate_scenario_spec)
    OptimizeMetricsForScenario = MockSignature(mock_generate_metrics_spec)
