"""
Comprehensive Evacuation Visualization Demo

This script generates multiple types of diagrams:
- Route density heatmap
- Evacuation progress over time
- Bottleneck analysis
- Clearance time statistics
- Flow analysis
"""

import asyncio
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict, Counter
from pathlib import Path
import json
import structlog

from services.simulation_service import LondonGraphService, EvacuationSimulator
from models.schemas import ScenarioConfig

logger = structlog.get_logger(__name__)

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)


class ComprehensiveVisualizer:
    """Generate comprehensive evacuation analysis visualizations."""
    
    def __init__(self, output_dir: str = "visualizations"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_clearance_time_analysis(
        self,
        agents_data: list,
        simulation_id: str,
        metrics: dict
    ):
        """Generate clearance time distribution and statistics."""
        
        # Extract completion times from agent data
        completion_times = []
        start_times = []
        travel_times = []
        
        for agent in agents_data:
            start = agent.get('start_time', 0)
            route = agent.get('route', [])
            speed = agent.get('speed', 1.2)  # m/s
            
            if route and len(route) > 1:
                # Estimate travel time based on route length
                # (In real simulation, this would come from Mesa results)
                route_length = len(route) * 100  # Approximate meters
                travel_time = route_length / speed / 60  # Convert to minutes
                completion = start + travel_time
                
                start_times.append(start)
                travel_times.append(travel_time)
                completion_times.append(completion)
        
        if not completion_times:
            logger.warning("No completion times to analyze")
            return None
        
        # Create figure with subplots
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Evacuation Clearance Time Analysis', fontsize=16, fontweight='bold')
        
        # 1. Histogram of completion times
        ax1 = axes[0, 0]
        ax1.hist(completion_times, bins=30, color='steelblue', edgecolor='black', alpha=0.7)
        ax1.axvline(np.median(completion_times), color='red', linestyle='--', 
                   linewidth=2, label=f'Median: {np.median(completion_times):.1f} min')
        ax1.axvline(np.percentile(completion_times, 95), color='orange', linestyle='--',
                   linewidth=2, label=f'95th %ile: {np.percentile(completion_times, 95):.1f} min')
        ax1.set_xlabel('Completion Time (minutes)', fontsize=12)
        ax1.set_ylabel('Number of Agents', fontsize=12)
        ax1.set_title('Distribution of Evacuation Completion Times', fontsize=14)
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. Cumulative evacuation curve
        ax2 = axes[0, 1]
        sorted_times = sorted(completion_times)
        cumulative = np.arange(1, len(sorted_times) + 1) / len(sorted_times) * 100
        ax2.plot(sorted_times, cumulative, linewidth=2, color='darkgreen')
        ax2.fill_between(sorted_times, cumulative, alpha=0.3, color='lightgreen')
        ax2.axhline(50, color='red', linestyle='--', alpha=0.5, label='50% Evacuated')
        ax2.axhline(95, color='orange', linestyle='--', alpha=0.5, label='95% Evacuated')
        ax2.set_xlabel('Time (minutes)', fontsize=12)
        ax2.set_ylabel('% Population Evacuated', fontsize=12)
        ax2.set_title('Cumulative Evacuation Progress', fontsize=14)
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 3. Start time vs completion time scatter
        ax3 = axes[1, 0]
        scatter = ax3.scatter(start_times, completion_times, 
                            c=travel_times, cmap='viridis', 
                            alpha=0.6, s=50)
        ax3.plot([0, max(start_times)], [0, max(start_times)], 
                'r--', alpha=0.5, label='Start Time Line')
        ax3.set_xlabel('Start Time (minutes)', fontsize=12)
        ax3.set_ylabel('Completion Time (minutes)', fontsize=12)
        ax3.set_title('Start Time vs Completion Time', fontsize=14)
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        plt.colorbar(scatter, ax=ax3, label='Travel Time (min)')
        
        # 4. Statistics table
        ax4 = axes[1, 1]
        ax4.axis('off')
        
        stats_data = [
            ['Metric', 'Value'],
            ['Total Agents', f"{len(agents_data)}"],
            ['Mean Clearance', f"{np.mean(completion_times):.2f} min"],
            ['Median Clearance (P50)', f"{np.median(completion_times):.2f} min"],
            ['95th Percentile (P95)', f"{np.percentile(completion_times, 95):.2f} min"],
            ['Std Deviation', f"{np.std(completion_times):.2f} min"],
            ['Min Time', f"{np.min(completion_times):.2f} min"],
            ['Max Time', f"{np.max(completion_times):.2f} min"],
            ['Range', f"{np.max(completion_times) - np.min(completion_times):.2f} min"],
            ['', ''],
            ['Mean Travel Time', f"{np.mean(travel_times):.2f} min"],
            ['Mean Start Delay', f"{np.mean(start_times):.2f} min"],
        ]
        
        table = ax4.table(cellText=stats_data, cellLoc='left',
                         colWidths=[0.6, 0.4], loc='center',
                         bbox=[0, 0, 1, 1])
        table.auto_set_font_size(False)
        table.set_fontsize(11)
        table.scale(1, 2)
        
        # Style header row
        for i in range(2):
            table[(0, i)].set_facecolor('#4CAF50')
            table[(0, i)].set_text_props(weight='bold', color='white')
        
        # Alternate row colors
        for i in range(1, len(stats_data)):
            for j in range(2):
                if i % 2 == 0:
                    table[(i, j)].set_facecolor('#f0f0f0')
        
        plt.tight_layout()
        
        # Save figure
        output_path = self.output_dir / f"{simulation_id}_clearance_analysis.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Clearance time analysis saved to {output_path}")
        return str(output_path)
    
    def generate_route_density_heatmap(
        self,
        agents_data: list,
        graph,
        simulation_id: str
    ):
        """Generate route density heatmap showing congestion."""
        
        # Count how many times each edge is used
        edge_usage = Counter()
        node_usage = Counter()
        
        for agent in agents_data:
            route = agent.get('route', [])
            for node in route:
                node_usage[node] += 1
            for i in range(len(route) - 1):
                edge = (route[i], route[i+1])
                edge_usage[edge] += 1
        
        if not edge_usage:
            logger.warning("No route data for density heatmap")
            return None
        
        # Create visualization
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))
        fig.suptitle('Route Density and Bottleneck Analysis', fontsize=16, fontweight='bold')
        
        # 1. Edge usage histogram
        usage_counts = list(edge_usage.values())
        ax1.hist(usage_counts, bins=30, color='coral', edgecolor='black', alpha=0.7)
        ax1.axvline(np.mean(usage_counts), color='red', linestyle='--', 
                   linewidth=2, label=f'Mean: {np.mean(usage_counts):.1f}')
        ax1.axvline(np.percentile(usage_counts, 90), color='darkred', linestyle='--',
                   linewidth=2, label=f'90th %ile: {np.percentile(usage_counts, 90):.1f}')
        ax1.set_xlabel('Number of Agents Using Edge', fontsize=12)
        ax1.set_ylabel('Number of Edges', fontsize=12)
        ax1.set_title('Edge Usage Distribution (Congestion)', fontsize=14)
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. Top bottlenecks
        ax2.axis('off')
        
        # Get top 20 most used edges
        top_edges = sorted(edge_usage.items(), key=lambda x: x[1], reverse=True)[:20]
        
        table_data = [['Rank', 'Edge', 'Agent Count', 'Congestion Level']]
        for i, ((u, v), count) in enumerate(top_edges, 1):
            # Shorten node IDs for display
            u_short = str(u)[:8] if len(str(u)) > 8 else str(u)
            v_short = str(v)[:8] if len(str(v)) > 8 else str(v)
            edge_str = f"{u_short}→{v_short}"
            
            # Calculate congestion level
            if count > np.percentile(usage_counts, 95):
                level = "CRITICAL"
            elif count > np.percentile(usage_counts, 75):
                level = "HIGH"
            elif count > np.percentile(usage_counts, 50):
                level = "MODERATE"
            else:
                level = "LOW"
            
            table_data.append([f"{i}", edge_str, f"{count}", level])
        
        table = ax2.table(cellText=table_data, cellLoc='left',
                         colWidths=[0.1, 0.4, 0.2, 0.3],
                         loc='center', bbox=[0, 0, 1, 1])
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 1.8)
        
        # Style header
        for i in range(4):
            table[(0, i)].set_facecolor('#FF5722')
            table[(0, i)].set_text_props(weight='bold', color='white')
        
        # Color code by congestion level
        for i in range(1, len(table_data)):
            level = table_data[i][3]
            if level == "CRITICAL":
                color = '#ffcdd2'
            elif level == "HIGH":
                color = '#fff9c4'
            elif level == "MODERATE":
                color = '#c8e6c9'
            else:
                color = '#f0f0f0'
            
            for j in range(4):
                table[(i, j)].set_facecolor(color)
        
        ax2.set_title('Top 20 Bottleneck Edges', fontsize=14, pad=20)
        
        plt.tight_layout()
        
        output_path = self.output_dir / f"{simulation_id}_route_density.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Route density analysis saved to {output_path}")
        return str(output_path)
    
    def generate_flow_analysis(
        self,
        agents_data: list,
        simulation_id: str
    ):
        """Generate evacuation flow analysis over time."""
        
        # Bin agents by start time
        time_bins = np.arange(0, 35, 5)  # 5-minute bins up to 30 minutes
        agents_starting = defaultdict(int)
        
        for agent in agents_data:
            start_time = agent.get('start_time', 0)
            bin_idx = np.digitize([start_time], time_bins)[0] - 1
            if 0 <= bin_idx < len(time_bins) - 1:
                bin_label = f"{time_bins[bin_idx]:.0f}-{time_bins[bin_idx+1]:.0f}"
                agents_starting[bin_label] += 1
        
        # Create visualization
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        fig.suptitle('Evacuation Flow Analysis', fontsize=16, fontweight='bold')
        
        # 1. Agents starting per time bin
        bins = list(agents_starting.keys())
        counts = list(agents_starting.values())
        
        ax1.bar(range(len(bins)), counts, color='teal', alpha=0.7, edgecolor='black')
        ax1.set_xticks(range(len(bins)))
        ax1.set_xticklabels(bins, rotation=45, ha='right')
        ax1.set_xlabel('Time Interval (minutes)', fontsize=12)
        ax1.set_ylabel('Number of Agents Starting', fontsize=12)
        ax1.set_title('Evacuation Initiation Pattern', fontsize=14)
        ax1.grid(True, alpha=0.3, axis='y')
        
        # 2. Route length distribution
        route_lengths = [len(agent.get('route', [])) for agent in agents_data if agent.get('route')]
        
        ax2.hist(route_lengths, bins=25, color='purple', alpha=0.7, edgecolor='black')
        ax2.axvline(np.mean(route_lengths), color='red', linestyle='--',
                   linewidth=2, label=f'Mean: {np.mean(route_lengths):.1f} nodes')
        ax2.set_xlabel('Route Length (nodes)', fontsize=12)
        ax2.set_ylabel('Number of Agents', fontsize=12)
        ax2.set_title('Distribution of Route Lengths', fontsize=14)
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        output_path = self.output_dir / f"{simulation_id}_flow_analysis.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Flow analysis saved to {output_path}")
        return str(output_path)
    
    def generate_summary_report(
        self,
        agents_data: list,
        metrics: dict,
        simulation_id: str
    ):
        """Generate a comprehensive summary report."""
        
        completion_times = []
        for agent in agents_data:
            start = agent.get('start_time', 0)
            route = agent.get('route', [])
            speed = agent.get('speed', 1.2)
            if route:
                route_length = len(route) * 100
                travel_time = route_length / speed / 60
                completion_times.append(start + travel_time)
        
        report = {
            "simulation_id": simulation_id,
            "total_agents": len(agents_data),
            "clearance_metrics": {
                "median_clearance_time_min": float(np.median(completion_times)) if completion_times else 0,
                "p95_clearance_time_min": float(np.percentile(completion_times, 95)) if completion_times else 0,
                "mean_clearance_time_min": float(np.mean(completion_times)) if completion_times else 0,
                "std_clearance_time_min": float(np.std(completion_times)) if completion_times else 0,
                "min_clearance_time_min": float(np.min(completion_times)) if completion_times else 0,
                "max_clearance_time_min": float(np.max(completion_times)) if completion_times else 0,
            },
            "route_metrics": {
                "mean_route_length": float(np.mean([len(a.get('route', [])) for a in agents_data])),
                "mean_speed_ms": float(np.mean([a.get('speed', 0) for a in agents_data])),
                "mean_start_delay_min": float(np.mean([a.get('start_time', 0) for a in agents_data])),
            },
            "original_metrics": metrics
        }
        
        output_path = self.output_dir / f"{simulation_id}_summary_report.json"
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Summary report saved to {output_path}")
        return str(output_path)


async def run_comprehensive_demo():
    """Run comprehensive evacuation visualization demo."""
    print("=" * 80)
    print("COMPREHENSIVE EVACUATION VISUALIZATION DEMO")
    print("=" * 80)
    print()
    
    # Initialize services
    print("1. Initializing services...")
    graph_service = LondonGraphService()
    simulator = EvacuationSimulator(graph_service)
    visualizer = ComprehensiveVisualizer()
    print("   ✓ Services initialized\n")
    
    # Create scenario
    print("2. Creating scenario...")
    scenario = ScenarioConfig(
        id="comprehensive_demo",
        name="Comprehensive 1000-Agent Visualization",
        description="Demo with multiple diagram types and clearance analysis",
        closures=[],
        capacity_changes=[],
        protected_corridors=[]
    )
    print("   ✓ Scenario created\n")
    
    # Run simulation
    print("3. Running simulation...")
    try:
        metrics, visualizations = await simulator.simulate_scenario_with_visualizations(scenario)
        graph = await graph_service.get_london_graph()
        
        # Extract agent data from the Mesa visualization service
        # We need to re-run to get the agent data
        modified_graph = simulator._apply_scenario_modifications(graph.copy(), scenario)
        simulation_results = await simulator._run_simulation(modified_graph, scenario)
        agents_data = simulation_results.get('agent_data', [])
        
        print(f"   ✓ Simulation complete ({len(agents_data)} agents)\n")
        
        # Generate comprehensive visualizations
        print("4. Generating comprehensive visualizations...")
        
        metrics_dict = {
            "clearance_time": metrics.clearance_time,
            "max_queue": metrics.max_queue,
            "fairness_index": metrics.fairness_index,
            "robustness": metrics.robustness
        }
        
        viz_paths = {}
        
        print("   - Generating clearance time analysis...")
        viz_paths['clearance'] = visualizer.generate_clearance_time_analysis(
            agents_data, scenario.id, metrics_dict
        )
        
        print("   - Generating route density heatmap...")
        viz_paths['density'] = visualizer.generate_route_density_heatmap(
            agents_data, modified_graph, scenario.id
        )
        
        print("   - Generating flow analysis...")
        viz_paths['flow'] = visualizer.generate_flow_analysis(
            agents_data, scenario.id
        )
        
        print("   - Generating summary report...")
        viz_paths['report'] = visualizer.generate_summary_report(
            agents_data, metrics_dict, scenario.id
        )
        
        print("   ✓ All visualizations generated\n")
        
        # Display results
        print("=" * 80)
        print("RESULTS")
        print("=" * 80)
        print()
        
        print("📊 CLEARANCE TIME METRICS:")
        print(f"   P50 (Median):     {metrics.clearance_time:.2f} minutes")
        print(f"   Max Queue:        {metrics.max_queue:.2f} people")
        print(f"   Fairness Index:   {metrics.fairness_index:.2f}")
        print(f"   Robustness:       {metrics.robustness:.2f}")
        print()
        
        print("📁 GENERATED VISUALIZATIONS:")
        for viz_type, viz_path in viz_paths.items():
            if viz_path:
                print(f"   ✓ {viz_type.upper():12} → {viz_path}")
        
        for viz_type, viz_path in visualizations.items():
            if viz_path:
                print(f"   ✓ {viz_type.upper():12} → {viz_path}")
        print()
        
        print("=" * 80)
        print("✅ SUCCESS - Comprehensive visualization complete!")
        print("=" * 80)
        print()
        print("View the generated files:")
        for viz_type, viz_path in {**viz_paths, **visualizations}.items():
            if viz_path:
                print(f"  open {viz_path}")
        print()
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(run_comprehensive_demo())
    exit(0 if success else 1)
