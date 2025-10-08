"""
Tests for agents.judge_agent module.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import List

from agents.judge_agent import JudgeAgent
from models.schemas import (
    ScenarioResult, UserPreferences, UserIntent, JudgeResult,
    ScenarioRanking, TaskStatus, SimulationMetrics, ScenarioConstraints
)


class TestJudgeAgent:
    """Test the JudgeAgent class."""
    
    def setup_method(self):
        """Set up test environment."""
        self.agent = JudgeAgent()
        
        # Create sample data
        self.sample_preferences = UserPreferences(
            fairness_weight=0.3,
            clearance_weight=0.5,
            robustness_weight=0.2
        )
        
        self.sample_intent = UserIntent(
            objective="Test evacuation planning",
            constraints=ScenarioConstraints(max_scenarios=5),
            preferences=self.sample_preferences
        )
        
        # Create sample scenario results
        self.sample_results = [
            ScenarioResult(
                scenario_id="scenario_001",
                metrics=SimulationMetrics(
                    clearance_time=1800.0,  # 30 minutes
                    max_queue=150.0,
                    fairness_index=0.85,
                    robustness=0.75
                ),
                status=TaskStatus.COMPLETED,
                duration_ms=5000
            ),
            ScenarioResult(
                scenario_id="scenario_002",
                metrics=SimulationMetrics(
                    clearance_time=2100.0,  # 35 minutes
                    max_queue=120.0,
                    fairness_index=0.90,
                    robustness=0.80
                ),
                status=TaskStatus.COMPLETED,
                duration_ms=5500
            ),
            ScenarioResult(
                scenario_id="scenario_003",
                metrics=SimulationMetrics(
                    clearance_time=1500.0,  # 25 minutes
                    max_queue=200.0,
                    fairness_index=0.70,
                    robustness=0.85
                ),
                status=TaskStatus.COMPLETED,
                duration_ms=4500
            )
        ]
    
    def test_initialization(self):
        """Test JudgeAgent initialization."""
        agent = JudgeAgent()
        assert agent is not None
    
    async def test_rank_scenarios_success(self):
        """Test successful scenario ranking."""
        result = await self.agent.rank_scenarios(
            self.sample_results,
            self.sample_preferences,
            self.sample_intent
        )
        
        assert isinstance(result, JudgeResult)
        assert len(result.ranking) == 3
        assert result.validation_passed is True
        assert result.best_scenario_id in ["scenario_001", "scenario_002", "scenario_003"]
        assert result.weights == self.sample_preferences
        
        # Check ranking order (should be sorted by score descending)
        scores = [ranking.score for ranking in result.ranking]
        assert scores == sorted(scores, reverse=True)
        
        # Check ranks are assigned correctly
        for i, ranking in enumerate(result.ranking):
            assert ranking.rank == i + 1
    
    async def test_rank_scenarios_with_failed_results(self):
        """Test ranking scenarios with some failed results."""
        results_with_failures = self.sample_results + [
            ScenarioResult(
                scenario_id="failed_scenario",
                metrics=SimulationMetrics(
                    clearance_time=0.0,
                    max_queue=0.0,
                    fairness_index=0.0,
                    robustness=0.0
                ),
                status=TaskStatus.FAILED,
                duration_ms=1000,
                error_message="Simulation timeout"
            )
        ]
        
        result = await self.agent.rank_scenarios(
            results_with_failures,
            self.sample_preferences,
            self.sample_intent
        )
        
        # Should only rank successful scenarios
        assert len(result.ranking) == 3
        assert all(ranking.scenario_id != "failed_scenario" for ranking in result.ranking)
        assert result.validation_passed is True
    
    async def test_rank_scenarios_all_failed(self):
        """Test ranking when all scenarios failed."""
        failed_results = [
            ScenarioResult(
                scenario_id="failed_001",
                metrics=SimulationMetrics(
                    clearance_time=0.0,
                    max_queue=0.0,
                    fairness_index=0.0,
                    robustness=0.0
                ),
                status=TaskStatus.FAILED,
                duration_ms=1000,
                error_message="Error 1"
            ),
            ScenarioResult(
                scenario_id="failed_002",
                metrics=SimulationMetrics(
                    clearance_time=0.0,
                    max_queue=0.0,
                    fairness_index=0.0,
                    robustness=0.0
                ),
                status=TaskStatus.FAILED,
                duration_ms=1000,
                error_message="Error 2"
            )
        ]
        
        result = await self.agent.rank_scenarios(
            failed_results,
            self.sample_preferences,
            self.sample_intent
        )
        
        assert len(result.ranking) == 0
        assert result.validation_passed is False
        assert result.best_scenario_id == ""
    
    async def test_rank_scenarios_empty_list(self):
        """Test ranking with empty results list."""
        result = await self.agent.rank_scenarios(
            [],
            self.sample_preferences,
            self.sample_intent
        )
        
        assert len(result.ranking) == 0
        assert result.validation_passed is False
        assert result.best_scenario_id == ""
    
    async def test_calculate_composite_score_balanced_weights(self):
        """Test composite score calculation with balanced weights."""
        metrics = SimulationMetrics(
            clearance_time=1800.0,  # 30 minutes
            max_queue=150.0,
            fairness_index=0.85,
            robustness=0.75
        )
        
        preferences = UserPreferences(
            fairness_weight=1/3,
            clearance_weight=1/3,
            robustness_weight=1/3
        )
        
        score = await self.agent._calculate_composite_score(metrics, preferences)
        
        # Score should be between 0 and 1
        assert 0.0 <= score <= 1.0
        
        # With balanced weights, score should be reasonable
        assert score > 0.5  # Should be decent with these metrics
    
    async def test_calculate_composite_score_clearance_focused(self):
        """Test composite score calculation focused on clearance time."""
        metrics = SimulationMetrics(
            clearance_time=900.0,   # 15 minutes (very good)
            max_queue=300.0,        # High queue (bad)
            fairness_index=0.60,    # Low fairness (bad)
            robustness=0.60         # Low robustness (bad)
        )
        
        clearance_focused_preferences = UserPreferences(
            fairness_weight=0.1,
            clearance_weight=0.8,   # Heavily weight clearance
            robustness_weight=0.1
        )
        
        score = await self.agent._calculate_composite_score(metrics, clearance_focused_preferences)
        
        # Should get high score due to excellent clearance time
        assert score > 0.7
    
    async def test_calculate_composite_score_fairness_focused(self):
        """Test composite score calculation focused on fairness."""
        metrics = SimulationMetrics(
            clearance_time=3600.0,  # 60 minutes (bad)
            max_queue=300.0,        # High queue (bad)
            fairness_index=0.95,    # Excellent fairness
            robustness=0.60         # Low robustness (bad)
        )
        
        fairness_focused_preferences = UserPreferences(
            fairness_weight=0.8,    # Heavily weight fairness
            clearance_weight=0.1,
            robustness_weight=0.1
        )
        
        score = await self.agent._calculate_composite_score(metrics, fairness_focused_preferences)
        
        # Should get high score due to excellent fairness
        assert score > 0.7
    
    async def test_validate_result_success(self):
        """Test successful result validation."""
        valid_result = ScenarioResult(
            scenario_id="valid_scenario",
            metrics=SimulationMetrics(
                clearance_time=1800.0,
                max_queue=150.0,
                fairness_index=0.85,
                robustness=0.75
            ),
            status=TaskStatus.COMPLETED,
            duration_ms=5000
        )
        
        is_valid = await self.agent._validate_result(valid_result, self.sample_intent)
        assert is_valid is True
    
    async def test_validate_result_excessive_clearance_time(self):
        """Test validation failure due to excessive clearance time."""
        slow_result = ScenarioResult(
            scenario_id="slow_scenario",
            metrics=SimulationMetrics(
                clearance_time=7200.0,  # 2 hours (too slow)
                max_queue=150.0,
                fairness_index=0.85,
                robustness=0.75
            ),
            status=TaskStatus.COMPLETED,
            duration_ms=5000
        )
        
        is_valid = await self.agent._validate_result(slow_result, self.sample_intent)
        assert is_valid is False
    
    async def test_validate_result_negative_metrics(self):
        """Test validation failure due to negative metrics."""
        invalid_result = ScenarioResult(
            scenario_id="invalid_scenario",
            metrics=SimulationMetrics(
                clearance_time=-100.0,  # Negative time (invalid)
                max_queue=150.0,
                fairness_index=0.85,
                robustness=0.75
            ),
            status=TaskStatus.COMPLETED,
            duration_ms=5000
        )
        
        is_valid = await self.agent._validate_result(invalid_result, self.sample_intent)
        assert is_valid is False
    
    async def test_validate_result_out_of_range_indices(self):
        """Test validation failure due to out-of-range indices."""
        invalid_result = ScenarioResult(
            scenario_id="invalid_scenario",
            metrics=SimulationMetrics(
                clearance_time=1800.0,
                max_queue=150.0,
                fairness_index=1.5,    # > 1.0 (invalid)
                robustness=0.75
            ),
            status=TaskStatus.COMPLETED,
            duration_ms=5000
        )
        
        is_valid = await self.agent._validate_result(invalid_result, self.sample_intent)
        assert is_valid is False
    
    async def test_normalize_clearance_time(self):
        """Test clearance time normalization."""
        # Test various clearance times
        test_cases = [
            (900.0, 1.0),    # 15 minutes -> excellent (1.0)
            (1800.0, 0.75),  # 30 minutes -> good (0.75)
            (3600.0, 0.25),  # 60 minutes -> poor (0.25)
            (7200.0, 0.0),   # 120 minutes -> very poor (0.0)
        ]
        
        for clearance_time, expected_min in test_cases:
            normalized = await self.agent._normalize_clearance_time(clearance_time)
            assert 0.0 <= normalized <= 1.0
            
            # Check that shorter times get higher scores
            if clearance_time <= 1800.0:  # 30 minutes or less
                assert normalized >= 0.5
    
    async def test_normalize_max_queue(self):
        """Test max queue normalization."""
        # Test various queue lengths
        test_cases = [
            (0.0, 1.0),      # No queue -> excellent
            (50.0, 0.9),     # Small queue -> very good
            (200.0, 0.6),    # Medium queue -> okay
            (500.0, 0.0),    # Large queue -> poor
        ]
        
        for max_queue, expected_min in test_cases:
            normalized = await self.agent._normalize_max_queue(max_queue)
            assert 0.0 <= normalized <= 1.0
            
            # Check that smaller queues get higher scores
            if max_queue <= 100.0:
                assert normalized >= 0.8
    
    async def test_ranking_consistency(self):
        """Test that ranking is consistent across multiple runs."""
        # Run ranking multiple times with same data
        results = []
        for _ in range(5):
            result = await self.agent.rank_scenarios(
                self.sample_results,
                self.sample_preferences,
                self.sample_intent
            )
            results.append(result)
        
        # All results should have same ranking order
        first_ranking = [r.scenario_id for r in results[0].ranking]
        for result in results[1:]:
            current_ranking = [r.scenario_id for r in result.ranking]
            assert current_ranking == first_ranking
    
    async def test_ranking_with_identical_scores(self):
        """Test ranking behavior with identical composite scores."""
        # Create scenarios with identical metrics
        identical_results = [
            ScenarioResult(
                scenario_id=f"scenario_{i:03d}",
                metrics=SimulationMetrics(
                    clearance_time=1800.0,
                    max_queue=150.0,
                    fairness_index=0.85,
                    robustness=0.75
                ),
                status=TaskStatus.COMPLETED,
                duration_ms=5000
            )
            for i in range(3)
        ]
        
        result = await self.agent.rank_scenarios(
            identical_results,
            self.sample_preferences,
            self.sample_intent
        )
        
        # Should still produce valid ranking
        assert len(result.ranking) == 3
        assert result.validation_passed is True
        
        # All scores should be identical
        scores = [ranking.score for ranking in result.ranking]
        assert len(set(scores)) == 1  # All scores are the same
        
        # Ranks should still be 1, 2, 3
        ranks = [ranking.rank for ranking in result.ranking]
        assert ranks == [1, 2, 3]
    
    async def test_edge_case_extreme_metrics(self):
        """Test ranking with extreme metric values."""
        extreme_results = [
            ScenarioResult(
                scenario_id="extreme_fast",
                metrics=SimulationMetrics(
                    clearance_time=60.0,    # 1 minute (extremely fast)
                    max_queue=0.0,          # No queue
                    fairness_index=1.0,     # Perfect fairness
                    robustness=1.0          # Perfect robustness
                ),
                status=TaskStatus.COMPLETED,
                duration_ms=1000
            ),
            ScenarioResult(
                scenario_id="extreme_slow",
                metrics=SimulationMetrics(
                    clearance_time=10800.0, # 3 hours (extremely slow)
                    max_queue=1000.0,       # Huge queue
                    fairness_index=0.1,     # Very unfair
                    robustness=0.1          # Very fragile
                ),
                status=TaskStatus.COMPLETED,
                duration_ms=10000
            )
        ]
        
        result = await self.agent.rank_scenarios(
            extreme_results,
            self.sample_preferences,
            self.sample_intent
        )
        
        assert len(result.ranking) == 2
        
        # Extreme fast should rank higher than extreme slow
        assert result.ranking[0].scenario_id == "extreme_fast"
        assert result.ranking[1].scenario_id == "extreme_slow"
        
        # Score difference should be significant
        score_diff = result.ranking[0].score - result.ranking[1].score
        assert score_diff > 0.5
    
    async def test_weight_validation(self):
        """Test that user preferences weights are properly validated."""
        # This test ensures the ranking works even with edge case weights
        edge_case_preferences = UserPreferences(
            fairness_weight=0.01,
            clearance_weight=0.01,
            robustness_weight=0.98  # Almost all weight on robustness
        )
        
        result = await self.agent.rank_scenarios(
            self.sample_results,
            edge_case_preferences,
            self.sample_intent
        )
        
        assert len(result.ranking) == 3
        assert result.validation_passed is True
        
        # The scenario with highest robustness should rank first
        best_scenario = result.ranking[0]
        best_result = next(r for r in self.sample_results if r.scenario_id == best_scenario.scenario_id)
        
        # Should be the one with highest robustness (scenario_003 has 0.85)
        assert best_result.metrics.robustness >= 0.8


@pytest.mark.unit
class TestJudgeAgentEdgeCases:
    """Test edge cases and error conditions."""
    
    def setup_method(self):
        """Set up test environment."""
        self.agent = JudgeAgent()
    
    async def test_rank_scenarios_with_nan_metrics(self):
        """Test ranking scenarios with NaN metric values."""
        import math
        
        nan_result = ScenarioResult(
            scenario_id="nan_scenario",
            metrics=SimulationMetrics(
                clearance_time=float('nan'),
                max_queue=150.0,
                fairness_index=0.85,
                robustness=0.75
            ),
            status=TaskStatus.COMPLETED,
            duration_ms=5000
        )
        
        preferences = UserPreferences()
        intent = UserIntent(
            objective="Test NaN handling",
            constraints=ScenarioConstraints(),
            preferences=preferences
        )
        
        result = await self.agent.rank_scenarios([nan_result], preferences, intent)
        
        # Should handle NaN gracefully (likely by filtering out or giving low score)
        assert isinstance(result, JudgeResult)
        # The specific behavior depends on implementation, but should not crash
    
    async def test_rank_scenarios_with_infinite_metrics(self):
        """Test ranking scenarios with infinite metric values."""
        inf_result = ScenarioResult(
            scenario_id="inf_scenario",
            metrics=SimulationMetrics(
                clearance_time=float('inf'),
                max_queue=150.0,
                fairness_index=0.85,
                robustness=0.75
            ),
            status=TaskStatus.COMPLETED,
            duration_ms=5000
        )
        
        preferences = UserPreferences()
        intent = UserIntent(
            objective="Test infinity handling",
            constraints=ScenarioConstraints(),
            preferences=preferences
        )
        
        result = await self.agent.rank_scenarios([inf_result], preferences, intent)
        
        # Should handle infinity gracefully
        assert isinstance(result, JudgeResult)
    
    async def test_concurrent_ranking_requests(self):
        """Test handling multiple concurrent ranking requests."""
        import asyncio
        
        preferences = UserPreferences()
        intent = UserIntent(
            objective="Concurrent test",
            constraints=ScenarioConstraints(),
            preferences=preferences
        )
        
        # Create multiple result sets
        result_sets = [
            [
                ScenarioResult(
                    scenario_id=f"set_{i}_scenario_{j}",
                    metrics=SimulationMetrics(
                        clearance_time=1800.0 + j * 100,
                        max_queue=150.0 + j * 10,
                        fairness_index=0.85 - j * 0.05,
                        robustness=0.75 + j * 0.05
                    ),
                    status=TaskStatus.COMPLETED,
                    duration_ms=5000
                )
                for j in range(3)
            ]
            for i in range(3)
        ]
        
        # Run rankings concurrently
        tasks = [
            self.agent.rank_scenarios(result_set, preferences, intent)
            for result_set in result_sets
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All should complete successfully
        assert len(results) == 3
        for result in results:
            assert isinstance(result, JudgeResult)
            assert len(result.ranking) == 3
    
    async def test_ranking_with_zero_weights(self):
        """Test ranking with zero weights (edge case)."""
        # This shouldn't happen due to validation, but test robustness
        zero_preferences = UserPreferences(
            fairness_weight=0.0,
            clearance_weight=0.0,
            robustness_weight=1.0  # Only robustness matters
        )
        
        results = [
            ScenarioResult(
                scenario_id="scenario_001",
                metrics=SimulationMetrics(
                    clearance_time=1800.0,
                    max_queue=150.0,
                    fairness_index=0.85,
                    robustness=0.75
                ),
                status=TaskStatus.COMPLETED,
                duration_ms=5000
            ),
            ScenarioResult(
                scenario_id="scenario_002",
                metrics=SimulationMetrics(
                    clearance_time=3600.0,  # Worse clearance
                    max_queue=300.0,        # Worse queue
                    fairness_index=0.60,    # Worse fairness
                    robustness=0.90         # Better robustness
                ),
                status=TaskStatus.COMPLETED,
                duration_ms=5000
            )
        ]
        
        intent = UserIntent(
            objective="Test zero weights",
            constraints=ScenarioConstraints(),
            preferences=zero_preferences
        )
        
        result = await self.agent.rank_scenarios(results, zero_preferences, intent)
        
        # Should rank based only on robustness
        assert result.ranking[0].scenario_id == "scenario_002"  # Higher robustness
        assert result.ranking[1].scenario_id == "scenario_001"
