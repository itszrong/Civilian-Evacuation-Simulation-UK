"""
Emergency Planning Service with DSPy
Analyzes evacuation hotspots and generates LLM-powered emergency response plans
"""

import dspy
from typing import List, Dict, Any, Optional
import numpy as np
from scipy.stats import gaussian_kde
import structlog
from core.config import get_settings
from services.llm_service import get_llm_service
from services.dspy_chat_tools import (
    run_simulation_tool,
    get_simulation_status_tool,
    list_recent_simulations_tool,
    get_borough_status_tool
)

logger = structlog.get_logger(__name__)
settings = get_settings()


class EmergencyHotspotAnalyzer:
    """Analyzes evacuation simulation data to identify critical hotspots."""

    def analyze_hotspots(self, simulation_data: Dict) -> List[Dict[str, Any]]:
        """
        Analyze simulation density data to find evacuation hotspots.
        Returns list of hotspot locations with severity scores.
        """
        try:
            # Extract density data from simulation
            if 'random_walks' in simulation_data:
                density_data = simulation_data['random_walks'].get('density_data', {})
            else:
                density_data = simulation_data.get('heatmap_data', {}).get('final_points', {})

            if not density_data:
                logger.warning("No density data found in simulation")
                return []

            x_coords = density_data.get('x', [])
            y_coords = density_data.get('y', [])
            densities = density_data.get('density', [])

            if not x_coords or not y_coords or not densities:
                return []

            # Find top hotspots (highest density areas)
            density_threshold = np.percentile(densities, 75)  # Top 25% density

            hotspots = []
            for i, (x, y, density) in enumerate(zip(x_coords, y_coords, densities)):
                if density >= density_threshold:
                    hotspots.append({
                        'id': f'hotspot_{i}',
                        'location': {'lat': y, 'lon': x},
                        'density': float(density),
                        'severity': self._calculate_severity(density, densities),
                        'estimated_population': int(density * 100)  # Mock estimate
                    })

            # Sort by severity (highest first)
            hotspots.sort(key=lambda h: h['severity'], reverse=True)

            logger.info(f"Identified {len(hotspots)} evacuation hotspots")
            return hotspots[:10]  # Return top 10

        except Exception as e:
            logger.error(f"Failed to analyze hotspots: {e}")
            return []

    def _calculate_severity(self, density: float, all_densities: List[float]) -> str:
        """Calculate severity level based on density percentile."""
        max_density = max(all_densities)
        percentile = (density / max_density) * 100

        if percentile >= 90:
            return "CRITICAL"
        elif percentile >= 75:
            return "HIGH"
        elif percentile >= 50:
            return "MEDIUM"
        else:
            return "LOW"


class POIService:
    """Service to find Points of Interest near hotspots using OSMnx."""

    def __init__(self):
        self.poi_cache = {}

    async def find_pois_near_hotspot(self, hotspot: Dict, radius_meters: int = 500) -> Dict[str, List[Dict]]:
        """
        Find POIs (buildings, hospitals, shops) near a hotspot.

        Args:
            hotspot: Hotspot location dict with 'location' key
            radius_meters: Search radius in meters

        Returns:
            Dict with categorized POIs: hospitals, buildings, shops, etc.
        """
        try:
            import osmnx as ox

            lat = hotspot['location']['lat']
            lon = hotspot['location']['lon']

            cache_key = f"{lat:.4f},{lon:.4f}_{radius_meters}"
            if cache_key in self.poi_cache:
                return self.poi_cache[cache_key]

            logger.info(f"Fetching POIs near ({lat}, {lon}) within {radius_meters}m")

            # Mock POI data for now - in production, use OSMnx tags parameter
            # pois = ox.geometries_from_point((lat, lon), tags={'amenity': True}, dist=radius_meters)

            # Mock data structure for now
            pois = {
                'hospitals': self._mock_hospitals(lat, lon),
                'buildings': self._mock_buildings(lat, lon),
                'shops': self._mock_shops(lat, lon),
                'transport': self._mock_transport(lat, lon)
            }

            self.poi_cache[cache_key] = pois
            return pois

        except Exception as e:
            logger.error(f"Failed to fetch POIs: {e}")
            return {'hospitals': [], 'buildings': [], 'shops': [], 'transport': []}

    def _mock_hospitals(self, lat: float, lon: float) -> List[Dict]:
        """Mock hospital data - replace with real OSMnx query."""
        return [
            {
                'name': 'City Emergency Hospital',
                'type': 'hospital',
                'capacity': 300,
                'distance_km': 0.8,
                'coordinates': {'lat': lat + 0.005, 'lon': lon + 0.003}
            },
            {
                'name': 'Central Medical Center',
                'type': 'hospital',
                'capacity': 500,
                'distance_km': 1.2,
                'coordinates': {'lat': lat - 0.007, 'lon': lon + 0.004}
            }
        ]

    def _mock_buildings(self, lat: float, lon: float) -> List[Dict]:
        """Mock building data - replace with real OSMnx query."""
        return [
            {'name': 'City Tower', 'type': 'office', 'occupancy': 2000, 'floors': 30},
            {'name': 'Residential Complex A', 'type': 'residential', 'occupancy': 500, 'floors': 15},
            {'name': 'Shopping Mall', 'type': 'commercial', 'occupancy': 3000, 'floors': 5}
        ]

    def _mock_shops(self, lat: float, lon: float) -> List[Dict]:
        """Mock shop data - replace with real OSMnx query."""
        return [
            {'name': 'Central Pharmacy', 'type': 'pharmacy', 'essential': True},
            {'name': 'Grocery Store', 'type': 'supermarket', 'essential': True},
            {'name': 'Gas Station', 'type': 'fuel', 'essential': True}
        ]

    def _mock_transport(self, lat: float, lon: float) -> List[Dict]:
        """Mock transport data - replace with real OSMnx query."""
        return [
            {'name': 'Metro Station Alpha', 'type': 'subway', 'capacity': 5000},
            {'name': 'Bus Terminal', 'type': 'bus', 'capacity': 1000}
        ]


# DSPy Signatures for Emergency Planning
class AnalyzeSimulationData(dspy.Signature):
    """Analyze evacuation simulation data to extract key insights."""

    simulation_metrics = dspy.InputField(desc="Real simulation metrics: clearance time, queue lengths, network topology")
    scenarios = dspy.InputField(desc="List of scenarios with hazard types, populations, compliance rates")
    city_context = dspy.InputField(desc="City name and geographic context")

    situation_assessment = dspy.OutputField(desc="Overall assessment of evacuation challenges")
    critical_findings = dspy.OutputField(desc="List of critical findings from the data")
    bottlenecks = dspy.OutputField(desc="Identified bottlenecks and capacity issues")
    timeline_estimate = dspy.OutputField(desc="Estimated timeline for full evacuation")


class IdentifyGovernmentDepartments(dspy.Signature):
    """Identify all government departments needed for emergency response."""

    situation_assessment = dspy.InputField(desc="Emergency situation assessment")
    hazard_types = dspy.InputField(desc="Types of hazards involved (flood, fire, chemical, etc.)")
    scale = dspy.InputField(desc="Scale of evacuation (population affected, area size)")

    departments = dspy.OutputField(desc="List of government departments with roles: Home Office, Health, Transport, Police, Fire, Ambulance, Local Authorities, etc.")
    coordination_structure = dspy.OutputField(desc="How departments should coordinate (COBR structure, command chain)")
    lead_department = dspy.OutputField(desc="Which department should lead coordination")


class AssignKeyPersonnel(dspy.Signature):
    """Assign key personnel and their specific responsibilities."""

    departments = dspy.InputField(desc="List of involved government departments")
    situation_scale = dspy.InputField(desc="Scale and complexity of the situation")
    city_context = dspy.InputField(desc="City name and context")

    personnel_assignments = dspy.OutputField(desc="Key personnel by role: Gold Commander, Silver Commanders, Bronze Commanders, Press Secretary, COBR Chair, etc.")
    activation_order = dspy.OutputField(desc="Order in which personnel should be activated")
    contact_protocols = dspy.OutputField(desc="How personnel should be contacted and mobilized")


class GenerateEvacuationStrategy(dspy.Signature):
    """Generate comprehensive evacuation strategy with all government areas."""

    simulation_data = dspy.InputField(desc="Real simulation results with routes, clearance times, bottlenecks")
    departments = dspy.InputField(desc="Involved government departments")
    personnel = dspy.InputField(desc="Assigned key personnel")
    critical_findings = dspy.InputField(desc="Critical findings from analysis")

    strategy = dspy.OutputField(desc="Comprehensive evacuation strategy with phases, priorities, and actions")
    resource_deployment = dspy.OutputField(desc="Detailed resource deployment plan (vehicles, personnel, equipment)")
    communication_plan = dspy.OutputField(desc="Public communication strategy and messaging")
    contingency_plans = dspy.OutputField(desc="Backup plans for failures or complications")
    timeline = dspy.OutputField(desc="Detailed timeline with milestones and checkpoints")


class AnalyzeEmergencySituation(dspy.Signature):
    """Analyze emergency situation and prioritize response actions."""

    hotspot_data = dspy.InputField(desc="Evacuation hotspot information including location, density, and severity")
    nearby_pois = dspy.InputField(desc="Nearby points of interest: hospitals, buildings, shops, transport")
    city_context = dspy.InputField(desc="City name and general context")

    priority_ranking = dspy.OutputField(desc="Priority ranking (1-10) for this hotspot")
    severity_assessment = dspy.OutputField(desc="Detailed severity assessment")
    recommended_actions = dspy.OutputField(desc="List of recommended immediate actions")
    resource_allocation = dspy.OutputField(desc="Recommended resource allocation (personnel, vehicles, supplies)")
    risk_factors = dspy.OutputField(desc="Key risk factors and vulnerabilities")


class GenerateRoleSpecificGuidance(dspy.Signature):
    """Generate role-specific guidance for government officials."""

    role = dspy.InputField(desc="Government role: PM, DPM, Comms, Chief of Staff, CE, Permanent Secretary")
    emergency_plan = dspy.InputField(desc="Overall emergency response plan with priorities and actions")
    city_context = dspy.InputField(desc="City name and situation context")

    guidance = dspy.OutputField(desc="Specific guidance and action items for this role")
    key_decisions = dspy.OutputField(desc="Key decisions this role needs to make")
    coordination_points = dspy.OutputField(desc="Who this role needs to coordinate with")
    communication_strategy = dspy.OutputField(desc="Recommended communication approach")


class EmergencyResponseChat(dspy.Signature):
    """Interactive chat for emergency response planning."""

    conversation_history = dspy.InputField(desc="Previous conversation messages")
    user_role = dspy.InputField(desc="User's government role")
    user_question = dspy.InputField(desc="User's current question or request")
    emergency_plan = dspy.InputField(desc="Current emergency response plan context")

    response = dspy.OutputField(desc="Clear, actionable response tailored to user's role")


class EmergencyPlannerModule(dspy.Module):
    """Main DSPy module for emergency response planning with comprehensive tools."""

    def __init__(self):
        super().__init__()
        # Core analysis tools
        self.analyze_simulation = dspy.ChainOfThought(AnalyzeSimulationData)
        self.identify_departments = dspy.ChainOfThought(IdentifyGovernmentDepartments)
        self.assign_personnel = dspy.ChainOfThought(AssignKeyPersonnel)
        self.generate_strategy = dspy.ChainOfThought(GenerateEvacuationStrategy)

        # Legacy tools
        self.analyze = dspy.ChainOfThought(AnalyzeEmergencySituation)
        self.generate_guidance = dspy.ChainOfThought(GenerateRoleSpecificGuidance)
        self.chat = dspy.ChainOfThought(EmergencyResponseChat)

    def forward(self, hotspot_data: str, nearby_pois: str, city_context: str):
        """Analyze a single hotspot and generate response plan."""
        result = self.analyze(
            hotspot_data=hotspot_data,
            nearby_pois=nearby_pois,
            city_context=city_context
        )
        return result

    def comprehensive_analysis(self, simulation_metrics: str, scenarios: str, city_context: str):
        """Run comprehensive analysis with all tools."""
        # Step 1: Analyze simulation data
        sim_analysis = self.analyze_simulation(
            simulation_metrics=simulation_metrics,
            scenarios=scenarios,
            city_context=city_context
        )

        # Step 2: Identify departments needed
        departments = self.identify_departments(
            situation_assessment=sim_analysis.situation_assessment,
            hazard_types=scenarios,
            scale=simulation_metrics
        )

        # Step 3: Assign personnel
        personnel = self.assign_personnel(
            departments=departments.departments,
            situation_scale=simulation_metrics,
            city_context=city_context
        )

        # Step 4: Generate comprehensive strategy
        strategy = self.generate_strategy(
            simulation_data=simulation_metrics,
            departments=departments.departments,
            personnel=personnel.personnel_assignments,
            critical_findings=sim_analysis.critical_findings
        )

        return {
            'simulation_analysis': sim_analysis,
            'departments': departments,
            'personnel': personnel,
            'strategy': strategy
        }


class EmergencyPlanningService:
    """Main service orchestrating emergency response planning."""

    def __init__(self):
        self.hotspot_analyzer = EmergencyHotspotAnalyzer()
        self.poi_service = POIService()
        self.llm_service = get_llm_service()
        self.llm_planner = self.llm_service.create_module(EmergencyPlannerModule)
        
        # Initialize DSPy ReAct agent with tools
        if self.llm_service.is_available():
            try:
                self.react_agent = dspy.ReAct(
                    signature="question -> answer",
                    tools=[
                        run_simulation_tool,
                        get_simulation_status_tool,
                        list_recent_simulations_tool,
                        get_borough_status_tool
                    ],
                    max_iters=5
                )
                logger.info("Initialized DSPy ReAct agent with 4 tools")
            except Exception as e:
                logger.error(f"Failed to initialize ReAct agent: {e}")
                self.react_agent = None
        else:
            self.react_agent = None


    async def generate_emergency_plan(self, simulation_data: Dict, city: str) -> Dict[str, Any]:
        """
        Generate comprehensive emergency response plan from simulation data.

        Args:
            simulation_data: Output from evacuation simulation
            city: City name

        Returns:
            Emergency response plan with hotspots, priorities, actions, departments, personnel, and strategy
        """
        try:
            # Step 1: Identify hotspots
            hotspots = self.hotspot_analyzer.analyze_hotspots(simulation_data)

            if not hotspots:
                return {
                    'status': 'no_hotspots',
                    'message': 'No critical hotspots identified',
                    'hotspots': []
                }

            # Step 2: Enrich each hotspot with POI data and LLM analysis
            enriched_hotspots = []
            for hotspot in hotspots:
                pois = await self.poi_service.find_pois_near_hotspot(hotspot)

                # Add LLM analysis if available
                if self.llm_planner:
                    llm_analysis = await self._analyze_hotspot_with_llm(hotspot, pois, city)
                    hotspot['llm_analysis'] = llm_analysis
                else:
                    hotspot['llm_analysis'] = self._mock_analysis(hotspot, pois)

                hotspot['nearby_pois'] = pois
                enriched_hotspots.append(hotspot)

            # Step 3: Generate comprehensive strategy using new tools
            comprehensive_strategy = await self._generate_comprehensive_strategy(simulation_data, enriched_hotspots, city)

            # Step 4: Generate overall plan
            plan = {
                'city': city,
                'timestamp': simulation_data.get('timestamp'),
                'total_hotspots': len(enriched_hotspots),
                'critical_hotspots': sum(1 for h in enriched_hotspots if h['severity'] == 'CRITICAL'),
                'hotspots': enriched_hotspots,
                'summary': self._generate_plan_summary(enriched_hotspots),
                'comprehensive_strategy': comprehensive_strategy
            }

            logger.info(f"Generated emergency plan for {city} with {len(enriched_hotspots)} hotspots and comprehensive strategy")
            return plan

        except Exception as e:
            logger.error(f"Failed to generate emergency plan: {e}")
            return {'status': 'error', 'message': str(e)}

    async def _generate_comprehensive_strategy(self, simulation_data: Dict, hotspots: List[Dict], city: str) -> Dict:
        """Generate comprehensive strategy using all tools."""
        try:
            if not self.llm_planner:
                return self._mock_comprehensive_strategy(simulation_data, hotspots, city)

            # Extract key metrics from simulation
            calculated_metrics = simulation_data.get('calculated_metrics', {})
            scenarios = simulation_data.get('scenarios', [])

            metrics_str = f"Clearance time: {calculated_metrics.get('clearance_time_p50', 0)} min (p50), " \
                         f"{calculated_metrics.get('clearance_time_p95', 0)} min (p95). " \
                         f"Max queue: {calculated_metrics.get('max_queue_length', 0)} people. " \
                         f"Network: {calculated_metrics.get('total_nodes', 0)} nodes, " \
                         f"{calculated_metrics.get('total_edges', 0)} edges, " \
                         f"density {calculated_metrics.get('network_density', 0):.3f}. " \
                         f"Efficiency: {calculated_metrics.get('evacuation_efficiency', 0):.1f}%"

            scenarios_str = "\n".join([
                f"- {s.get('name', 'Scenario')}: {s.get('hazard_type', 'evacuation')}, "
                f"population {s.get('population_affected', 0)}, "
                f"compliance {s.get('compliance_rate', 0)*100:.0f}%, "
                f"transport disruption {s.get('transport_disruption', 0)*100:.0f}%"
                for s in scenarios[:5]  # Top 5 scenarios
            ])

            # Run comprehensive analysis
            result = self.llm_planner.comprehensive_analysis(
                simulation_metrics=metrics_str,
                scenarios=scenarios_str,
                city_context=f"{city}, UK"
            )

            return {
                'simulation_analysis': {
                    'situation_assessment': result['simulation_analysis'].situation_assessment,
                    'critical_findings': result['simulation_analysis'].critical_findings,
                    'bottlenecks': result['simulation_analysis'].bottlenecks,
                    'timeline_estimate': result['simulation_analysis'].timeline_estimate
                },
                'departments': {
                    'departments_list': result['departments'].departments,
                    'coordination_structure': result['departments'].coordination_structure,
                    'lead_department': result['departments'].lead_department
                },
                'personnel': {
                    'assignments': result['personnel'].personnel_assignments,
                    'activation_order': result['personnel'].activation_order,
                    'contact_protocols': result['personnel'].contact_protocols
                },
                'strategy': {
                    'overall_strategy': result['strategy'].strategy,
                    'resource_deployment': result['strategy'].resource_deployment,
                    'communication_plan': result['strategy'].communication_plan,
                    'contingency_plans': result['strategy'].contingency_plans,
                    'timeline': result['strategy'].timeline
                }
            }

        except Exception as e:
            logger.error(f"Comprehensive strategy generation failed: {e}")
            return self._mock_comprehensive_strategy(simulation_data, hotspots, city)

    def _mock_comprehensive_strategy(self, simulation_data: Dict, hotspots: List[Dict], city: str) -> Dict:
        """Mock comprehensive strategy when LLM is unavailable."""
        calculated_metrics = simulation_data.get('calculated_metrics', {})
        scenarios = simulation_data.get('scenarios', [])

        return {
            'simulation_analysis': {
                'situation_assessment': f"Evacuation simulation for {city} indicates clearance time of "
                                      f"{calculated_metrics.get('clearance_time_p50', 45)} minutes with "
                                      f"{len(hotspots)} critical hotspots identified.",
                'critical_findings': [
                    f"Network has {calculated_metrics.get('total_nodes', 0)} street intersections",
                    f"Maximum queue length: {calculated_metrics.get('max_queue_length', 100)} people",
                    f"Evacuation efficiency: {calculated_metrics.get('evacuation_efficiency', 50)}%",
                    f"{len([h for h in hotspots if h['severity'] == 'CRITICAL'])} CRITICAL severity hotspots"
                ],
                'bottlenecks': [
                    "High-degree nodes in street network",
                    "Limited egress routes from city center",
                    "Transport disruption zones"
                ],
                'timeline_estimate': f"Full evacuation: {calculated_metrics.get('clearance_time_p95', 90)} minutes (95th percentile)"
            },
            'departments': {
                'departments_list': [
                    "Home Office - Overall coordination",
                    "Department of Health - Medical response",
                    "Department for Transport - Transport coordination",
                    "Metropolitan Police - Security and traffic control",
                    "London Fire Brigade - Fire and rescue",
                    "London Ambulance Service - Medical emergency response",
                    "Local Authority (Westminster) - Local coordination",
                    "COBR (Cabinet Office Briefing Rooms) - Central coordination"
                ],
                'coordination_structure': "COBR chairs overall response. Gold-Silver-Bronze command structure. "
                                        "Gold: Strategic command. Silver: Tactical coordination. Bronze: Operational delivery.",
                'lead_department': "Home Office leads with support from COBR"
            },
            'personnel': {
                'assignments': [
                    "Gold Commander: Chief Constable - Overall strategic command",
                    "Silver Commander (Police): Borough Commander - Tactical police operations",
                    "Silver Commander (Fire): Area Manager - Fire and rescue coordination",
                    "Silver Commander (Ambulance): Duty Manager - Medical response",
                    "Bronze Commanders: Sector leads for each hotspot zone",
                    "Press Secretary: Public communications",
                    "COBR Chair: Cross-government coordination",
                    "Scientific Advisor: Technical guidance"
                ],
                'activation_order': [
                    "1. Gold Commander",
                    "2. COBR Chair and Home Office",
                    "3. Silver Commanders (all services)",
                    "4. Bronze Commanders (by zone priority)",
                    "5. Support personnel and specialists"
                ],
                'contact_protocols': "Primary: Secure government phone lines. Secondary: Encrypted radio. "
                                   "Tertiary: Secure mobile apps. 24/7 duty officers activated immediately."
            },
            'strategy': {
                'overall_strategy': f"Phased evacuation of {city} prioritizing CRITICAL hotspots. "
                                  f"Establish evacuation corridors along optimal A* routes. "
                                  f"Deploy resources to {len(hotspots)} identified hotspots in priority order. "
                                  f"Maintain communication with evacuees throughout process.",
                'resource_deployment': {
                    'phase_1': f"Deploy to {len([h for h in hotspots if h['severity'] == 'CRITICAL'])} CRITICAL hotspots",
                    'personnel': f"{sum([h['llm_analysis']['resource_allocation'].get('personnel', 30) for h in hotspots])} total personnel",
                    'vehicles': f"{sum([h['llm_analysis']['resource_allocation'].get('vehicles', 5) for h in hotspots])} emergency vehicles",
                    'medical_units': f"{sum([h['llm_analysis']['resource_allocation'].get('medical_units', 1) for h in hotspots])} medical units"
                },
                'communication_plan': [
                    "T+0: Activate Emergency Alert System",
                    "T+5: First public statement from Gold Commander",
                    "T+15: Detailed evacuation instructions via all channels",
                    "T+30: Regular updates every 15 minutes",
                    "Ongoing: Social media monitoring and response"
                ],
                'contingency_plans': [
                    "Route blockage: Secondary evacuation corridors pre-identified",
                    "Medical surge: Additional hospitals on standby",
                    "Communication failure: Backup radio systems and mobile units",
                    "Resource shortage: Mutual aid agreements with neighboring authorities"
                ],
                'timeline': [
                    "T+0: Emergency declared, Gold command activated",
                    "T+5: All Silver commanders activated",
                    "T+10: Bronze commanders deployed to zones",
                    f"T+15: Evacuation begins from CRITICAL zones",
                    f"T+30: Full evacuation underway",
                    f"T+{calculated_metrics.get('clearance_time_p50', 45)}: 50% evacuation complete",
                    f"T+{calculated_metrics.get('clearance_time_p95', 90)}: 95% evacuation complete",
                    f"T+{int(calculated_metrics.get('clearance_time_p95', 90) * 1.2)}: All-clear assessment"
                ]
            }
        }

    async def _analyze_hotspot_with_llm(self, hotspot: Dict, pois: Dict, city: str) -> Dict:
        """Use LLM to analyze hotspot and generate recommendations."""
        try:
            hotspot_str = f"Location: ({hotspot['location']['lat']}, {hotspot['location']['lon']}), " \
                         f"Severity: {hotspot['severity']}, Density: {hotspot['density']:.2f}, " \
                         f"Est. Population: {hotspot['estimated_population']}"

            pois_str = f"Nearby hospitals: {len(pois['hospitals'])}, Buildings: {len(pois['buildings'])}, " \
                      f"Shops: {len(pois['shops'])}, Transport: {len(pois['transport'])}"

            result = self.llm_planner(
                hotspot_data=hotspot_str,
                nearby_pois=pois_str,
                city_context=f"City: {city}, Emergency evacuation scenario"
            )

            return {
                'priority_ranking': result.priority_ranking,
                'severity_assessment': result.severity_assessment,
                'recommended_actions': result.recommended_actions,
                'resource_allocation': result.resource_allocation,
                'risk_factors': result.risk_factors
            }

        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return self._mock_analysis(hotspot, pois)

    def _mock_analysis(self, hotspot: Dict, pois: Dict) -> Dict:
        """Mock LLM analysis when no LLM is configured."""
        severity = hotspot['severity']

        return {
            'priority_ranking': 9 if severity == 'CRITICAL' else 7 if severity == 'HIGH' else 5,
            'severity_assessment': f"{severity} severity hotspot with high evacuation density. "
                                  f"Immediate attention required.",
            'recommended_actions': [
                "Deploy emergency response teams immediately",
                "Establish evacuation corridors",
                "Set up medical triage stations",
                "Coordinate with nearby hospitals for capacity"
            ],
            'resource_allocation': {
                'personnel': 50 if severity == 'CRITICAL' else 30,
                'vehicles': 10 if severity == 'CRITICAL' else 5,
                'medical_units': 3 if severity == 'CRITICAL' else 1
            },
            'risk_factors': [
                "High population density",
                "Limited egress routes",
                "Proximity to vulnerable infrastructure"
            ]
        }

    def _generate_plan_summary(self, hotspots: List[Dict]) -> Dict:
        """Generate executive summary of emergency plan."""
        critical_count = sum(1 for h in hotspots if h['severity'] == 'CRITICAL')
        high_count = sum(1 for h in hotspots if h['severity'] == 'HIGH')

        total_population = sum(h.get('estimated_population', 0) for h in hotspots)

        return {
            'overview': f"Identified {len(hotspots)} evacuation hotspots requiring immediate response",
            'critical_areas': critical_count,
            'high_priority_areas': high_count,
            'total_affected_population': total_population,
            'immediate_priorities': [
                f"Address {critical_count} CRITICAL severity hotspots",
                "Deploy emergency response teams to highest density areas",
                "Coordinate with nearby hospitals and emergency services",
                "Establish communication channels with affected populations"
            ]
        }

    async def chat_response(self, role: str, question: str, plan_context: Dict,
                           conversation_history: List[Dict]) -> str:
        """
        Generate role-specific chat response for emergency planning.
        Uses centralized LLM service with comprehensive logging.

        Args:
            role: User's government role (PM, DPM, etc.)
            question: User's question
            plan_context: Current emergency plan data
            conversation_history: Previous messages

        Returns:
            Response message
        """
        try:
            # Check for special commands
            question_lower = question.lower()

            # Special command: Generate comprehensive strategy
            if 'generate scenario' in question_lower or 'generate strategy' in question_lower or 'full strategy' in question_lower:
                strategy = plan_context.get('comprehensive_strategy', {})

                if not strategy:
                    return "⚠️ Comprehensive strategy not available. Please wait for the simulation analysis to complete."

                response = "## 📋 Comprehensive Evacuation Strategy\n\n"

                # Situation Assessment
                if 'simulation_analysis' in strategy:
                    sim_analysis = strategy['simulation_analysis']
                    response += f"### Situation Assessment\n{sim_analysis.get('situation_assessment', 'N/A')}\n\n"
                    response += f"**Critical Findings:**\n"
                    for finding in sim_analysis.get('critical_findings', []):
                        response += f"- {finding}\n"
                    response += f"\n**Timeline:** {sim_analysis.get('timeline_estimate', 'N/A')}\n\n"

                # Government Departments
                if 'departments' in strategy:
                    depts = strategy['departments']
                    response += f"### 🏛️ Government Departments Involved\n"
                    response += f"**Lead Department:** {depts.get('lead_department', 'N/A')}\n\n"
                    response += f"**All Departments:**\n"
                    for dept in depts.get('departments_list', []):
                        response += f"- {dept}\n"
                    response += f"\n**Coordination:** {depts.get('coordination_structure', 'N/A')}\n\n"

                # Key Personnel
                if 'personnel' in strategy:
                    personnel = strategy['personnel']
                    response += f"### 👥 Key Personnel Assignments\n"
                    for assignment in personnel.get('assignments', []):
                        response += f"- {assignment}\n"
                    response += f"\n**Activation Order:**\n"
                    for order in personnel.get('activation_order', []):
                        response += f"{order}\n"
                    response += f"\n**Contact Protocols:** {personnel.get('contact_protocols', 'N/A')}\n\n"

                # Overall Strategy
                if 'strategy' in strategy:
                    strat = strategy['strategy']
                    response += f"### 🎯 Overall Strategy\n{strat.get('overall_strategy', 'N/A')}\n\n"

                    # Resource Deployment
                    response += f"**Resource Deployment:**\n"
                    resource_dep = strat.get('resource_deployment', {})
                    if isinstance(resource_dep, dict):
                        for key, value in resource_dep.items():
                            response += f"- {key.replace('_', ' ').title()}: {value}\n"
                    else:
                        response += f"{resource_dep}\n"
                    response += "\n"

                    # Communication Plan
                    response += f"**Communication Plan:**\n"
                    for comm in strat.get('communication_plan', []):
                        response += f"- {comm}\n"
                    response += "\n"

                    # Timeline
                    response += f"**Timeline:**\n"
                    for milestone in strat.get('timeline', []):
                        response += f"- {milestone}\n"
                    response += "\n"

                    # Contingencies
                    response += f"**Contingency Plans:**\n"
                    for contingency in strat.get('contingency_plans', []):
                        response += f"- {contingency}\n"

                return response

            # Check if user question requires tool use
            if self._should_use_tools(question):
                # Use DSPy ReAct agent for tool-based responses
                if self.react_agent:
                    try:
                        # Build context for the agent
                        context_parts = []
                        if plan_context:
                            if plan_context.get('current_situation'):
                                context_parts.append(f"Context: {plan_context['current_situation']}")
                            if plan_context.get('total_hotspots'):
                                context_parts.append(f"Current plan has {plan_context['total_hotspots']} hotspots")
                        
                        context_str = "\n".join(context_parts) if context_parts else ""
                        full_question = f"{context_str}\n\nUser ({role}): {question}" if context_str else f"User ({role}): {question}"
                        
                        # Call ReAct agent
                        result = self.react_agent(question=full_question)
                        
                        logger.info(f"ReAct agent completed. Trajectory: {result.trajectory}")
                        return result.answer
                        
                    except Exception as e:
                        logger.error(f"ReAct agent failed: {e}", exc_info=True)
                        # Fall through to regular LLM response
            
            # Normal LLM chat response (no tools)
            if not self.llm_service.is_available():
                return self._mock_chat_response(role, question, plan_context)

            # Build comprehensive prompt for the LLM
            prompt = self._build_chat_prompt(role, question, plan_context, conversation_history)
            
            # Use centralized LLM service with logging
            response = await self.llm_service.generate_text(
                prompt=prompt,
                max_tokens=2000,
                metadata={
                    "service": "emergency_planner",
                    "function": "chat_response",
                    "user_role": role,
                    "has_plan_context": bool(plan_context),
                    "conversation_length": len(conversation_history)
                }
            )
            
            return response

        except Exception as e:
            logger.error(f"Chat response failed: {e}")
            return self._mock_chat_response(role, question, plan_context)
    
    def _build_chat_prompt(self, role: str, question: str, plan_context: Dict, 
                          conversation_history: List[Dict]) -> str:
        """Build comprehensive prompt for chat LLM call."""
        
        prompt_parts = []
        
        # System context
        prompt_parts.append("You are an emergency response assistant helping UK government officials coordinate evacuation planning.")
        prompt_parts.append(f"The user is a {role} asking for guidance.")
        prompt_parts.append("")
        
        # Add conversation history
        if conversation_history:
            prompt_parts.append("## Conversation History:")
            for msg in conversation_history[-5:]:  # Last 5 messages
                prompt_parts.append(f"{msg['role']}: {msg['content']}")
            prompt_parts.append("")
        
        # Add plan context
        if plan_context:
            prompt_parts.append("## Current Context:")
            
            # Add current situation
            if plan_context.get('current_situation'):
                prompt_parts.append(f"Situation: {plan_context['current_situation']}")
            
            # Add emergency plan data
            hotspots = plan_context.get('total_hotspots', 0)
            critical = plan_context.get('critical_hotspots', 0)
            if hotspots > 0 or critical > 0:
                prompt_parts.append(f"Emergency plan: {hotspots} hotspots identified, {critical} critical")
            
            # Add strategy context
            if 'comprehensive_strategy' in plan_context:
                strategy = plan_context['comprehensive_strategy']
                if 'departments' in strategy:
                    depts = strategy['departments'].get('departments_list', [])[:5]
                    if depts:
                        prompt_parts.append(f"Key departments involved: {', '.join(depts)}")
                if 'personnel' in strategy:
                    personnel = strategy['personnel'].get('assignments', [])[:3]
                    if personnel:
                        prompt_parts.append(f"Key personnel: {'; '.join(personnel)}")
            
            # Add page context
            if plan_context.get('page_context'):
                page_ctx = plan_context['page_context']
                prompt_parts.append(f"User is viewing: {page_ctx.get('current_page', 'unknown page')}")
                if page_ctx.get('current_tab'):
                    prompt_parts.append(f"Current tab: {page_ctx['current_tab']}")
            
            prompt_parts.append("")
        
        # Add the question
        prompt_parts.append(f"## User Question:")
        prompt_parts.append(question)
        prompt_parts.append("")
        
        # Add instructions
        prompt_parts.append("## Instructions:")
        prompt_parts.append(f"Provide a clear, actionable response tailored to the {role}'s role and responsibilities.")
        prompt_parts.append("Be specific and reference the current context when relevant.")
        prompt_parts.append("Use a professional, government-appropriate tone.")
        
        return "\n".join(prompt_parts)
    
    def _should_use_tools(self, question: str) -> bool:
        """Determine if the question requires tool use."""
        question_lower = question.lower()
        
        # Keywords that indicate tool use
        tool_keywords = [
            'run', 'start', 'execute', 'trigger', 'simulation',
            'status', 'check', 'progress',
            'list', 'show', 'recent',
            'borough', 'westminster', 'camden', 'islington'
        ]
        
        return any(keyword in question_lower for keyword in tool_keywords)
    
    async def _handle_tool_calls(self, llm_response: str) -> Optional[Dict[str, Any]]:
        """
        Check if the LLM response contains a tool call and execute it.
        Returns the tool result if a tool was called, None otherwise.
        """
        try:
            # For now, parse simple tool calls from the response
            # In production with OpenAI function calling, this would be handled by the API
            
            # Check for simulation trigger patterns
            import re
            
            # Pattern: "run simulation" or "start simulation" with city and hazard type
            sim_pattern = r'(?:run|start|execute|trigger)\s+(?:a\s+)?(?:simulation|sim)\s+(?:for\s+)?(\w+).*?(?:flood|fire|terrorist|chemical|earthquake|evacuation)'
            match = re.search(sim_pattern, llm_response.lower())
            
            if match:
                city = match.group(1).title()
                hazard_match = re.search(r'(flood|fire|terrorist|chemical|earthquake|evacuation)', llm_response.lower())
                hazard_type = hazard_match.group(1) if hazard_match else "general_evacuation"
                
                # Execute the simulation tool
                result = await self.tool_registry.execute_tool(
                    "run_simulation",
                    {"city": city, "hazard_type": hazard_type}
                )
                
                return result
            
            # Check for status check patterns
            status_pattern = r'(?:check|get|show)\s+(?:status|progress)\s+(?:of\s+)?(?:simulation\s+)?([a-f0-9-]+)'
            match = re.search(status_pattern, llm_response.lower())
            
            if match:
                run_id = match.group(1)
                result = await self.tool_registry.execute_tool(
                    "get_simulation_status",
                    {"run_id": run_id}
                )
                return result
            
            # Check for list simulations patterns
            if re.search(r'(?:list|show|get)\s+(?:recent\s+)?simulations', llm_response.lower()):
                result = await self.tool_registry.execute_tool(
                    "list_recent_simulations",
                    {"limit": 5}
                )
                return result
            
            # Check for borough status patterns
            borough_pattern = r'(?:status|check)\s+(?:of\s+)?(\w+)\s+(?:borough)?'
            match = re.search(borough_pattern, llm_response.lower())
            
            if match and any(word in llm_response.lower() for word in ['borough', 'area', 'district']):
                borough = match.group(1).title()
                result = await self.tool_registry.execute_tool(
                    "get_borough_status",
                    {"borough_name": borough}
                )
                return result
            
            return None
            
        except Exception as e:
            logger.error(f"Tool handling failed: {e}", exc_info=True)
            return None
    
    def _format_tool_result(self, tool_result: Dict[str, Any]) -> str:
        """Format tool execution result for display to the user."""
        if not tool_result.get('success'):
            return f"❌ Error: {tool_result.get('error', 'Unknown error occurred')}"
        
        message = tool_result.get('message', '')
        
        # Add additional details based on the result
        if 'run_id' in tool_result:
            message += f"\n\n📋 **Run ID**: `{tool_result['run_id']}`"
            message += f"\n🏙️ **City**: {tool_result.get('city', 'Unknown')}"
            message += f"\n⚠️ **Hazard**: {tool_result.get('hazard_type', 'Unknown')}"
            if 'estimated_completion' in tool_result:
                message += f"\n⏱️ **Estimated completion**: {tool_result['estimated_completion']}"
            message += "\n\n💡 You can monitor progress in the Results tab or ask me for a status update using the Run ID."
        
        elif 'status' in tool_result:
            message += f"\n\n📊 **Status**: {tool_result['status']}"
            if tool_result.get('completed'):
                message += " ✅ (Completed)"
            else:
                message += " ⏳ (In Progress)"
        
        elif 'simulations' in tool_result:
            sims = tool_result['simulations']
            if sims:
                message += "\n\n📋 **Recent Simulations**:"
                for sim in sims[:5]:
                    message += f"\n• **{sim.get('run_id')}** - {sim.get('city')} ({sim.get('status')})"
            else:
                message += "\n\nNo recent simulations found."
        
        elif 'borough' in tool_result:
            message += f"\n\n🏙️ **Borough**: {tool_result['borough']}"
            message += f"\n🚦 **Status**: {tool_result.get('status', 'unknown').upper()}"
            if 'clearance_time' in tool_result:
                message += f"\n⏱️ **Clearance Time**: {tool_result['clearance_time']} minutes"
            if 'fairness_index' in tool_result:
                message += f"\n⚖️ **Fairness**: {tool_result['fairness_index']:.2f}"
            if 'robustness' in tool_result:
                message += f"\n💪 **Robustness**: {tool_result['robustness']:.2f}"
        
        return message

    def _mock_chat_response(self, role: str, question: str, plan_context: Dict = None) -> str:
        """Mock chat response when LLM is not available."""
        if plan_context is None:
            plan_context = {}

        # Check for strategy request
        question_lower = question.lower()
        if 'generate scenario' in question_lower or 'generate strategy' in question_lower or 'full strategy' in question_lower:
            strategy = plan_context.get('comprehensive_strategy', {})
            if not strategy:
                return "⚠️ Comprehensive strategy not available yet. The system is still analysing the simulation data."

            # Return simplified strategy overview
            depts = strategy.get('departments', {}).get('departments_list', [])
            personnel = strategy.get('personnel', {}).get('assignments', [])

            response = f"## Strategy Overview\n\n"
            response += f"**Departments:** {len(depts)} government departments involved\n"
            response += f"**Personnel:** {len(personnel)} key personnel assigned\n\n"
            response += f"Type 'generate strategy' to see the full detailed plan with all departments, personnel, and action steps."

            return response

        role_responses = {
            'PM': "As Prime Minister, your priority is coordinating overall response and communicating with the public. "
                  "Focus on strategic decisions and inter-agency coordination.\n\n"
                  "💡 Tip: Ask me to 'generate strategy' to see the full evacuation plan with all departments and personnel.",
            'DPM': "As Deputy PM, support the PM and manage specific operational aspects. "
                   "Coordinate between different government departments.\n\n"
                   "💡 Tip: Ask me to 'generate strategy' to see department coordination structure.",
            'Comms': "As Communications lead, prepare public statements and coordinate messaging across channels. "
                     "Focus on clear, calm communication to prevent panic.\n\n"
                     "💡 Tip: Ask me to 'generate strategy' to see the communication plan and timeline.",
            'Chief of Staff': "Coordinate execution of emergency plans across teams. "
                             "Ensure all departments are aligned and resources are deployed efficiently.\n\n"
                             "💡 Tip: Ask me to 'generate strategy' to see resource deployment and personnel assignments.",
            'CE': "As Chief Executive, oversee operational implementation. "
                  "Ensure emergency services and resources are properly allocated.\n\n"
                  "💡 Tip: Ask me to 'generate strategy' to see the operational timeline and resource plan.",
            'Permanent Secretary': "Provide departmental expertise and ensure compliance with protocols. "
                                  "Coordinate long-term recovery planning.\n\n"
                                  "💡 Tip: Ask me to 'generate strategy' to see contingency plans and protocols."
        }

        return role_responses.get(role, "I'll help coordinate the emergency response for your role.\n\n"
                                       "💡 Tip: Ask me to 'generate strategy' to see the comprehensive evacuation plan.")
