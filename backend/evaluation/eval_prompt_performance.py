"""
Simple DSPy Prompt Performance Evaluation with Visualization

Evaluates agentic scenario generation prompts and outputs performance graphs.
Run: python backend/evaluation/eval_prompt_performance.py
"""

import os
import json
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend

# Simple evaluation without heavy dependencies
def evaluate_scenario_quality(scenario: dict) -> dict:
    """Simple scoring function for scenarios."""
    scores = {
        'completeness': 0.0,
        'realism': 0.0,
        'framework_compliance': 0.0
    }
    
    # Completeness: check required fields
    required_fields = ['name', 'hazard_type', 'scale', 'people_affected', 
                      'duration_minutes', 'compliance', 'modes', 'warning_time']
    present = sum(1 for f in required_fields if f in scenario and scenario.get(f))
    scores['completeness'] = present / len(required_fields)
    
    # Realism: check if values are in reasonable ranges
    realism_score = 0
    max_realism = 5
    
    # Population check
    if 'people_affected' in scenario:
        pop = scenario['people_affected']
        if 100 <= pop <= 200000:
            realism_score += 1
    
    # Duration check
    if 'duration_minutes' in scenario:
        dur = scenario['duration_minutes']
        if 30 <= dur <= 2880:  # 30 min to 48 hours
            realism_score += 1
    
    # Compliance check
    if 'compliance' in scenario:
        comp = scenario['compliance']
        if 0.4 <= comp <= 1.0:
            realism_score += 1
    
    # Scale check
    if 'scale' in scenario:
        if scenario['scale'] in ['small', 'medium', 'large', 'mass']:
            realism_score += 1
    
    # Hazard type check
    if 'hazard_type' in scenario:
        valid_hazards = ['flood', 'fire', 'chemical', 'terrorist_event', 'UXO', 'gas_leak']
        if scenario['hazard_type'] in valid_hazards:
            realism_score += 1
    
    scores['realism'] = realism_score / max_realism
    
    # Framework compliance: check governance
    compliance_score = 0
    max_compliance = 4
    
    if 'governance' in scenario:
        compliance_score += 1
    
    if 'warning_time' in scenario:
        if scenario['warning_time'] in ['sudden_impact', 'immediate', 'rising_tide', 'planned']:
            compliance_score += 1
    
    if 'modes' in scenario and isinstance(scenario['modes'], list):
        if len(scenario['modes']) > 0:
            compliance_score += 1
    
    # Check scale appropriateness
    if 'scale' in scenario and 'people_affected' in scenario:
        scale = scenario['scale']
        people = scenario['people_affected']
        if (scale == 'small' and people < 2000) or \
           (scale == 'medium' and 2000 <= people < 40000) or \
           (scale == 'large' and 40000 <= people < 100000) or \
           (scale == 'mass' and people >= 100000):
            compliance_score += 1
    
    scores['framework_compliance'] = compliance_score / max_compliance
    
    # Combined score (weighted average)
    scores['combined'] = (
        scores['realism'] * 0.4 +
        scores['framework_compliance'] * 0.4 +
        scores['completeness'] * 0.2
    )
    
    return scores


def generate_test_scenarios():
    """Generate test scenarios with varied quality levels."""
    
    scenarios = {
        "Minimal (Poor)": {
            "name": "Flood scenario",
            "hazard_type": "flood",
            "scale": "medium",
            "people_affected": 20000
        },
        "Basic (Fair)": {
            "name": "Central London flood evacuation",
            "hazard_type": "flood",
            "scale": "large",
            "people_affected": 60000,
            "duration_minutes": 480,
            "compliance": 0.7,
            "modes": ["walk", "bus", "rail"]
        },
        "Detailed (Good)": {
            "name": "Westminster flood with governance",
            "hazard_type": "flood",
            "scale": "large",
            "people_affected": 65000,
            "duration_minutes": 500,
            "compliance": 0.72,
            "modes": ["walk", "bus", "rail", "car"],
            "warning_time": "rising_tide",
            "governance": {"SCG": True}
        },
        "Framework (Very Good)": {
            "name": "Chemical release – sudden impact with protocols",
            "hazard_type": "chemical",
            "scale": "large",
            "people_affected": 60000,
            "duration_minutes": 480,
            "compliance": 0.6,
            "modes": ["walk", "bus", "rail", "car"],
            "warning_time": "sudden_impact",
            "governance": {"SCG": True, "ESCG": True}
        },
        "Comprehensive (Excellent)": {
            "name": "Thames fluvial flood – pan-London RWC",
            "hazard_type": "flood",
            "scale": "mass",
            "people_affected": 150000,
            "duration_minutes": 1440,
            "compliance": 0.7,
            "modes": ["walk", "bus", "rail", "car", "river"],
            "warning_time": "rising_tide",
            "governance": {"SCG": True, "ESCG": True, "LLACC": True},
            "phases": ["initiate", "alert", "move", "shelter", "return"]
        },
        "Unrealistic (Bad)": {
            "name": "Massive evacuation",
            "hazard_type": "unknown_hazard",
            "scale": "large",
            "people_affected": 5000000,  # Unrealistic - too many
            "duration_minutes": 10,  # Too short
            "compliance": 1.5,  # Invalid
            "modes": ["teleport"]  # Not real
        }
    }
    
    return scenarios


def create_performance_visualization(results: dict, output_path: str):
    """Create bar chart showing prompt performance."""
    
    # Prepare data
    prompts = list(results.keys())
    metrics = ['Realism', 'Framework\nCompliance', 'Completeness', 'Combined']
    
    # Set up the plot
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    fig.suptitle('DSPy Agentic Scenario Generation: Prompt Performance Comparison', 
                 fontsize=16, fontweight='bold')
    
    # Chart 1: Individual metrics comparison
    x = range(len(prompts))
    width = 0.2
    
    for i, metric_key in enumerate(['realism', 'framework_compliance', 'completeness', 'combined']):
        values = [results[p][metric_key] for p in prompts]
        offset = (i - 1.5) * width
        ax1.bar([xi + offset for xi in x], values, width, 
                label=metrics[i], alpha=0.8)
    
    ax1.set_xlabel('Prompt Type', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Score (0-1)', fontsize=12, fontweight='bold')
    ax1.set_title('Metric Breakdown by Prompt', fontsize=14)
    ax1.set_xticks(x)
    ax1.set_xticklabels(prompts, rotation=15, ha='right')
    ax1.legend(loc='upper left', fontsize=10)
    ax1.grid(axis='y', alpha=0.3, linestyle='--')
    ax1.set_ylim(0, 1.1)
    
    # Add horizontal line for pass threshold
    ax1.axhline(y=0.7, color='green', linestyle='--', linewidth=2, 
                alpha=0.5, label='Pass Threshold (0.7)')
    
    # Chart 2: Combined scores comparison (larger)
    combined_scores = [results[p]['combined'] for p in prompts]
    colors = ['#ff6b6b' if s < 0.5 else '#ffd93d' if s < 0.7 else '#6bcf7f' 
              for s in combined_scores]
    
    bars = ax2.bar(prompts, combined_scores, color=colors, alpha=0.8, edgecolor='black')
    ax2.set_xlabel('Prompt Type', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Combined Score (0-1)', fontsize=12, fontweight='bold')
    ax2.set_title('Overall Performance (Combined Score)', fontsize=14)
    ax2.set_xticklabels(prompts, rotation=15, ha='right')
    ax2.grid(axis='y', alpha=0.3, linestyle='--')
    ax2.set_ylim(0, 1.1)
    
    # Add threshold line
    ax2.axhline(y=0.7, color='green', linestyle='--', linewidth=2, 
                alpha=0.5, label='Pass Threshold')
    
    # Add value labels on bars
    for bar, score in zip(bars, combined_scores):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + 0.02,
                f'{score:.2f}',
                ha='center', va='bottom', fontweight='bold', fontsize=10)
    
    ax2.legend(loc='upper left', fontsize=10)
    
    # Add color legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#6bcf7f', label='Pass (≥0.7)'),
        Patch(facecolor='#ffd93d', label='Amber (0.5-0.7)'),
        Patch(facecolor='#ff6b6b', label='Fail (<0.5)')
    ]
    ax2.legend(handles=legend_elements, loc='upper right', fontsize=10)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\n✅ Visualization saved to: {output_path}")
    
    return output_path


def main():
    """Run prompt performance evaluation."""
    
    print("=" * 80)
    print("DSPy AGENTIC SCENARIO EVALUATION - PROMPT PERFORMANCE")
    print("=" * 80)
    print("\nEvaluating different prompt strategies for scenario generation...")
    
    # Generate test scenarios
    scenarios = generate_test_scenarios()
    
    # Evaluate each scenario
    results = {}
    print("\nEvaluation Results:")
    print("-" * 80)
    
    for prompt_type, scenario in scenarios.items():
        scores = evaluate_scenario_quality(scenario)
        results[prompt_type] = scores
        
        print(f"\n{prompt_type}:")
        print(f"  Realism:             {scores['realism']:.2f} {'✅' if scores['realism'] >= 0.7 else '⚠️' if scores['realism'] >= 0.5 else '❌'}")
        print(f"  Framework Compliance: {scores['framework_compliance']:.2f} {'✅' if scores['framework_compliance'] >= 0.7 else '⚠️' if scores['framework_compliance'] >= 0.5 else '❌'}")
        print(f"  Completeness:        {scores['completeness']:.2f} {'✅' if scores['completeness'] >= 0.7 else '⚠️' if scores['completeness'] >= 0.5 else '❌'}")
        print(f"  Combined Score:      {scores['combined']:.2f} {'✅' if scores['combined'] >= 0.7 else '⚠️' if scores['combined'] >= 0.5 else '❌'}")
    
    # Calculate summary statistics
    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)
    
    avg_scores = {
        'realism': sum(r['realism'] for r in results.values()) / len(results),
        'framework_compliance': sum(r['framework_compliance'] for r in results.values()) / len(results),
        'completeness': sum(r['completeness'] for r in results.values()) / len(results),
        'combined': sum(r['combined'] for r in results.values()) / len(results)
    }
    
    print(f"\nAverage Scores Across All Prompts:")
    print(f"  Realism:             {avg_scores['realism']:.2f}")
    print(f"  Framework Compliance: {avg_scores['framework_compliance']:.2f}")
    print(f"  Completeness:        {avg_scores['completeness']:.2f}")
    print(f"  Combined:            {avg_scores['combined']:.2f}")
    
    # Find best performing prompt
    best_prompt = max(results.items(), key=lambda x: x[1]['combined'])
    print(f"\n🏆 Best Performing Prompt: {best_prompt[0]} (Score: {best_prompt[1]['combined']:.2f})")
    
    # Count pass rates
    pass_count = sum(1 for r in results.values() if r['combined'] >= 0.7)
    print(f"\n📊 Pass Rate: {pass_count}/{len(results)} ({pass_count/len(results)*100:.0f}%)")
    
    # Create visualization
    output_dir = Path("backend/evaluation")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "prompt_performance.png"
    
    print("\n" + "=" * 80)
    print("GENERATING VISUALIZATION")
    print("=" * 80)
    
    create_performance_visualization(results, str(output_path))
    
    # Save results to JSON
    json_path = output_dir / "prompt_performance_results.json"
    output_data = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "num_prompts_evaluated": len(results),
            "pass_threshold": 0.7
        },
        "results": results,
        "summary": avg_scores,
        "best_prompt": {
            "name": best_prompt[0],
            "score": best_prompt[1]['combined']
        }
    }
    
    with open(json_path, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"✅ Results saved to: {json_path}")
    
    print("\n" + "=" * 80)
    print("KEY INSIGHTS")
    print("=" * 80)
    
    # Generate insights
    insights = []
    
    if best_prompt[1]['combined'] >= 0.7:
        insights.append(f"✅ {best_prompt[0]} achieves passing score (≥0.7)")
    
    if avg_scores['completeness'] > avg_scores['framework_compliance']:
        insights.append("⚠️  Framework compliance is lower than completeness - prompts need more framework guidance")
    
    if any(r['combined'] < 0.5 for r in results.values()):
        failing = [name for name, r in results.items() if r['combined'] < 0.5]
        insights.append(f"❌ {len(failing)} prompt(s) failing: {', '.join(failing)}")
    
    for insight in insights:
        print(f"\n{insight}")
    
    print("\n" + "=" * 80)
    print("✅ EVALUATION COMPLETE")
    print("=" * 80)
    print(f"\nView graph: open {output_path}")
    print(f"View data:  open {json_path}")


if __name__ == "__main__":
    main()
