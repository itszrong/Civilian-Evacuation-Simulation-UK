"""
Tests for agents.planner_agent module.
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, patch
from typing import List

from agents.planner_agent import PlannerAgent

pytestmark = pytest.mark.asyncio
from models.schemas import (
    UserIntent, ScenarioConfig, ScenarioConstraints, UserPreferences,
    PolygonCordon, CapacityChange, ProtectedCorridor, StagedEgress
)


class TestPlannerAgent:
    """Test the PlannerAgent class."""

    def setup_method(self):
        """Set up test environment."""
        with patch('agents.planner_agent.get_settings') as mock_settings:
            mock_settings_instance = Mock()
            mock_settings.return_value = mock_settings_instance
            self.agent = PlannerAgent()

        # Create sample user intent
        self.sample_intent = UserIntent(
            objective="Optimize evacuation for central London",
            city="london",
            constraints=ScenarioConstraints(
                max_scenarios=5,
                must_protect_pois=["Westminster", "London Bridge"]
            ),
            hypotheses=[
                "Westminster cordon needed for 2h",
                "Thames bridges should have reduced capacity"
            ],
            preferences=UserPreferences(
                fairness_weight=0.3,
                clearance_weight=0.5,
                robustness_weight=0.2
            )
        )

    async def test_initialization(self):
        """Test PlannerAgent initialization."""
        with patch('agents.planner_agent.get_settings'):
            agent = PlannerAgent()
            assert agent is not None
            assert isinstance(agent._scenario_cache, set)

    async def test_generate_scenarios_basic(self):
        """Test basic scenario generation."""
        scenarios = await self.agent.generate_scenarios(self.sample_intent, "london")

        assert len(scenarios) == 5
        assert all(isinstance(s, ScenarioConfig) for s in scenarios)
        assert all(s.city == "london" for s in scenarios)
        assert all(s.id for s in scenarios)

    async def test_generate_scenarios_poi_protection(self):
        """Test that generated scenarios protect required POIs."""
        scenarios = await self.agent.generate_scenarios(self.sample_intent, "london")

        for scenario in scenarios:
            # Check that each protected POI has a corresponding corridor
            for poi in self.sample_intent.constraints.must_protect_pois:
                has_protection = any(
                    poi.lower() in corridor.name.lower()
                    for corridor in scenario.protected_corridors
                )
                assert has_protection, f"Scenario {scenario.id} missing protection for {poi}"

    async def test_generate_scenarios_applies_hypotheses(self):
        """Test that hypotheses are applied to scenarios."""
        scenarios = await self.agent.generate_scenarios(self.sample_intent, "london")

        # At least some scenarios should have Westminster cordon
        has_westminster = any(
            any(closure.area == "westminster" for closure in scenario.closures)
            for scenario in scenarios
        )
        assert has_westminster, "No scenarios have Westminster cordon"

        # At least some scenarios should have bridge capacity changes
        has_bridge_changes = any(
            any("bridge" in change.edge_selector.lower() for change in scenario.capacity_changes)
            for scenario in scenarios
        )
        assert has_bridge_changes, "No scenarios have bridge capacity changes"

    async def test_generate_scenarios_no_duplicates(self):
        """Test that generated scenarios are unique."""
        scenarios = await self.agent.generate_scenarios(self.sample_intent, "london")

        # Calculate hashes for all scenarios
        hashes = [self.agent._calculate_scenario_hash(s) for s in scenarios]

        # All hashes should be unique
        assert len(hashes) == len(set(hashes)), "Duplicate scenarios were generated"

    async def test_generate_scenarios_different_cities(self):
        """Test scenario generation for different cities."""
        # Generate for London
        london_scenarios = await self.agent.generate_scenarios(self.sample_intent, "london")
        assert all(s.city == "london" for s in london_scenarios)

        # Clear cache to allow generating for another city
        self.agent._scenario_cache.clear()

        # Generate for another city
        nyc_scenarios = await self.agent.generate_scenarios(self.sample_intent, "new_york")
        assert all(s.city == "new_york" for s in nyc_scenarios)

    async def test_apply_hypotheses_westminster_cordon(self):
        """Test applying Westminster cordon hypothesis."""
        scenario = ScenarioConfig(
            id="test",
            city="london",
            seed=42,
            closures=[],
            capacity_changes=[],
            protected_corridors=[],
            staged_egress=[],
            notes=""
        )

        hypotheses = ["Westminster cordon needed for 2h"]
        await self.agent._apply_hypotheses(scenario, hypotheses)

        assert len(scenario.closures) == 1
        assert scenario.closures[0].area == "westminster"
        assert scenario.closures[0].end_minute == 120  # 2 hours

    async def test_apply_hypotheses_bridge_closure(self):
        """Test applying bridge capacity reduction hypothesis."""
        scenario = ScenarioConfig(
            id="test",
            city="london",
            seed=42,
            closures=[],
            capacity_changes=[],
            protected_corridors=[],
            staged_egress=[],
            notes=""
        )

        hypotheses = ["Thames bridges should be closed"]
        await self.agent._apply_hypotheses(scenario, hypotheses)

        assert len(scenario.capacity_changes) >= 1
        assert any("bridge" in change.edge_selector.lower() for change in scenario.capacity_changes)
        assert scenario.capacity_changes[0].multiplier < 0.5

    async def test_apply_hypotheses_staged_egress(self):
        """Test applying staged egress hypothesis."""
        scenario = ScenarioConfig(
            id="test",
            city="london",
            seed=42,
            closures=[],
            capacity_changes=[],
            protected_corridors=[],
            staged_egress=[],
            notes=""
        )

        hypotheses = ["Staged egress at Wembley"]
        await self.agent._apply_hypotheses(scenario, hypotheses)

        assert len(scenario.staged_egress) == 1
        assert scenario.staged_egress[0].area == "wembley"

    async def test_add_clearance_optimizations(self):
        """Test adding clearance time optimizations."""
        scenario = ScenarioConfig(
            id="test",
            city="london",
            seed=42,
            closures=[],
            capacity_changes=[],
            protected_corridors=[],
            staged_egress=[],
            notes=""
        )

        await self.agent._add_clearance_optimizations(scenario)

        assert len(scenario.capacity_changes) > 0
        # Should have capacity increase for major routes
        assert any(change.multiplier > 1.0 for change in scenario.capacity_changes)

    async def test_add_fairness_optimizations(self):
        """Test adding fairness optimizations."""
        scenario = ScenarioConfig(
            id="test",
            city="london",
            seed=42,
            closures=[],
            capacity_changes=[],
            protected_corridors=[],
            staged_egress=[],
            notes=""
        )

        await self.agent._add_fairness_optimizations(scenario)

        assert len(scenario.staged_egress) > 0
        # Should have staged egress for fairness
        assert scenario.staged_egress[0].area in ["camden", "islington", "southwark"]

    async def test_add_robustness_optimizations(self):
        """Test adding robustness optimizations."""
        scenario = ScenarioConfig(
            id="test",
            city="london",
            seed=42,
            closures=[],
            capacity_changes=[],
            protected_corridors=[],
            staged_egress=[],
            notes=""
        )

        await self.agent._add_robustness_optimizations(scenario)

        assert len(scenario.protected_corridors) > 0
        # Should have emergency corridor
        assert any("emergency" in corridor.name.lower() for corridor in scenario.protected_corridors)

    async def test_ensure_poi_protection(self):
        """Test ensuring POI protection."""
        scenario = ScenarioConfig(
            id="test",
            city="london",
            seed=42,
            closures=[],
            capacity_changes=[],
            protected_corridors=[],
            staged_egress=[],
            notes=""
        )

        pois = ["Westminster", "London Bridge"]
        await self.agent._ensure_poi_protection(scenario, pois)

        assert len(scenario.protected_corridors) == 2
        for poi in pois:
            has_corridor = any(
                poi.lower() in corridor.name.lower()
                for corridor in scenario.protected_corridors
            )
            assert has_corridor, f"Missing corridor for {poi}"

    async def test_validate_scenario_success(self):
        """Test successful scenario validation."""
        scenario = ScenarioConfig(
            id="valid_scenario",
            city="london",
            seed=42,
            closures=[
                PolygonCordon(
                    type="polygon_cordon",
                    area="westminster",
                    start_minute=0,
                    end_minute=60
                )
            ],
            capacity_changes=[
                CapacityChange(
                    edge_selector="primary",
                    multiplier=1.5
                )
            ],
            protected_corridors=[
                ProtectedCorridor(
                    name="westminster_access",
                    rule="increase_capacity",
                    multiplier=1.5
                )
            ],
            staged_egress=[],
            notes="Valid test scenario"
        )

        intent = UserIntent(
            objective="Test",
            constraints=ScenarioConstraints(must_protect_pois=["Westminster"]),
            preferences=UserPreferences()
        )

        result = await self.agent._validate_scenario(scenario, intent)
        assert result is True

    async def test_validate_scenario_missing_poi_protection(self):
        """Test validation failure when POI protection is missing."""
        scenario = ScenarioConfig(
            id="invalid_scenario",
            city="london",
            seed=42,
            closures=[],
            capacity_changes=[],
            protected_corridors=[],
            staged_egress=[],
            notes=""
        )

        intent = UserIntent(
            objective="Test",
            constraints=ScenarioConstraints(must_protect_pois=["Westminster"]),
            preferences=UserPreferences()
        )

        result = await self.agent._validate_scenario(scenario, intent)
        assert result is False

    async def test_validate_scenario_conflicting_elements(self):
        """Test validation failure for conflicting closure and protection."""
        scenario = ScenarioConfig(
            id="conflicting_scenario",
            city="london",
            seed=42,
            closures=[
                PolygonCordon(
                    type="polygon_cordon",
                    area="westminster",
                    start_minute=0,
                    end_minute=60
                )
            ],
            capacity_changes=[],
            protected_corridors=[
                ProtectedCorridor(
                    name="westminster_access",
                    rule="increase_capacity",
                    multiplier=1.5
                )
            ],
            staged_egress=[],
            notes=""
        )

        intent = UserIntent(
            objective="Test",
            constraints=ScenarioConstraints(must_protect_pois=[]),
            preferences=UserPreferences()
        )

        result = await self.agent._validate_scenario(scenario, intent)
        assert result is False

    async def test_validate_scenario_unreasonable_capacity(self):
        """Test validation failure for unreasonable capacity changes."""
        scenario = ScenarioConfig(
            id="unreasonable_scenario",
            city="london",
            seed=42,
            closures=[],
            capacity_changes=[
                CapacityChange(
                    edge_selector="primary",
                    multiplier=10.0  # Too high
                )
            ],
            protected_corridors=[],
            staged_egress=[],
            notes=""
        )

        intent = UserIntent(
            objective="Test",
            constraints=ScenarioConstraints(must_protect_pois=[]),
            preferences=UserPreferences()
        )

        result = await self.agent._validate_scenario(scenario, intent)
        assert result is False

    async def test_calculate_scenario_hash_identical(self):
        """Test that identical scenarios produce the same hash."""
        scenario1 = ScenarioConfig(
            id="test1",
            city="london",
            seed=42,
            closures=[
                PolygonCordon(type="polygon_cordon", area="westminster", start_minute=0, end_minute=60)
            ],
            capacity_changes=[
                CapacityChange(edge_selector="primary", multiplier=1.5)
            ],
            protected_corridors=[],
            staged_egress=[],
            notes="Test 1"
        )

        scenario2 = ScenarioConfig(
            id="test2",
            city="london",
            seed=99,
            closures=[
                PolygonCordon(type="polygon_cordon", area="westminster", start_minute=0, end_minute=60)
            ],
            capacity_changes=[
                CapacityChange(edge_selector="primary", multiplier=1.5)
            ],
            protected_corridors=[],
            staged_egress=[],
            notes="Test 2"
        )

        hash1 = self.agent._calculate_scenario_hash(scenario1)
        hash2 = self.agent._calculate_scenario_hash(scenario2)

        # Even though IDs, seeds, and notes differ, hashes should be the same
        assert hash1 == hash2

    async def test_calculate_scenario_hash_different(self):
        """Test that different scenarios produce different hashes."""
        scenario1 = ScenarioConfig(
            id="test1",
            city="london",
            seed=42,
            closures=[
                PolygonCordon(type="polygon_cordon", area="westminster", start_minute=0, end_minute=60)
            ],
            capacity_changes=[],
            protected_corridors=[],
            staged_egress=[],
            notes=""
        )

        scenario2 = ScenarioConfig(
            id="test2",
            city="london",
            seed=42,
            closures=[
                PolygonCordon(type="polygon_cordon", area="camden", start_minute=0, end_minute=60)
            ],
            capacity_changes=[],
            protected_corridors=[],
            staged_egress=[],
            notes=""
        )

        hash1 = self.agent._calculate_scenario_hash(scenario1)
        hash2 = self.agent._calculate_scenario_hash(scenario2)

        assert hash1 != hash2

    async def test_replan_after_failure(self):
        """Test replanning after validation failures."""
        failed_results = [
            {
                'status': 'failed',
                'error_message': 'POI unreachable: Westminster'
            },
            {
                'status': 'failed',
                'error_message': 'Insufficient capacity on primary routes'
            }
        ]

        intent = UserIntent(
            objective="Recovery planning",
            constraints=ScenarioConstraints(must_protect_pois=["Westminster"]),
            preferences=UserPreferences()
        )

        scenarios = await self.agent.replan_after_failure(intent, failed_results)

        # Should generate targeted scenarios
        assert len(scenarios) > 0
        assert all(isinstance(s, ScenarioConfig) for s in scenarios)

    async def test_analyze_failures_poi_accessibility(self):
        """Test failure analysis for POI accessibility."""
        failed_results = [
            {
                'status': 'failed',
                'error_message': 'POI unreachable: Westminster'
            }
        ]

        reasons = self.agent._analyze_failures(failed_results)

        assert 'poi_accessibility' in reasons

    async def test_analyze_failures_capacity(self):
        """Test failure analysis for capacity issues."""
        failed_results = [
            {
                'status': 'failed',
                'error_message': 'Insufficient capacity on routes'
            }
        ]

        reasons = self.agent._analyze_failures(failed_results)

        assert 'insufficient_capacity' in reasons

    async def test_generate_targeted_scenario_poi_accessibility(self):
        """Test generating targeted scenario for POI accessibility."""
        intent = UserIntent(
            objective="Test",
            constraints=ScenarioConstraints(must_protect_pois=["Westminster", "London Bridge"]),
            preferences=UserPreferences()
        )

        scenario = await self.agent._generate_targeted_scenario(
            intent,
            'poi_accessibility',
            0
        )

        assert scenario is not None
        # Should have enhanced POI protection
        assert len(scenario.protected_corridors) >= 2
        assert any(corridor.multiplier >= 2.0 for corridor in scenario.protected_corridors)

    async def test_generate_targeted_scenario_insufficient_capacity(self):
        """Test generating targeted scenario for capacity issues."""
        intent = UserIntent(
            objective="Test",
            constraints=ScenarioConstraints(must_protect_pois=[]),
            preferences=UserPreferences()
        )

        scenario = await self.agent._generate_targeted_scenario(
            intent,
            'insufficient_capacity',
            0
        )

        assert scenario is not None
        # Should have capacity boosts
        assert len(scenario.capacity_changes) > 0
        assert any(change.multiplier >= 2.0 for change in scenario.capacity_changes)


@pytest.mark.unit
class TestPlannerAgentEdgeCases:
    """Test edge cases and error conditions."""

    def setup_method(self):
        """Set up test environment."""
        with patch('agents.planner_agent.get_settings'):
            self.agent = PlannerAgent()

    async def test_generate_scenarios_max_attempts(self):
        """Test that generation stops after max attempts."""
        # Create intent with very restrictive constraints
        intent = UserIntent(
            objective="Test",
            constraints=ScenarioConstraints(
                max_scenarios=100,  # Request many scenarios
                must_protect_pois=["POI1", "POI2", "POI3"]
            ),
            preferences=UserPreferences()
        )

        scenarios = await self.agent.generate_scenarios(intent, "london")

        # Should not hang forever, should return fewer than requested
        assert len(scenarios) < 100

    async def test_generate_scenarios_empty_hypotheses(self):
        """Test scenario generation with empty hypotheses."""
        intent = UserIntent(
            objective="Test",
            constraints=ScenarioConstraints(max_scenarios=2, must_protect_pois=[]),
            hypotheses=[],
            preferences=UserPreferences()
        )

        scenarios = await self.agent.generate_scenarios(intent, "london")

        assert len(scenarios) == 2

    async def test_validate_scenario_empty_id(self):
        """Test validation with empty scenario ID."""
        scenario = ScenarioConfig(
            id="",
            city="london",
            seed=42,
            closures=[],
            capacity_changes=[],
            protected_corridors=[],
            staged_egress=[],
            notes=""
        )

        intent = UserIntent(
            objective="Test",
            constraints=ScenarioConstraints(must_protect_pois=[]),
            preferences=UserPreferences()
        )

        result = await self.agent._validate_scenario(scenario, intent)
        assert result is False

    async def test_generate_scenarios_concurrent_cache(self):
        """Test that scenario cache works correctly."""
        intent = UserIntent(
            objective="Test",
            constraints=ScenarioConstraints(max_scenarios=3, must_protect_pois=[]),
            preferences=UserPreferences()
        )

        # Generate first batch
        scenarios1 = await self.agent.generate_scenarios(intent, "london")

        # Generate second batch (should not have duplicates from first batch)
        scenarios2 = await self.agent.generate_scenarios(intent, "london")

        # Calculate all hashes
        hashes1 = [self.agent._calculate_scenario_hash(s) for s in scenarios1]
        hashes2 = [self.agent._calculate_scenario_hash(s) for s in scenarios2]

        # No overlap between batches
        assert len(set(hashes1) & set(hashes2)) == 0
