# Metrics Builder & Scenario Builder Summary

## Overview

We've successfully built a **simple, powerful, and agentic** metrics and scenario system for evacuation simulations. The system is designed to be:

- **Simple**: Uses pandas instead of complex SQL - easy to understand and maintain
- **Agentic**: Allows AI agents to define metrics and scenarios programmatically
- **Practical**: Focuses on real evacuation planning needs
- **Extensible**: Easy to add new metrics and scenario types

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Scenario      │    │    Metrics      │    │    Agents       │
│   Builder       │    │    Builder      │    │                 │
│                 │    │                 │    │                 │
│ • Templates     │    │ • Pandas Ops    │    │ • Metrics Agent │
│ • Variants      │    │ • Simple Config │    │ • Analysis      │
│ • Studies       │    │ • FastAPI       │    │ • Insights      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │  Simulation     │
                    │  Data           │
                    │                 │
                    │ • Timeseries    │
                    │ • Events        │
                    │ • Parquet/CSV   │
                    └─────────────────┘
```

## 📊 Metrics Builder

### Core Features

1. **Simple Configuration**: YAML/JSON-based metric definitions
2. **Pandas Operations**: Fast, reliable calculations using pandas
3. **Multiple Data Sources**: Timeseries and events data
4. **Flexible Filtering**: Time, scope, and value-based filters
5. **Post-Processing**: Unit conversions, rounding, etc.
6. **FastAPI Integration**: RESTful API for agent access

### Available Operations

- `percentile_time_to_threshold`: When does X% evacuation complete?
- `time_above_threshold`: How long are conditions dangerous?
- `max_value` / `min_value`: Peak values
- `quantile`: Statistical distributions
- `value_at_time`: Snapshot at specific time
- `area_under_curve`: Cumulative metrics
- `mean_value`: Averages
- `count_events`: Event counting

### Example Usage

```python
from metrics.builder import MetricsBuilder

builder = MetricsBuilder("data/")

# Calculate 95% evacuation time
result = builder.calculate_metric("run_123", {
    'source': 'timeseries',
    'metric_key': 'clearance_pct',
    'operation': 'percentile_time_to_threshold',
    'args': {'threshold_pct': 95},
    'post_process': {'divide_by': 60}  # Convert to minutes
})
```

### API Endpoints

- `GET /api/metrics/runs/{run_id}/info` - Get available data
- `POST /api/metrics/calculate` - Calculate single metric
- `POST /api/metrics/calculate-multiple` - Calculate multiple metrics
- `GET /api/metrics/examples` - Get example configurations

## 🏗️ Scenario Builder

### Core Features

1. **Template System**: Predefined scenario types (flood, fire, security, chemical)
2. **Variant Generation**: Automatically create parameter variations
3. **Comparison Studies**: Multi-scenario analysis
4. **Validation**: Ensure scenarios are realistic
5. **YAML Storage**: Human-readable scenario files

### Available Templates

- **Flood Central**: Major flooding in central London
- **Fire Building**: High-rise building fire evacuation
- **Terrorist Threat**: Security threat requiring area evacuation
- **Chemical Spill**: Chemical incident in industrial area

### Example Usage

```python
from scenarios.builder import ScenarioBuilder

builder = ScenarioBuilder()

# Create scenario from template
scenario = builder.create_scenario("flood_central", {
    "parameters.compliance_rate": 0.8,
    "severity": "high"
})

# Generate variants for comparison
variants = builder.generate_scenario_variants(scenario, {
    "parameters.compliance_rate": [0.6, 0.7, 0.8],
    "transport_disruption": [0.7, 0.8, 0.9]
})
```

## 🤖 Agent Integration

### Metrics Agent

The `MetricsAgent` demonstrates how AI agents can use the system:

```python
from agents.metrics_agent import MetricsAgent

agent = MetricsAgent()

# Analyze evacuation performance
analysis = agent.analyze_evacuation_performance("run_123")

# Get insights and recommendations
print(analysis['insights'])
print(analysis['recommendations'])

# Generate human-readable report
report = agent.generate_report("run_123")
```

### Agent Capabilities

- **Automated Analysis**: Calculate standard evacuation metrics
- **Insight Generation**: Convert metrics to human-readable insights
- **Bottleneck Detection**: Identify worst congestion points
- **Recommendations**: Suggest improvements based on data
- **Scenario Comparison**: Compare multiple evacuation scenarios

## 📁 File Structure

```
backend/
├── metrics/
│   ├── __init__.py
│   ├── builder.py          # Main metrics builder
│   ├── operations.py       # Pandas-based operations
│   └── examples.yaml       # Example configurations
├── scenarios/
│   ├── __init__.py
│   └── builder.py          # Scenario generation
├── agents/
│   └── metrics_agent.py    # Example agent
├── api/
│   └── metrics.py          # FastAPI endpoints
└── tests/
    └── test_metrics.py     # Unit tests
```

## 🧪 Testing & Demo

### Sample Data Created

- **Timeseries Data**: 488 records with realistic evacuation curves
- **Events Data**: 6 events showing simulation lifecycle
- **Time Range**: 30 minutes (0-1800 seconds)
- **Metrics**: clearance_pct, queue_len, density
- **Scopes**: City-wide, edges, stations

### Test Results

```
✅ Clearance p95: 20.0 minutes
✅ Max queue length: 50.0 (edge:main_st)
✅ Platform overcrowding: 1.5 minutes
✅ Total events: 6
✅ All operations working correctly
```

## 🚀 Key Benefits

### For Emergency Planners

1. **Quick Analysis**: Get evacuation metrics in seconds
2. **Clear Insights**: Automated interpretation of complex data
3. **Actionable Recommendations**: Specific improvement suggestions
4. **Scenario Comparison**: Test different emergency responses

### For AI Agents

1. **Simple Interface**: Easy-to-use Python API
2. **Flexible Configuration**: Define custom metrics on-the-fly
3. **Rich Context**: Get detailed analysis with bottlenecks and insights
4. **Extensible**: Add new operations and scenario types easily

### For Developers

1. **No SQL Complexity**: Pure Python with pandas
2. **Well Tested**: Comprehensive unit tests
3. **Clear Documentation**: Examples and demos included
4. **FastAPI Integration**: RESTful API ready

## 🔄 Agent Workflow Example

```python
# 1. Agent creates scenarios
builder = ScenarioBuilder()
scenarios = builder.create_comparison_study("flood_central", "Flood Study", {
    "parameters.compliance_rate": [0.6, 0.7, 0.8]
})

# 2. Run simulations (external system)
for scenario in scenarios['scenarios']:
    run_id = run_simulation(scenario)
    
    # 3. Agent analyzes results
    agent = MetricsAgent()
    analysis = agent.analyze_evacuation_performance(run_id)
    
    # 4. Agent provides insights
    print(f"Scenario: {scenario['name']}")
    print(f"Clearance time: {analysis['metrics']['clearance_p95']} minutes")
    for insight in analysis['insights']:
        print(f"- {insight}")
    
    # 5. Agent recommends improvements
    for rec in analysis['recommendations']:
        print(f"💡 {rec}")
```

## 🎯 Next Steps

The system is now ready for:

1. **Integration with existing simulation engines**
2. **Extension with more sophisticated agents**
3. **Addition of new metric types as needed**
4. **Deployment in production emergency planning workflows**

The simple, pandas-based approach ensures the system is maintainable, fast, and easy for both humans and AI agents to use effectively.

---

**Status**: ✅ Complete and fully functional
**Testing**: ✅ All components tested with sample data
**Documentation**: ✅ Comprehensive examples and demos included
