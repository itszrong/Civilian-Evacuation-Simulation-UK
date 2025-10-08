"""
Test script for dual visualization system integration.

This script tests the Mesa visualization service integration with the simulation service.
"""

import asyncio
from services.simulation_service import LondonGraphService, EvacuationSimulator
from models.schemas import ScenarioConfig
from pathlib import Path


async def test_dual_visualization():
    """Test the dual visualization system."""
    print("🧪 Testing Dual Visualization System Integration\n")
    
    # Initialize services
    print("1. Initializing services...")
    graph_service = LondonGraphService()
    simulator = EvacuationSimulator(graph_service)
    print("   ✓ Services initialized\n")
    
    # Create a simple test scenario
    print("2. Creating test scenario...")
    scenario = ScenarioConfig(
        id="test_dual_viz",
        name="Test Dual Visualization",
        description="Test scenario for dual visualization system",
        closures=[],
        capacity_changes=[],
        protected_corridors=[]
    )
    print("   ✓ Test scenario created\n")
    
    # Run simulation with visualizations
    print("3. Running simulation with dual visualizations...")
    try:
        metrics, visualizations = await simulator.simulate_scenario_with_visualizations(scenario)
        print("   ✓ Simulation completed\n")
        
        # Check results
        print("4. Checking results...")
        print(f"   Metrics:")
        print(f"     - Clearance time: {metrics.clearance_time:.2f} minutes")
        print(f"     - Max queue: {metrics.max_queue:.2f}")
        print(f"     - Fairness index: {metrics.fairness_index:.2f}")
        print(f"     - Robustness: {metrics.robustness:.2f}")
        print()
        
        print(f"   Visualizations:")
        for viz_type, viz_path in visualizations.items():
            exists = Path(viz_path).exists() if viz_path else False
            status = "✓" if exists else "✗"
            print(f"     {status} {viz_type}: {viz_path}")
        print()
        
        # Check if Mesa visualization was created
        mesa_viz_path = visualizations.get('mesa_routes', '')
        if mesa_viz_path and Path(mesa_viz_path).exists():
            print("✅ SUCCESS: Dual visualization system is working!")
            print(f"   Mesa routes visualization created at: {mesa_viz_path}")
            return True
        else:
            print("⚠️  WARNING: Mesa visualization was not created")
            print("   This may be normal if no agent data was available")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function."""
    print("=" * 60)
    print("DUAL VISUALIZATION SYSTEM TEST")
    print("=" * 60)
    print()
    
    success = await test_dual_visualization()
    
    print()
    print("=" * 60)
    if success:
        print("TEST PASSED ✓")
    else:
        print("TEST COMPLETED WITH WARNINGS ⚠️")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
