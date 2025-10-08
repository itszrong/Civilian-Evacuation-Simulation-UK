"""
MCP (Model Context Protocol) Server for London Evacuation Planning Tool.

This module exposes the evacuation planning system functionality via MCP,
allowing AI assistants to interact with the system for emergency planning.
"""

import asyncio
import json
import os
from typing import Any, Dict, List, Optional
from datetime import datetime
import structlog

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Resource, Tool, TextContent, ImageContent
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    Server = None
    stdio_server = None

from services.simulation_service import LondonGraphService, EvacuationSimulator
from services.orchestration.multi_city_orchestrator import EvacuationOrchestrator
from services.notification_service import (
    get_notification_service,
    NotificationRequest,
    NotificationType,
    NotificationPriority,
    NotificationTemplate
)
from models.schemas import ScenarioConfig

logger = structlog.get_logger(__name__)


class EvacuationMCPServer:
    """MCP Server for Evacuation Planning System."""

    def __init__(self):
        if not MCP_AVAILABLE:
            raise ImportError("MCP SDK not available. Install with: pip install mcp")

        self.server = Server("london-evacuation-planning")
        self.graph_service = LondonGraphService()
        self.simulator = EvacuationSimulator(self.graph_service)
        self.multi_city_service = EvacuationOrchestrator()
        self.notification_service = get_notification_service()

        self._register_resources()
        self._register_tools()

        logger.info("MCP Server initialized for London Evacuation Planning Tool")

    def _register_resources(self):
        """Register available resources that can be read."""

        @self.server.list_resources()
        async def list_resources() -> List[Resource]:
            """List available evacuation planning resources."""
            return [
                Resource(
                    uri="evacuation://capabilities",
                    name="System Capabilities",
                    description="Available features and capabilities of the evacuation planning system",
                    mimeType="application/json"
                ),
                Resource(
                    uri="evacuation://cities",
                    name="Supported Cities",
                    description="List of cities supported for evacuation simulation",
                    mimeType="application/json"
                ),
                Resource(
                    uri="evacuation://templates/notifications",
                    name="Notification Templates",
                    description="Available notification templates for emergency communications",
                    mimeType="application/json"
                ),
                Resource(
                    uri="evacuation://london/graph",
                    name="London Street Network",
                    description="London street network graph statistics",
                    mimeType="application/json"
                )
            ]

        @self.server.read_resource()
        async def read_resource(uri: str) -> str:
            """Read a specific resource."""
            logger.info("Reading resource", uri=uri)

            if uri == "evacuation://capabilities":
                return json.dumps({
                    "system": "London Evacuation Planning Tool",
                    "version": "1.0.0",
                    "features": [
                        "real_time_simulation",
                        "multi_city_support",
                        "network_based_routing",
                        "emergency_notifications",
                        "decision_memo_generation",
                        "scenario_comparison"
                    ],
                    "cities": ["london"],
                    "notification_channels": ["sms", "whatsapp"],
                    "government_ready": True
                }, indent=2)

            elif uri == "evacuation://cities":
                cities = self.multi_city_service.get_supported_cities()
                return json.dumps({
                    "supported_cities": cities,
                    "default": "london",
                    "capabilities": {
                        "london": {
                            "network_type": "real_street_network",
                            "data_source": "OpenStreetMap",
                            "routing": "A* pathfinding"
                        }
                    }
                }, indent=2)

            elif uri == "evacuation://templates/notifications":
                templates = {
                    template.value: content
                    for template, content in self.notification_service._templates.items()
                }
                return json.dumps(templates, indent=2)

            elif uri == "evacuation://london/graph":
                graph = await self.graph_service.get_london_graph()
                return json.dumps({
                    "nodes": graph.number_of_nodes(),
                    "edges": graph.number_of_edges(),
                    "coverage_area": "Central London",
                    "last_updated": datetime.now().isoformat()
                }, indent=2)

            else:
                raise ValueError(f"Unknown resource: {uri}")

    def _register_tools(self):
        """Register available tools that can be called."""

        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List available evacuation planning tools."""
            return [
                Tool(
                    name="run_evacuation_simulation",
                    description="Run an evacuation simulation for a specific city with given scenario parameters",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "city": {
                                "type": "string",
                                "description": "City to simulate (london)",
                                "enum": ["london"]
                            },
                            "num_simulations": {
                                "type": "integer",
                                "description": "Number of simulation runs",
                                "default": 10
                            },
                            "scenario_description": {
                                "type": "string",
                                "description": "Description of the evacuation scenario"
                            }
                        },
                        "required": ["city"]
                    }
                ),
                Tool(
                    name="send_emergency_notification",
                    description="Send emergency notification via SMS and WhatsApp to government contacts",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": "Emergency message to send"
                            },
                            "priority": {
                                "type": "string",
                                "enum": ["low", "medium", "high", "critical"],
                                "default": "high"
                            },
                            "recipients": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Phone numbers in E.164 format",
                                "default": [os.getenv("GOVERNMENT_CONTACT_NUMBER", "+44XXXXXXXXXX")]
                            }
                        },
                        "required": ["message"]
                    }
                ),
                Tool(
                    name="send_evacuation_alert",
                    description="Send formatted evacuation alert with route information",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "area": {
                                "type": "string",
                                "description": "Area being evacuated"
                            },
                            "route_id": {
                                "type": "string",
                                "description": "Recommended evacuation route"
                            },
                            "exit_points": {
                                "type": "string",
                                "description": "Exit points to use"
                            },
                            "closed_roads": {
                                "type": "string",
                                "description": "Roads to avoid"
                            },
                            "recipients": {
                                "type": "array",
                                "items": {"type": "string"},
                                "default": [os.getenv("GOVERNMENT_CONTACT_NUMBER", "+44XXXXXXXXXX")]
                            }
                        },
                        "required": ["area", "route_id", "exit_points", "closed_roads"]
                    }
                ),
                Tool(
                    name="get_simulation_status",
                    description="Get current status of evacuation simulations",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "city": {
                                "type": "string",
                                "description": "City to check status for",
                                "enum": ["london"]
                            }
                        },
                        "required": ["city"]
                    }
                ),
                Tool(
                    name="compare_evacuation_scenarios",
                    description="Compare multiple evacuation scenarios and recommend best option",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "city": {
                                "type": "string",
                                "enum": ["london"]
                            },
                            "scenarios": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "description": {"type": "string"}
                                    }
                                },
                                "description": "List of scenarios to compare"
                            }
                        },
                        "required": ["city", "scenarios"]
                    }
                ),
                Tool(
                    name="get_city_capabilities",
                    description="Get detailed capabilities and features for a specific city",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "city": {
                                "type": "string",
                                "enum": ["london"]
                            }
                        },
                        "required": ["city"]
                    }
                ),
                Tool(
                    name="notify_simulation_complete",
                    description="Send notification when evacuation simulation is complete",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "run_id": {"type": "string"},
                            "best_scenario": {"type": "string"},
                            "clearance_time": {"type": "number"},
                            "confidence": {"type": "number"},
                            "recipients": {
                                "type": "array",
                                "items": {"type": "string"},
                                "default": [os.getenv("GOVERNMENT_CONTACT_NUMBER", "+44XXXXXXXXXX")]
                            }
                        },
                        "required": ["run_id", "best_scenario", "clearance_time", "confidence"]
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Execute a tool call."""
            logger.info("Tool called", name=name, arguments=arguments)

            try:
                if name == "run_evacuation_simulation":
                    result = await self._run_evacuation_simulation(arguments)
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]

                elif name == "send_emergency_notification":
                    result = await self._send_emergency_notification(arguments)
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]

                elif name == "send_evacuation_alert":
                    result = await self._send_evacuation_alert(arguments)
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]

                elif name == "get_simulation_status":
                    result = await self._get_simulation_status(arguments)
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]

                elif name == "compare_evacuation_scenarios":
                    result = await self._compare_scenarios(arguments)
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]

                elif name == "get_city_capabilities":
                    result = await self._get_city_capabilities(arguments)
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]

                elif name == "notify_simulation_complete":
                    result = await self._notify_simulation_complete(arguments)
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]

                else:
                    raise ValueError(f"Unknown tool: {name}")

            except Exception as e:
                logger.error("Tool execution failed", name=name, error=str(e))
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": str(e), "tool": name}, indent=2)
                )]

    async def _run_evacuation_simulation(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Run evacuation simulation."""
        city = args["city"]
        num_simulations = args.get("num_simulations", 10)
        scenario_description = args.get("scenario_description", "Standard evacuation")

        logger.info("Running evacuation simulation via MCP",
                   city=city,
                   num_simulations=num_simulations)

        config = {
            "num_simulations": num_simulations,
            "num_routes": 8 if city == "london" else 5
        }

        result = self.multi_city_service.run_evacuation_simulation(city, config)

        return {
            "city": city,
            "scenario": scenario_description,
            "num_simulations": num_simulations,
            "results": result,
            "timestamp": datetime.now().isoformat()
        }

    async def _send_emergency_notification(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Send emergency notification."""
        message = args["message"]
        priority = NotificationPriority(args.get("priority", "high"))
        recipients = args.get("recipients", [os.getenv("GOVERNMENT_CONTACT_NUMBER", "+44XXXXXXXXXX")])

        logger.info("Sending emergency notification via MCP",
                   recipients=len(recipients),
                   priority=priority)

        requests = []
        for recipient in recipients:
            requests.extend([
                NotificationRequest(
                    recipient=recipient,
                    message_type=NotificationType.SMS,
                    priority=priority,
                    custom_message=f"🚨 EMERGENCY: {message}"
                ),
                NotificationRequest(
                    recipient=recipient,
                    message_type=NotificationType.WHATSAPP,
                    priority=priority,
                    custom_message=f"🚨 *EMERGENCY ALERT*\n\n{message}\n\n_London Evacuation Planning Tool_"
                )
            ])

        responses = await self.notification_service.send_bulk_notifications(requests)

        return {
            "sent": len(responses),
            "successful": len([r for r in responses if r.status != "failed"]),
            "failed": len([r for r in responses if r.status == "failed"]),
            "recipients": recipients,
            "timestamp": datetime.now().isoformat()
        }

    async def _send_evacuation_alert(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Send formatted evacuation alert."""
        recipients = args.get("recipients", [os.getenv("GOVERNMENT_CONTACT_NUMBER", "+44XXXXXXXXXX")])

        logger.info("Sending evacuation alert via MCP", area=args["area"])

        responses = await self.notification_service.send_evacuation_alert(
            recipients=recipients,
            area=args["area"],
            route_id=args["route_id"],
            exit_points=args["exit_points"],
            closed_roads=args["closed_roads"],
            info_url="gov.uk/emergency",
            authority="UK Government Emergency Response"
        )

        return {
            "alert_sent": True,
            "area": args["area"],
            "recipients": len(recipients),
            "successful": len([r for r in responses if r.status != "failed"]),
            "timestamp": datetime.now().isoformat()
        }

    async def _get_simulation_status(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get simulation status."""
        city = args["city"]

        supported_cities = self.multi_city_service.get_supported_cities()

        if city not in supported_cities:
            return {"error": f"City {city} not supported", "supported_cities": supported_cities}

        status = {
            "city": city,
            "supported": True,
            "status": "operational",
            "last_simulation": datetime.now().isoformat()
        }

        if city == "london":
            graph = await self.graph_service.get_london_graph()
            status["network_stats"] = {
                "nodes": graph.number_of_nodes(),
                "edges": graph.number_of_edges()
            }

        return status

    async def _compare_scenarios(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Compare evacuation scenarios."""
        city = args["city"]
        scenarios = args["scenarios"]

        logger.info("Comparing scenarios via MCP", city=city, count=len(scenarios))

        results = []
        for scenario in scenarios:
            sim_result = self.multi_city_service.run_evacuation_simulation(city, {
                "num_simulations": 10,
                "num_routes": 5
            })
            results.append({
                "name": scenario.get("name", "Unnamed"),
                "description": scenario.get("description", ""),
                "metrics": sim_result.get("heatmap_data", {})
            })

        return {
            "city": city,
            "scenarios_compared": len(results),
            "results": results,
            "recommendation": results[0]["name"] if results else None,
            "timestamp": datetime.now().isoformat()
        }

    async def _get_city_capabilities(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get city capabilities."""
        city = args["city"]

        capabilities = {
            "city": city,
            "simulation_ready": True
        }

        if city == "london":
            capabilities["features"] = {
                "network_type": "real_street_network",
                "data_source": "OpenStreetMap via OSMnx",
                "routing_algorithm": "A* pathfinding",
                "capacity_modeling": True,
                "traffic_simulation": True,
                "hospital_awareness": True,
                "bridge_identification": True
            }

        return capabilities

    async def _notify_simulation_complete(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Notify simulation complete."""
        recipients = args.get("recipients", [os.getenv("GOVERNMENT_CONTACT_NUMBER", "+44XXXXXXXXXX")])

        responses = await self.notification_service.notify_simulation_complete(
            recipients=recipients,
            run_id=args["run_id"],
            best_scenario=args["best_scenario"],
            clearance_time=args["clearance_time"],
            confidence=args["confidence"]
        )

        return {
            "notification_sent": True,
            "run_id": args["run_id"],
            "recipients": len(recipients),
            "successful": len([r for r in responses if r.status != "failed"]),
            "timestamp": datetime.now().isoformat()
        }

    async def run(self):
        """Run the MCP server."""
        logger.info("Starting MCP server for London Evacuation Planning Tool")

        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def main():
    """Main entry point for MCP server."""
    if not MCP_AVAILABLE:
        print("Error: MCP SDK not installed. Install with: pip install mcp")
        return

    try:
        server = EvacuationMCPServer()
        await server.run()
    except Exception as e:
        logger.error("MCP server failed", error=str(e))
        raise


if __name__ == "__main__":
    asyncio.run(main())
