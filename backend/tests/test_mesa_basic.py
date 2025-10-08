"""
Basic test to verify Mesa simulation is working.
Run with: python test_mesa_basic.py
"""

import networkx as nx
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from services.mesa_simulation.model import EvacuationModel


def test_simple_evacuation():
    """Test basic evacuation with 5 agents on simple network."""
    print("🧪 Testing Mesa Evacuation Simulation...")
    print("-" * 50)
    
    # Create simple network
    G = nx.MultiDiGraph()
    G.add_edge(0, 1, 0, length=100, highway='residential')
    G.add_edge(1, 2, 0, length=100, highway='residential')
    G.add_edge(2, 3, 0, length=100, highway='residential')
    
    print(f"✓ Created network with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")
    
    # Create 5 agents
    agents = [
        {
            'unique_id': i,
            'current_node': 0,
            'target_node': 3,
            'route': [0, 1, 2, 3],
            'speed': 1.2,
            'start_time': 0.0
        }
        for i in range(5)
    ]
    
    print(f"✓ Created {len(agents)} agents")
    
    # Run simulation
    print("\n🏃 Running simulation...")
    model = EvacuationModel(G, agents, time_step_min=1.0, scenario_name="basic_test")
    results = model.run(duration_minutes=30)
    
    # Display results
    print("\n📊 Results:")
    print(f"  Total evacuated: {results['total_evacuated']}/{results['total_agents']}")
    print(f"  Evacuation rate: {results['evacuation_rate']*100:.1f}%")
    print(f"  Clearance P50: {results['clearance_time_p50']:.1f} minutes")
    print(f"  Clearance P95: {results['clearance_time_p95']:.1f} minutes")
    print(f"  Max queue length: {results['max_queue_length']}")
    print(f"  Simulation time: {results['simulation_time']:.1f} minutes")
    
    # Assertions
    assert results['total_evacuated'] == 5, f"Expected 5 evacuated, got {results['total_evacuated']}"
    assert results['clearance_time_p95'] is not None, "Clearance time should not be None"
    assert results['clearance_time_p95'] > 0, "Clearance time should be positive"
    
    print("\n✅ All tests passed!")
    return results


if __name__ == '__main__':
    try:
        results = test_simple_evacuation()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
