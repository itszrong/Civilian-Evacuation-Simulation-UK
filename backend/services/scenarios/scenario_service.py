"""
Stateless Scenario Service

Wraps ScenarioBuilder with a stateless, dependency-injectable interface.
All operations are stateless - scenarios path passed as parameter.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import structlog

from scenarios.builder import ScenarioBuilder
from scenarios.framework_templates import FrameworkScenarioTemplates

logger = structlog.get_logger(__name__)


class ScenarioService:
    """
    Stateless service for scenario management.

    All methods accept scenarios_path as parameter instead of storing it as instance state.
    This allows the service to work across multiple scenario stores concurrently.
    """

    def __init__(self):
        """Initialize service. No instance state stored."""
        pass

    @staticmethod
    def create_scenario(
        template_name: Optional[str] = None,
        custom_params: Optional[Dict[str, Any]] = None,
        scenario_name: Optional[str] = None,
        scenarios_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new evacuation scenario. Stateless operation.

        Args:
            template_name: Name of template to use
            custom_params: Custom parameters to override template
            scenario_name: Custom name for the scenario
            scenarios_path: Path to save scenarios

        Returns:
            Complete scenario definition
        """
        builder = ScenarioBuilder(scenarios_path=scenarios_path)

        try:
            scenario = builder.create_scenario(
                template_name=template_name,
                custom_params=custom_params,
                scenario_name=scenario_name
            )
            return scenario
        except Exception as e:
            logger.error(f"Failed to create scenario: {e}", exc_info=True)
            return {"error": str(e)}

    @staticmethod
    def create_framework_scenario(
        template_name: str,
        custom_params: Optional[Dict[str, Any]] = None,
        scenario_name: Optional[str] = None,
        scenarios_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a framework-compliant scenario. Stateless operation.

        Args:
            template_name: Name of framework template
            custom_params: Custom parameters to override
            scenario_name: Custom name for the scenario
            scenarios_path: Path to save scenarios

        Returns:
            Framework-compliant scenario definition
        """
        builder = ScenarioBuilder(scenarios_path=scenarios_path)

        try:
            scenario = builder.create_framework_scenario(
                template_name=template_name,
                custom_params=custom_params,
                scenario_name=scenario_name
            )
            return scenario
        except Exception as e:
            logger.error(f"Failed to create framework scenario: {e}", exc_info=True)
            return {"error": str(e)}

    @staticmethod
    def save_scenario(
        scenario: Dict[str, Any],
        scenarios_path: Optional[str] = None
    ) -> str:
        """
        Save a scenario to disk. Stateless operation.

        Args:
            scenario: Scenario definition
            scenarios_path: Path to save scenarios

        Returns:
            Path to saved scenario file
        """
        builder = ScenarioBuilder(scenarios_path=scenarios_path)

        try:
            filepath = builder.save_scenario(scenario)
            return filepath
        except Exception as e:
            logger.error(f"Failed to save scenario: {e}", exc_info=True)
            return f"error: {str(e)}"

    @staticmethod
    def load_scenario(
        scenario_id: str,
        scenarios_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Load a scenario from disk. Stateless operation.

        Args:
            scenario_id: Scenario ID
            scenarios_path: Path to scenarios directory

        Returns:
            Scenario definition
        """
        builder = ScenarioBuilder(scenarios_path=scenarios_path)

        try:
            scenario = builder.load_scenario(scenario_id)
            return scenario
        except Exception as e:
            logger.error(f"Failed to load scenario: {e}", exc_info=True)
            return {"error": str(e)}

    @staticmethod
    def list_scenarios(scenarios_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all saved scenarios. Stateless operation.

        Args:
            scenarios_path: Path to scenarios directory

        Returns:
            List of scenario summaries
        """
        builder = ScenarioBuilder(scenarios_path=scenarios_path)

        try:
            scenarios = builder.list_scenarios()
            return scenarios
        except Exception as e:
            logger.error(f"Failed to list scenarios: {e}", exc_info=True)
            return []

    @staticmethod
    def generate_scenario_variants(
        base_scenario: Dict[str, Any],
        variations: Dict[str, List[Any]],
        scenarios_path: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate scenario variants. Stateless operation.

        Args:
            base_scenario: Base scenario to vary
            variations: Dictionary of parameters to vary
            scenarios_path: Path to scenarios directory

        Returns:
            List of scenario variants
        """
        builder = ScenarioBuilder(scenarios_path=scenarios_path)

        try:
            variants = builder.generate_scenario_variants(base_scenario, variations)
            return variants
        except Exception as e:
            logger.error(f"Failed to generate variants: {e}", exc_info=True)
            return []

    @staticmethod
    def validate_scenario(scenario: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a scenario definition. Pure function.

        Args:
            scenario: Scenario to validate

        Returns:
            Validation results
        """
        builder = ScenarioBuilder()

        try:
            validation = builder.validate_scenario(scenario)
            return validation
        except Exception as e:
            logger.error(f"Failed to validate scenario: {e}", exc_info=True)
            return {"valid": False, "errors": [str(e)], "warnings": []}

    @staticmethod
    def get_template_info() -> Dict[str, Any]:
        """
        Get information about available templates. Pure function.

        Returns:
            Dictionary of template information
        """
        builder = ScenarioBuilder()

        try:
            info = builder.get_template_info()
            return info
        except Exception as e:
            logger.error(f"Failed to get template info: {e}", exc_info=True)
            return {"error": str(e)}

    @staticmethod
    def get_framework_templates() -> Dict[str, Any]:
        """
        Get framework-compliant templates. Pure function.

        Returns:
            Dictionary of framework templates
        """
        try:
            templates = FrameworkScenarioTemplates.get_templates()
            return templates
        except Exception as e:
            logger.error(f"Failed to get framework templates: {e}", exc_info=True)
            return {}

    @staticmethod
    def get_scenarios_by_scale(scale: str) -> List[str]:
        """
        Get framework scenarios by scale category. Pure function.

        Args:
            scale: Scale category (e.g., 'local', 'major', 'mass')

        Returns:
            List of scenario template names
        """
        try:
            return FrameworkScenarioTemplates.get_scenario_by_scale(scale)
        except Exception as e:
            logger.error(f"Failed to get scenarios by scale: {e}", exc_info=True)
            return []

    @staticmethod
    def get_scenarios_by_hazard(hazard_type: str) -> List[str]:
        """
        Get framework scenarios by hazard type. Pure function.

        Args:
            hazard_type: Hazard type (e.g., 'flood', 'chemical', 'terrorist')

        Returns:
            List of scenario template names
        """
        try:
            return FrameworkScenarioTemplates.get_scenario_by_hazard(hazard_type)
        except Exception as e:
            logger.error(f"Failed to get scenarios by hazard: {e}", exc_info=True)
            return []
