"""
Planner Agent for London Evacuation Planning Tool.

This agent generates evacuation scenarios based on user intent and constraints,
ensuring coverage and avoiding duplicates.
"""

import hashlib
import random
from typing import List, Dict, Any, Set, Optional
import structlog

from models.schemas import UserIntent, ScenarioConfig, PolygonCordon, CapacityChange, ProtectedCorridor, StagedEgress
from core.config import get_settings

logger = structlog.get_logger(__name__)


class PlannerAgent:
    """Agent responsible for generating evacuation scenarios."""

    def __init__(self):
        self.settings = get_settings()
        self._scenario_cache: Set[str] = set()  # Cache of scenario hashes to avoid duplicates

    async def generate_scenarios(self, intent: UserIntent, city: str = "london") -> List[ScenarioConfig]:
        """Generate evacuation scenarios based on user intent for specified city."""
        logger.info("Planner agent starting scenario generation", 
                   objective=intent.objective,
                   city=city,
                   max_scenarios=intent.constraints.max_scenarios)

        scenarios = []
        attempts = 0
        max_attempts = intent.constraints.max_scenarios * 3  # Allow some failed attempts

        while len(scenarios) < intent.constraints.max_scenarios and attempts < max_attempts:
            attempts += 1
            
            try:
                # Generate a scenario for the specified city
                scenario = await self._generate_single_scenario(intent, len(scenarios), city)
                
                # Check for duplicates
                scenario_hash = self._calculate_scenario_hash(scenario)
                if scenario_hash in self._scenario_cache:
                    logger.debug("Duplicate scenario generated, skipping")
                    continue
                
                # Validate scenario
                if await self._validate_scenario(scenario, intent):
                    scenarios.append(scenario)
                    self._scenario_cache.add(scenario_hash)
                    logger.debug("Generated scenario", 
                               scenario_id=scenario.id,
                               city=city,
                               total_scenarios=len(scenarios))
                else:
                    logger.debug("Scenario failed validation", scenario_id=scenario.id)
                    
            except Exception as e:
                logger.error("Failed to generate scenario", 
                           attempt=attempts, 
                           city=city,
                           error=str(e))
                continue

        if len(scenarios) < intent.constraints.max_scenarios:
            logger.warning("Could not generate requested number of scenarios",
                         requested=intent.constraints.max_scenarios,
                         generated=len(scenarios),
                         city=city)

        logger.info("Planner agent completed scenario generation",
                   scenarios_generated=len(scenarios),
                   city=city,
                   attempts=attempts)

        return scenarios

    async def _generate_single_scenario(self, intent: UserIntent, scenario_index: int, city: str = "london") -> ScenarioConfig:
        """Generate a single evacuation scenario for specified city."""
        scenario_id = f"{city}_{intent.objective.lower().replace(' ', '_')}_v{scenario_index + 1}"
        
        # Start with base scenario
        scenario = ScenarioConfig(
            id=scenario_id,
            city=city,  # Use the specified city
            seed=random.randint(1, 10000),
            closures=[],
            capacity_changes=[],
            protected_corridors=[],
            staged_egress=[],
            notes=""
        )

        # Apply user hypotheses
        await self._apply_hypotheses(scenario, intent.hypotheses)

        # Generate additional scenario elements based on objective
        await self._generate_scenario_elements(scenario, intent)

        # Ensure protected POIs are accessible
        await self._ensure_poi_protection(scenario, intent.constraints.must_protect_pois)

        return scenario

    async def _apply_hypotheses(self, scenario: ScenarioConfig, hypotheses: List[str]) -> None:
        """Apply user hypotheses to the scenario."""
        for hypothesis in hypotheses:
            hypothesis_lower = hypothesis.lower()
            
            if "westminster cordon" in hypothesis_lower:
                # Extract duration if specified
                duration = 120  # Default 2 hours
                if "1h" in hypothesis_lower:
                    duration = 60
                elif "3h" in hypothesis_lower:
                    duration = 180
                elif "2h" in hypothesis_lower:
                    duration = 120

                closure = PolygonCordon(
                    type="polygon_cordon",
                    area="westminster",
                    start_minute=0,
                    end_minute=duration
                )
                scenario.closures.append(closure)
                scenario.notes += f"Westminster cordon applied for {duration} minutes. "

            elif "thames bridge" in hypothesis_lower or "bridge" in hypothesis_lower:
                # Reduce bridge capacity
                multiplier = 0.5
                if "closed" in hypothesis_lower:
                    multiplier = 0.01  # Almost closed but > 0
                elif "partial" in hypothesis_lower:
                    multiplier = 0.3

                change = CapacityChange(
                    edge_selector="is_bridge==true",
                    multiplier=multiplier
                )
                scenario.capacity_changes.append(change)
                scenario.notes += f"Thames bridges capacity reduced to {int(multiplier*100)}%. "

            elif "staged egress" in hypothesis_lower and "wembley" in hypothesis_lower:
                egress = StagedEgress(
                    area="wembley",
                    start_minute=15,
                    release_rate="25%/15min"
                )
                scenario.staged_egress.append(egress)
                scenario.notes += "Staged egress at Wembley implemented. "

    async def _generate_scenario_elements(self, scenario: ScenarioConfig, intent: UserIntent) -> None:
        """Generate additional scenario elements based on optimization objective."""
        objective_lower = intent.objective.lower()

        # Generate elements based on objective focus
        if "clearance" in objective_lower and "time" in objective_lower:
            # Focus on reducing clearance time
            await self._add_clearance_optimizations(scenario)
        
        if "fairness" in objective_lower:
            # Focus on improving fairness
            await self._add_fairness_optimizations(scenario)
        
        if "robustness" in objective_lower:
            # Focus on improving robustness
            await self._add_robustness_optimizations(scenario)

        # Add some randomization for variety
        if random.random() < 0.3:  # 30% chance
            await self._add_random_elements(scenario)

    async def _add_clearance_optimizations(self, scenario: ScenarioConfig) -> None:
        """Add elements that optimize for clearance time."""
        # Increase capacity on major routes
        major_route_boost = CapacityChange(
            edge_selector="primary",
            multiplier=1.5
        )
        scenario.capacity_changes.append(major_route_boost)
        scenario.notes += "Major routes capacity increased for faster clearance. "

    async def _add_fairness_optimizations(self, scenario: ScenarioConfig) -> None:
        """Add elements that optimize for fairness."""
        # Implement staged egress to prevent bottlenecks
        areas = ["camden", "islington", "southwark"]
        area = random.choice(areas)
        
        egress = StagedEgress(
            area=area,
            start_minute=random.randint(10, 30),
            release_rate="20%/10min"
        )
        scenario.staged_egress.append(egress)
        scenario.notes += f"Staged egress in {area} for fairness. "

    async def _add_robustness_optimizations(self, scenario: ScenarioConfig) -> None:
        """Add elements that optimize for robustness."""
        # Create redundant routes
        corridor = ProtectedCorridor(
            name="emergency_corridor",
            rule="increase_capacity",
            multiplier=2.0
        )
        scenario.protected_corridors.append(corridor)
        scenario.notes += "Emergency corridor protected for robustness. "

    async def _add_random_elements(self, scenario: ScenarioConfig) -> None:
        """Add random scenario elements for variety."""
        element_type = random.choice(["closure", "capacity_change", "staged_egress"])
        
        if element_type == "closure":
            areas = ["camden", "islington", "hackney"]
            area = random.choice(areas)
            
            closure = PolygonCordon(
                type="polygon_cordon",
                area=area,
                start_minute=random.randint(0, 60),
                end_minute=random.randint(90, 180)
            )
            scenario.closures.append(closure)
            scenario.notes += f"Random closure in {area}. "
            
        elif element_type == "capacity_change":
            selectors = ["secondary", "tertiary", "residential"]
            selector = random.choice(selectors)
            multiplier = random.uniform(0.7, 1.3)
            
            change = CapacityChange(
                edge_selector=selector,
                multiplier=multiplier
            )
            scenario.capacity_changes.append(change)
            scenario.notes += f"Random capacity change on {selector} roads. "

    async def _ensure_poi_protection(self, scenario: ScenarioConfig, protected_pois: List[str]) -> None:
        """Ensure protected POIs remain accessible."""
        for poi in protected_pois:
            # Add protected corridor for each POI
            corridor_name = f"{poi.lower()}_access"
            
            corridor = ProtectedCorridor(
                name=corridor_name,
                rule="increase_capacity",
                multiplier=1.5
            )
            scenario.protected_corridors.append(corridor)
            
        if protected_pois:
            scenario.notes += f"Protected access to: {', '.join(protected_pois)}. "

    async def _validate_scenario(self, scenario: ScenarioConfig, intent: UserIntent) -> bool:
        """Validate that a scenario meets basic requirements."""
        try:
            # Check that scenario ID is unique and valid
            if not scenario.id or len(scenario.id) < 3:
                return False

            # Check that protected POIs have corresponding corridors
            for poi in intent.constraints.must_protect_pois:
                has_protection = any(
                    poi.lower() in corridor.name.lower() 
                    for corridor in scenario.protected_corridors
                )
                if not has_protection:
                    logger.debug("Scenario missing POI protection", 
                               scenario_id=scenario.id, 
                               poi=poi)
                    return False

            # Check that scenario doesn't have conflicting elements
            # (e.g., closing and protecting the same area)
            closed_areas = {closure.area.lower() for closure in scenario.closures}
            for corridor in scenario.protected_corridors:
                if any(area in corridor.name.lower() for area in closed_areas):
                    logger.debug("Scenario has conflicting closure and protection",
                               scenario_id=scenario.id)
                    return False

            # Check capacity changes are reasonable
            for change in scenario.capacity_changes:
                if change.multiplier <= 0 or change.multiplier > 5.0:
                    logger.debug("Scenario has unreasonable capacity change",
                               scenario_id=scenario.id,
                               multiplier=change.multiplier)
                    return False

            return True

        except Exception as e:
            logger.error("Scenario validation failed", 
                        scenario_id=scenario.id, 
                        error=str(e))
            return False

    def _calculate_scenario_hash(self, scenario: ScenarioConfig) -> str:
        """Calculate hash of scenario for duplicate detection."""
        # Create a canonical representation
        canonical = {
            'closures': sorted([
                (c.area, c.start_minute, c.end_minute) 
                for c in scenario.closures
            ]),
            'capacity_changes': sorted([
                (c.edge_selector, c.multiplier) 
                for c in scenario.capacity_changes
            ]),
            'protected_corridors': sorted([
                (c.name, c.rule, c.multiplier) 
                for c in scenario.protected_corridors
            ]),
            'staged_egress': sorted([
                (s.area, s.start_minute, s.release_rate) 
                for s in scenario.staged_egress
            ])
        }
        
        canonical_str = str(canonical)
        return hashlib.md5(canonical_str.encode()).hexdigest()

    async def replan_after_failure(self, intent: UserIntent, 
                                  failed_results: List[Dict[str, Any]]) -> List[ScenarioConfig]:
        """Generate new scenarios after validation failures."""
        logger.info("Planner agent starting re-planning after failures",
                   failed_results_count=len(failed_results))

        # Analyze failure reasons
        failure_reasons = self._analyze_failures(failed_results)
        
        # Generate targeted scenarios to address failures
        scenarios = []
        for reason in failure_reasons:
            try:
                scenario = await self._generate_targeted_scenario(intent, reason, len(scenarios))
                if scenario and await self._validate_scenario(scenario, intent):
                    scenarios.append(scenario)
            except Exception as e:
                logger.error("Failed to generate targeted scenario", 
                           reason=reason, 
                           error=str(e))

        logger.info("Planner agent completed re-planning",
                   new_scenarios=len(scenarios))

        return scenarios

    def _analyze_failures(self, failed_results: List[Dict[str, Any]]) -> List[str]:
        """Analyze failure reasons to inform re-planning."""
        reasons = []
        
        for result in failed_results:
            if result.get('status') == 'failed':
                error_msg = result.get('error_message', '').lower()
                
                if 'poi' in error_msg or 'unreachable' in error_msg:
                    reasons.append('poi_accessibility')
                elif 'capacity' in error_msg:
                    reasons.append('insufficient_capacity')
                elif 'timeout' in error_msg:
                    reasons.append('simulation_timeout')
                else:
                    reasons.append('general_failure')
        
        return list(set(reasons))  # Remove duplicates

    async def _generate_targeted_scenario(self, intent: UserIntent, 
                                        failure_reason: str, 
                                        scenario_index: int) -> Optional[ScenarioConfig]:
        """Generate a scenario targeted at addressing a specific failure."""
        scenario_id = f"recovery_{failure_reason}_v{scenario_index + 1}"
        
        scenario = ScenarioConfig(
            id=scenario_id,
            city="london",
            seed=random.randint(1, 10000),
            closures=[],
            capacity_changes=[],
            protected_corridors=[],
            staged_egress=[],
            notes=f"Generated to address {failure_reason}. "
        )

        if failure_reason == 'poi_accessibility':
            # Focus heavily on POI protection
            for poi in intent.constraints.must_protect_pois:
                corridor = ProtectedCorridor(
                    name=f"{poi.lower()}_priority_access",
                    rule="increase_capacity",
                    multiplier=2.5  # Higher multiplier
                )
                scenario.protected_corridors.append(corridor)
            
            scenario.notes += "Enhanced POI protection. "

        elif failure_reason == 'insufficient_capacity':
            # Add capacity boosts
            change = CapacityChange(
                edge_selector="primary",
                multiplier=2.0
            )
            scenario.capacity_changes.append(change)
            scenario.notes += "Enhanced capacity on primary routes. "

        elif failure_reason == 'simulation_timeout':
            # Create simpler scenario
            scenario.notes += "Simplified for faster simulation. "

        return scenario
