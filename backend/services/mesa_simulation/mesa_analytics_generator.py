"""
Mesa Comprehensive Analytics Generator.
Generates detailed charts and metrics from Mesa simulation results.
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
from typing import Dict, List, Any
import structlog
import io
import base64

logger = structlog.get_logger(__name__)

# Set style
sns.set_style("whitegrid")


class MesaAnalyticsGenerator:
    """Generate comprehensive Mesa evacuation analytics."""
    
    def generate_clearance_time_analysis(
        self,
        agent_data: List[Dict[str, Any]],
        metrics: Dict[str, Any]
    ) -> str:
        """
        Generate clearance time analysis with 4 subplots.
        Returns base64-encoded PNG.
        """
        # Extract evacuation times
        evacuated_agents = [a for a in agent_data if a.get('evacuation_time') is not None]
        if not evacuated_agents:
            logger.warning("No evacuated agents for clearance analysis")
            return ""
        
        completion_times = [a['evacuation_time'] for a in evacuated_agents]
        start_times = [a.get('start_time', 0) for a in evacuated_agents]
        travel_times = [a['evacuation_time'] - a.get('start_time', 0) for a in evacuated_agents]
        
        # Create figure with 2x2 subplots
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Mesa Evacuation Clearance Time Analysis', fontsize=16, fontweight='bold')
        
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
        max_start = max(start_times) if start_times else 1
        ax3.plot([0, max_start], [0, max_start], 
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
            ['Total Agents', f"{len(agent_data)}"],
            ['Evacuated', f"{len(evacuated_agents)}"],
            ['Evacuation Rate', f"{len(evacuated_agents)/len(agent_data)*100:.1f}%"],
            ['Mean Clearance', f"{np.mean(completion_times):.2f} min"],
            ['Median (P50)', f"{np.median(completion_times):.2f} min"],
            ['95th Percentile', f"{np.percentile(completion_times, 95):.2f} min"],
            ['Std Deviation', f"{np.std(completion_times):.2f} min"],
            ['Min Time', f"{np.min(completion_times):.2f} min"],
            ['Max Time', f"{np.max(completion_times):.2f} min"],
            ['', ''],
            ['Fairness Index', f"{metrics.get('fairness_index', 0):.3f}"],
            ['Robustness', f"{metrics.get('robustness', 0):.3f}"],
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
        
        # Convert to base64
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=200, bbox_inches='tight')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close()
        
        logger.info("Generated clearance time analysis chart")
        return img_base64
    
    def generate_route_density_analysis(
        self,
        agent_data: List[Dict[str, Any]]
    ) -> str:
        """
        Generate route density heatmap showing bottlenecks.
        Returns base64-encoded PNG.
        """
        # Count edge usage
        edge_usage = Counter()
        node_usage = Counter()
        
        for agent in agent_data:
            route = agent.get('route', [])
            for node in route:
                node_usage[node] += 1
            for i in range(len(route) - 1):
                edge = (route[i], route[i+1])
                edge_usage[edge] += 1
        
        if not edge_usage:
            logger.warning("No route data for density analysis")
            return ""
        
        # Create visualization
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))
        fig.suptitle('Mesa Route Density and Bottleneck Analysis', fontsize=16, fontweight='bold')
        
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
        
        # 2. Top bottlenecks table
        ax2.axis('off')
        
        top_edges = sorted(edge_usage.items(), key=lambda x: x[1], reverse=True)[:20]
        
        table_data = [['Rank', 'Edge', 'Agents', 'Level']]
        for i, ((u, v), count) in enumerate(top_edges, 1):
            u_short = str(u)[:10]
            v_short = str(v)[:10]
            edge_str = f"{u_short}→{v_short}"
            
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
                         colWidths=[0.1, 0.5, 0.15, 0.25],
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
            colors_map = {
                "CRITICAL": '#ffcdd2',
                "HIGH": '#fff9c4',
                "MODERATE": '#c8e6c9',
                "LOW": '#f0f0f0'
            }
            color = colors_map.get(level, '#f0f0f0')
            
            for j in range(4):
                table[(i, j)].set_facecolor(color)
        
        ax2.set_title('Top 20 Bottleneck Edges', fontsize=14, pad=20)
        
        plt.tight_layout()
        
        # Convert to base64
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=200, bbox_inches='tight')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close()
        
        logger.info("Generated route density analysis chart")
        return img_base64
    
    def generate_flow_analysis(
        self,
        agent_data: List[Dict[str, Any]]
    ) -> str:
        """
        Generate evacuation flow analysis.
        Returns base64-encoded PNG.
        """
        # Bin agents by start time
        time_bins = np.arange(0, 35, 5)  # 5-minute bins
        from collections import defaultdict
        agents_starting = defaultdict(int)
        
        for agent in agent_data:
            start_time = agent.get('start_time', 0)
            bin_idx = np.digitize([start_time], time_bins)[0] - 1
            if 0 <= bin_idx < len(time_bins) - 1:
                bin_label = f"{time_bins[bin_idx]:.0f}-{time_bins[bin_idx+1]:.0f}"
                agents_starting[bin_label] += 1
        
        # Create visualization
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        fig.suptitle('Mesa Evacuation Flow Analysis', fontsize=16, fontweight='bold')
        
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
        route_lengths = [len(agent.get('route', [])) for agent in agent_data if agent.get('route')]
        
        if route_lengths:
            ax2.hist(route_lengths, bins=25, color='purple', alpha=0.7, edgecolor='black')
            ax2.axvline(np.mean(route_lengths), color='red', linestyle='--',
                       linewidth=2, label=f'Mean: {np.mean(route_lengths):.1f} nodes')
            ax2.set_xlabel('Route Length (nodes)', fontsize=12)
            ax2.set_ylabel('Number of Agents', fontsize=12)
            ax2.set_title('Distribution of Route Lengths', fontsize=14)
            ax2.legend()
            ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Convert to base64
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=200, bbox_inches='tight')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close()
        
        logger.info("Generated flow analysis chart")
        return img_base64
