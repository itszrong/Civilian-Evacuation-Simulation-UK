"""
Demo script for 1000-agent evacuation simulation with dual visualization.

This script demonstrates:
- 1000 agents starting from city center
- Evacuating to borough boundaries
- Full Mesa agent-based simulation
- Dual visualization (primary + Mesa routes)
"""

import asyncio
from services.simulation_service import LondonGraphService, EvacuationSimulator
from models.schemas import ScenarioConfig
from pathlib import Path
import time


async def run_1000_agent_demo():
    """Run full 1000-agent evacuation simulation with visualization."""
    print("=" * 70)
    print("1000-AGENT EVACUATION SIMULATION DEMO")
    print("=" * 70)
    print()
    
    start_time = time.time()
    
    # Initialize services
    print("1. Initializing services...")
    graph_service = LondonGraphService()
    simulator = EvacuationSimulator(graph_service)
    print("   ✓ Services initialized\n")
    
    # Create scenario
    print("2. Creating scenario...")
    scenario = ScenarioConfig(
        id="demo_1000_agents",
        name="1000-Agent City Center Evacuation",
        description="Demo: 1000 agents evacuating from city center to borough boundaries",
        closures=[],
        capacity_changes=[],
        protected_corridors=[]
    )
    print("   ✓ Scenario created\n")
    
    # Run simulation with visualizations
    print("3. Running 1000-agent simulation from city center...")
    print("   (This may take a few minutes...)")
    print()
    
    try:
        metrics, visualizations = await simulator.simulate_scenario_with_visualizations(scenario)
        
        # Also generate density heatmap
        print("   Generating density heatmap...")
        from services.visualization.mesa_visualizer import MesaVisualizationService
        visualizer = MesaVisualizationService()
        
        # Get the agent data and graph
        graph = await graph_service.get_london_graph()
        modified_graph = simulator._apply_scenario_modifications(graph.copy(), scenario)
        simulation_results = await simulator._run_simulation(modified_graph, scenario)
        agents_data = simulation_results.get('agent_data', [])
        
        if agents_data:
            density_path = await visualizer.create_density_heatmap(
                agents_data=agents_data,
                graph=modified_graph,
                simulation_id=scenario.id
            )
            if density_path:
                visualizations['density_heatmap'] = density_path
        
        elapsed = time.time() - start_time
        
        print()
        print("=" * 70)
        print("SIMULATION COMPLETE")
        print("=" * 70)
        print()
        
        # Display results
        print("📊 SIMULATION METRICS:")
        print(f"   Clearance Time (P50): {metrics.clearance_time:.2f} minutes")
        print(f"   Max Queue Length:     {metrics.max_queue:.2f} people")
        print(f"   Fairness Index:       {metrics.fairness_index:.2f}")
        print(f"   Robustness Score:     {metrics.robustness:.2f}")
        print()
        
        print("🗺️  VISUALIZATIONS:")
        for viz_type, viz_path in visualizations.items():
            if viz_path:
                exists = Path(viz_path).exists()
                file_size = Path(viz_path).stat().st_size if exists else 0
                status = "✓" if exists else "✗"
                viz_name = viz_type.replace('_', ' ').title()
                print(f"   {status} {viz_name}:")
                print(f"      Path: {viz_path}")
                if exists:
                    print(f"      Size: {file_size / 1024:.1f} KB")
        print()
        
        print(f"⏱️  Total Time: {elapsed:.1f} seconds")
        print()
        
        # Check Mesa visualization
        mesa_viz_path = visualizations.get('mesa_routes', '')
        if mesa_viz_path and Path(mesa_viz_path).exists():
            print("=" * 70)
            print("✅ SUCCESS!")
            print("=" * 70)
            print()
            print(f"View the visualizations:")
            print(f"  open {mesa_viz_path}")
            if 'density_heatmap' in visualizations:
                print(f"  open {visualizations['density_heatmap']}")
            print()
            print("The visualizations show:")
            print("  • Routes: All agents starting from city center")
            print("  • Routes: Multiple evacuation routes radiating outward")
            print("  • Routes: Color-coded paths for individual agents")
            print("  • Heatmap: Route density and congestion hotspots")
            print("  • Heatmap: Green (low) to Red (high) usage intensity")
            print("  • Both: Black borough boundary outlines")
            print("  • Both: Interactive maps with zoom and pan")
            print()
            return True
        else:
            print("⚠️  WARNING: Mesa visualization not found")
            print("   Check logs for errors")
            return False
            
    except Exception as e:
        print()
        print("=" * 70)
        print("❌ ERROR")
        print("=" * 70)
        print(f"   {str(e)}")
        print()
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main entry point."""
    success = await run_1000_agent_demo()
    
    if not success:
        print("Demo completed with errors")
        exit(1)
    else:
        print("Demo completed successfully")
        exit(0)


if __name__ == "__main__":
    asyncio.run(main())
