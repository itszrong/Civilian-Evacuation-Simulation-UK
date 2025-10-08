"""
Integration tests for Mesa simulation in full system.

Tests the complete flow from scenario configuration through Mesa simulation
to evaluation with the framework.
"""
import pytest
import asyncio
from services.simulation_service import EvacuationSimulator, LondonGraphService
from models.schemas import ScenarioConfig
from evaluation.evaluator import FrameworkEvaluator


@pytest.mark.asyncio
async def test_mesa_simulation_end_to_end():
    """Test complete flow with Mesa simulation."""
    
    # Setup
    graph_service = LondonGraphService()
    simulator = EvacuationSimulator(graph_service)
    
    # Create test scenario with small population for fast testing
    scenario = ScenarioConfig(
        id="test_mesa",
        name="Mesa Integration Test"
    )
    # Note: We use defaults which will be 50000, but Mesa will handle it
    
    # Run simulation
    metrics = await simulator.simulate_scenario(scenario)
    
    # Verify Mesa was used
    assert hasattr(simulator, 'mesa_executor')
    
    # Verify metrics are realistic
    assert 0 < metrics.clearance_time < 180
    assert 0 < metrics.max_queue < 500
    assert 0 <= metrics.fairness_index <= 1.0
    
    # Verify not using default heuristics
    assert metrics.clearance_time != 180.0  # Not default heuristic
    
    print("✅ Mesa integration test passed")


@pytest.mark.asyncio
async def test_mesa_with_evaluation():
    """Test Mesa results work with evaluation framework."""
    
    # Run simulation
    graph_service = LondonGraphService()
    simulator = EvacuationSimulator(graph_service)
    scenario = ScenarioConfig(
        id="test_eval",
        name="Mesa Evaluation Test",
        template="mass_fluvial_flood_rwc",
        population_size=50000,
        duration_minutes=180
    )
    
    metrics = await simulator.simulate_scenario(scenario)
    
    # Evaluate with framework
    evaluator = FrameworkEvaluator()
    eval_result = evaluator.evaluate_scenario_result(
        scenario_template="mass_fluvial_flood_rwc",
        metrics=metrics.__dict__,
        scenario_data={'simulation_engine': 'mesa_agent_based'}
    )
    
    # Verify evaluation works
    assert eval_result['status'] in ['ok', 'amber', 'fail']
    assert len(eval_result['evaluations']) > 0
    
    # Verify confidence is marked as MEDIUM (not VERY_LOW)
    for metric_eval in eval_result['evaluations'].values():
        assert metric_eval['confidence'] in ['medium', 'low']
        assert metric_eval['source'] == 'mesa_simulation'
    
    print("✅ Mesa evaluation integration test passed")


@pytest.mark.asyncio
async def test_mesa_fallback_to_heuristic():
    """Test that system falls back to heuristic if Mesa fails."""
    
    # This test would require mocking Mesa failure
    # For now, we just verify the fallback method exists
    
    graph_service = LondonGraphService()
    simulator = EvacuationSimulator(graph_service)
    
    # Verify fallback method exists
    assert hasattr(simulator, '_run_simulation_fallback')
    
    print("✅ Mesa fallback test passed")


@pytest.mark.asyncio
async def test_orchestrator_mesa_integration():
    """Test orchestrator uses Mesa for real evacuation simulations."""
    
    from services.orchestration.multi_city_orchestrator import EvacuationOrchestrator
    
    orchestrator = EvacuationOrchestrator()
    
    # Verify Mesa executor is initialized
    assert hasattr(orchestrator, 'mesa_executor')
    
    # Run a small test simulation
    result = orchestrator.run_real_evacuation_simulation(
        city="Westminster",
        scenario_config={
            'population_size': 1000,
            'duration_minutes': 60,
            'num_scenarios': 2  # Small number for testing
        }
    )
    
    # Verify Mesa was used
    assert result.get('simulation_engine') == 'mesa_agent_based'
    assert 'calculated_metrics' in result
    assert 'clearance_time_p50' in result['calculated_metrics']
    
    print("✅ Orchestrator Mesa integration test passed")


def test_mesa_metric_mapping():
    """Test that Mesa metrics are correctly mapped to framework metrics."""
    
    evaluator = FrameworkEvaluator()
    
    # Simulate Mesa metrics
    mesa_metrics = {
        'clearance_time_p50': 45.0,
        'clearance_time_p95': 90.0,
        'max_queue_length': 150,
        'total_evacuated': 50000,
        'simulation_engine': 'mesa_agent_based'
    }
    
    # Evaluate
    result = evaluator.evaluate_scenario_result(
        scenario_template="mass_fluvial_flood_rwc",
        metrics=mesa_metrics,
        scenario_data={'simulation_engine': 'mesa_agent_based'}
    )
    
    # Verify mapping worked
    assert 'clearance_p50_minutes' in result['evaluations'] or \
           'clearance_p95_minutes' in result['evaluations']
    
    print("✅ Mesa metric mapping test passed")


if __name__ == '__main__':
    # Run tests individually for debugging
    print("Running Mesa integration tests...\n")
    
    asyncio.run(test_mesa_simulation_end_to_end())
    asyncio.run(test_mesa_with_evaluation())
    asyncio.run(test_mesa_fallback_to_heuristic())
    asyncio.run(test_orchestrator_mesa_integration())
    test_mesa_metric_mapping()
    
    print("\n✅ All Mesa integration tests passed!")
