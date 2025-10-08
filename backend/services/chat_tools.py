"""
Chat Tools System
Provides tool/function calling capabilities for the emergency response chat assistant.
Allows the LLM to trigger actions like running simulations, checking status, etc.
"""

import structlog
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import json

logger = structlog.get_logger(__name__)


class ChatTool:
    """Base class for a chat tool that can be called by the LLM."""
    
    def __init__(self, name: str, description: str, parameters: Dict[str, Any]):
        self.name = name
        self.description = description
        self.parameters = parameters
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool with given parameters. Override in subclasses."""
        raise NotImplementedError
    
    def to_function_definition(self) -> Dict[str, Any]:
        """Convert tool to OpenAI function calling format."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }


class RunSimulationTool(ChatTool):
    """Tool to trigger a new evacuation simulation."""
    
    def __init__(self, simulation_service):
        self.simulation_service = simulation_service
        super().__init__(
            name="run_simulation",
            description="Trigger a new evacuation simulation for a specified location and hazard type. "
                       "Use this when the user asks to run, start, or execute a simulation.",
            parameters={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "The city to simulate (e.g., 'London', 'Westminster')",
                        "enum": ["London", "Westminster", "Camden", "Islington", "Hackney"]
                    },
                    "hazard_type": {
                        "type": "string",
                        "description": "Type of emergency hazard",
                        "enum": ["flood", "fire", "terrorist_attack", "chemical_spill", "earthquake", "general_evacuation"]
                    },
                    "affected_boroughs": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of specific boroughs affected (optional)"
                    },
                    "population_affected": {
                        "type": "integer",
                        "description": "Estimated number of people affected (optional)"
                    }
                },
                "required": ["city", "hazard_type"]
            }
        )
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute simulation with given parameters."""
        try:
            city = kwargs.get('city', 'London')
            hazard_type = kwargs.get('hazard_type', 'general_evacuation')
            affected_boroughs = kwargs.get('affected_boroughs', [])
            population = kwargs.get('population_affected')
            
            logger.info(f"Running simulation via chat tool: {city}, {hazard_type}")
            
            # Import here to avoid circular dependency
            from services.framework_simulation_service import FrameworkSimulationService
            
            sim_service = FrameworkSimulationService()
            
            # Create scenario configuration
            scenario_config = {
                "name": f"Chat-triggered {hazard_type} simulation for {city}",
                "city": city,
                "hazard_type": hazard_type,
                "timestamp": datetime.now().isoformat(),
                "triggered_by": "chat_assistant"
            }
            
            if affected_boroughs:
                scenario_config["affected_boroughs"] = affected_boroughs
            if population:
                scenario_config["population_affected"] = population
            
            # Run the simulation
            result = await sim_service.run_simulation(city, scenario_config)
            
            return {
                "success": True,
                "run_id": result.get('run_id'),
                "city": city,
                "hazard_type": hazard_type,
                "message": f"Started {hazard_type} evacuation simulation for {city}",
                "estimated_completion": "2-3 minutes"
            }
            
        except Exception as e:
            logger.error(f"Simulation execution failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to start simulation: {str(e)}"
            }


class GetSimulationStatusTool(ChatTool):
    """Tool to check the status of a running simulation."""
    
    def __init__(self, storage_service):
        self.storage_service = storage_service
        super().__init__(
            name="get_simulation_status",
            description="Check the status of a specific simulation run. "
                       "Use this when the user asks about a simulation's progress or results.",
            parameters={
                "type": "object",
                "properties": {
                    "run_id": {
                        "type": "string",
                        "description": "The unique identifier of the simulation run"
                    }
                },
                "required": ["run_id"]
            }
        )
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Get status of a simulation run."""
        try:
            run_id = kwargs.get('run_id')
            
            if not run_id:
                return {
                    "success": False,
                    "error": "No run_id provided"
                }
            
            # Get run status from storage
            run_data = await self.storage_service.get_run(run_id)
            
            if not run_data:
                return {
                    "success": False,
                    "error": f"Run {run_id} not found"
                }
            
            return {
                "success": True,
                "run_id": run_id,
                "status": run_data.get('status', 'unknown'),
                "city": run_data.get('city'),
                "created_at": run_data.get('created_at'),
                "completed": run_data.get('status') == 'completed',
                "message": f"Simulation {run_id} is {run_data.get('status', 'unknown')}"
            }
            
        except Exception as e:
            logger.error(f"Status check failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }


class ListRecentSimulationsTool(ChatTool):
    """Tool to list recent simulation runs."""
    
    def __init__(self, storage_service):
        self.storage_service = storage_service
        super().__init__(
            name="list_recent_simulations",
            description="List recent evacuation simulations. "
                       "Use this when the user asks about recent runs or wants to see what simulations have been done.",
            parameters={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of simulations to return (default 5)",
                        "default": 5
                    },
                    "city": {
                        "type": "string",
                        "description": "Filter by specific city (optional)"
                    }
                },
                "required": []
            }
        )
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """List recent simulations."""
        try:
            limit = kwargs.get('limit', 5)
            city_filter = kwargs.get('city')
            
            # Get all runs
            runs = await self.storage_service.list_all_runs()
            
            # Filter by city if specified
            if city_filter:
                runs = [r for r in runs if r.get('city', '').lower() == city_filter.lower()]
            
            # Sort by creation time (most recent first)
            runs.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            # Limit results
            runs = runs[:limit]
            
            # Format for response
            formatted_runs = [
                {
                    "run_id": r.get('run_id'),
                    "city": r.get('city'),
                    "status": r.get('status'),
                    "created_at": r.get('created_at')
                }
                for r in runs
            ]
            
            return {
                "success": True,
                "count": len(formatted_runs),
                "simulations": formatted_runs,
                "message": f"Found {len(formatted_runs)} recent simulations"
            }
            
        except Exception as e:
            logger.error(f"List simulations failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }


class GetBoroughStatusTool(ChatTool):
    """Tool to get the current status of a specific borough."""
    
    def __init__(self):
        super().__init__(
            name="get_borough_status",
            description="Get the current emergency preparedness status of a London borough. "
                       "Use this when the user asks about a specific borough's readiness or metrics.",
            parameters={
                "type": "object",
                "properties": {
                    "borough_name": {
                        "type": "string",
                        "description": "Name of the London borough (e.g., 'Westminster', 'Camden')"
                    }
                },
                "required": ["borough_name"]
            }
        )
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Get borough status."""
        try:
            borough = kwargs.get('borough_name', '')
            
            # Mock data for now - in production, fetch from actual metrics
            borough_data = {
                "borough": borough,
                "status": "amber",
                "clearance_time": 45.2,
                "fairness_index": 0.67,
                "robustness": 0.82,
                "last_assessed": datetime.now().isoformat(),
                "message": f"{borough} currently has AMBER status - acceptable but needs monitoring"
            }
            
            return {
                "success": True,
                **borough_data
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


class ChatToolRegistry:
    """Registry of all available chat tools."""
    
    def __init__(self):
        self.tools: Dict[str, ChatTool] = {}
    
    def register(self, tool: ChatTool):
        """Register a new tool."""
        self.tools[tool.name] = tool
        logger.info(f"Registered chat tool: {tool.name}")
    
    def get_tool(self, name: str) -> Optional[ChatTool]:
        """Get a tool by name."""
        return self.tools.get(name)
    
    def get_all_tools(self) -> List[ChatTool]:
        """Get all registered tools."""
        return list(self.tools.values())
    
    def get_function_definitions(self) -> List[Dict[str, Any]]:
        """Get function definitions for LLM function calling."""
        return [tool.to_function_definition() for tool in self.tools.values()]
    
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool with given parameters."""
        tool = self.get_tool(tool_name)
        
        if not tool:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found"
            }
        
        try:
            result = await tool.execute(**parameters)
            logger.info(f"Tool '{tool_name}' executed successfully", result=result)
            return result
        except Exception as e:
            logger.error(f"Tool '{tool_name}' execution failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }


# Global registry instance
_tool_registry = None

def get_tool_registry() -> ChatToolRegistry:
    """Get the global tool registry instance."""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ChatToolRegistry()
        _initialize_tools()
    return _tool_registry


def _initialize_tools():
    """Initialize and register all available tools."""
    from services.storage_service import StorageService
    
    registry = get_tool_registry()
    storage = StorageService()
    
    # Register all tools
    registry.register(RunSimulationTool(None))  # Service injected at execution time
    registry.register(GetSimulationStatusTool(storage))
    registry.register(ListRecentSimulationsTool(storage))
    registry.register(GetBoroughStatusTool())
    
    logger.info(f"Initialized {len(registry.tools)} chat tools")
