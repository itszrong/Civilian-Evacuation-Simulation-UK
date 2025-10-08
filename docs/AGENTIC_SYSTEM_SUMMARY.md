# Agentic Metrics and Scenario Builders

## Overview

The system now includes **LLM-powered agentic builders** that allow AI agents to create custom metrics and scenarios for evacuation simulations using natural language. This makes the system truly "agentic" by enabling AI to define how simulations should be judged and what scenarios should be tested.

## 🧠 Key Features

### 1. **Agentic Metrics Builder**
- **Natural Language Input**: "I want to analyze evacuation efficiency and identify bottlenecks"
- **LLM-Generated Specifications**: Uses DSPy + OpenAI/Claude to create YAML metrics specs
- **Context Engineering**: Specialized prompts for evacuation planning domain
- **Template Fallback**: Works without LLM using intelligent templates

### 2. **Agentic Scenario Builder**  
- **Intent-Based Generation**: "Create a major flood scenario affecting London transport"
- **Realistic Parameters**: Generates population, duration, severity, affected areas
- **Variant Suggestions**: Proposes parameter variations for comparison studies
- **Multi-Hazard Support**: Flood, fire, security, chemical incidents

### 3. **Analysis Package Creation**
- **Complete Workflows**: Generates both scenario + optimized metrics together
- **Scenario-Optimized Metrics**: Metrics are tailored to the specific scenario type
- **Executable Specifications**: Ready to run on simulation data

## 🏗️ Architecture

### Core Components

```
backend/agents/agentic_builders.py
├── AgenticMetricsBuilder    # LLM-powered metrics generation
├── AgenticScenarioBuilder   # LLM-powered scenario generation  
└── AgenticBuilderService    # Orchestrates complete workflows

backend/api/agentic.py       # FastAPI endpoints for agentic features
```

### DSPy Integration

The system uses **DSPy** (Declarative Self-improving Python) for structured LLM interactions:

```python
class GenerateMetricsSpec(dspy.Signature):
    """Generate a metrics specification for evacuation analysis."""
    
    analysis_goal = dspy.InputField(desc="What to analyze")
    available_data = dspy.InputField(desc="Available data sources") 
    context = dspy.InputField(desc="Additional context")
    
    metrics_specification = dspy.OutputField(desc="Complete YAML metrics spec")
    reasoning = dspy.OutputField(desc="Explanation of choices")
```

### Context Engineering

Specialized prompts provide domain knowledge:
- **Evacuation metrics**: clearance_pct, queue_len, density
- **Event types**: route_closure, capacity_warning, emergency_alert
- **Scopes**: city-wide, edge (roads), node (stations)
- **Realistic constraints**: Population sizes, durations, severity levels

## 🚀 API Endpoints

### Generate Metrics
```bash
POST /api/agentic/metrics/generate
{
  "analysis_goal": "Analyze evacuation bottlenecks and congestion",
  "run_id": "sample_run",
  "context": "Focus on transport stations"
}
```

### Generate Scenarios
```bash
POST /api/agentic/scenarios/generate
{
  "scenario_intent": "Major flood affecting London transport during rush hour",
  "city_context": "London", 
  "constraints": "High severity, 50,000 people, 4 hours"
}
```

### Complete Analysis Package
```bash
POST /api/agentic/analysis-package
{
  "analysis_goal": "Analyze flood evacuation efficiency and safety",
  "scenario_intent": "Major Thames flood during rush hour",
  "city_context": "London"
}
```

## 📊 Example Workflows

### 1. Bottleneck Analysis
**Input**: "Find congestion bottlenecks and queue buildup points"

**Generated Metrics**:
```yaml
metrics:
  max_queue_by_edge:
    source: timeseries
    metric_key: queue_len
    operation: max_value
    group_by: scope
    filters: {scope_contains: "edge:"}
  
  congestion_duration:
    source: timeseries
    metric_key: queue_len
    operation: time_above_threshold
    args: {threshold: 20}
    post_process: {divide_by: 60}
```

### 2. Flood Scenario Generation
**Input**: "Major Thames flood affecting central London transport"

**Generated Scenario**:
```json
{
  "name": "Major Thames Flood Scenario",
  "hazard_type": "flood",
  "affected_areas": ["Westminster", "City of London", "Southwark"],
  "severity": "high",
  "duration_minutes": 240,
  "population_affected": 50000,
  "transport_disruption": 0.8,
  "parameters": {
    "compliance_rate": 0.7,
    "car_availability": 0.3,
    "walking_speed_reduction": 0.6
  }
}
```

### 3. Complete Analysis Package
**Input**: 
- Analysis Goal: "Analyze flood evacuation efficiency and safety"
- Scenario Intent: "Major Thames flood during rush hour"

**Output**:
- ✅ **Flood scenario** with realistic parameters
- ✅ **Flood-optimized metrics** (clearance time, water-affected routes)
- ✅ **Variant suggestions** (compliance rates, severity levels)
- ✅ **Executable package** ready for simulation

## 🔄 Integration with Existing System

### Metrics Builder Integration
```python
# Generated metrics work with existing MetricsBuilder
from metrics.builder import MetricsBuilder

builder = MetricsBuilder()
results = builder.calculate_metrics(run_id, generated_metrics_spec)
```

### Scenario Builder Integration  
```python
# Generated scenarios work with existing ScenarioBuilder
from scenarios.builder import ScenarioBuilder

builder = ScenarioBuilder()
variants = builder.generate_scenario_variants(base_scenario, parameter_ranges)
```

### Frontend Integration
The agentic endpoints are accessible from the frontend:
```javascript
// Generate metrics from natural language
const response = await fetch('/api/agentic/metrics/generate', {
  method: 'POST',
  body: JSON.stringify({
    analysis_goal: "Analyze evacuation efficiency",
    run_id: currentRunId
  })
});
```

## 🧪 Testing Results

The system has been thoroughly tested:

✅ **LLM Integration**: Successfully uses OpenAI GPT-4 via DSPy  
✅ **Metrics Generation**: Creates valid YAML specifications from natural language  
✅ **Scenario Generation**: Generates realistic evacuation scenarios  
✅ **Analysis Packages**: Creates complete scenario + metrics workflows  
✅ **API Endpoints**: All REST endpoints working correctly  
✅ **Execution**: Generated metrics execute successfully on sample data  

### Sample Test Results
```
🤖 Agentic Builders System Test
✅ Metrics Builder: Generated 5 metrics for evacuation efficiency
✅ Scenario Builder: Created flood scenario (50K people, 4 hours)  
✅ Analysis Package: Complete workflow with optimized metrics
✅ Execution: 3 agentic metrics calculated successfully
```

## 🔧 Configuration

### LLM Setup
The system supports multiple LLM providers:

```python
# OpenAI (preferred)
OPENAI_API_KEY=sk-proj-...

# Anthropic Claude (fallback)  
ANTHROPIC_API_KEY=sk-ant-...

# Template mode (no API key needed)
# Falls back to intelligent templates
```

### DSPy Configuration
```python
# Automatic initialization in agentic_builders.py
lm = dspy.LM(
    model='openai/gpt-4o-mini',
    api_key=settings.OPENAI_API_KEY,
    max_tokens=3000
)
dspy.configure(lm=lm)
```

## 🎯 Use Cases

### 1. **Emergency Planners**
- "Create metrics to assess hospital evacuation efficiency"
- "Generate a chemical spill scenario for industrial areas"

### 2. **Researchers**  
- "Compare flood vs fire evacuation patterns"
- "Analyze the impact of compliance rates on evacuation success"

### 3. **AI Agents**
- Agents can now specify their own evaluation criteria
- Dynamic scenario generation based on current events
- Automated analysis pipeline creation

## 🚀 Future Enhancements

### Planned Features
- **Multi-City Support**: Extend beyond London to other cities
- **Real-Time Integration**: Generate scenarios from live news feeds
- **Advanced Optimization**: Multi-objective scenario optimization
- **Evaluation Framework**: Automated testing of generated scenarios

### Integration Opportunities  
- **Emergency Chat**: LLM can generate scenarios during conversations
- **RSS Feeds**: Auto-generate scenarios from breaking news
- **Simulation Engine**: Direct integration with OSMnx evacuation simulations

## 📈 Impact

The agentic system transforms the evacuation planning tool from a **static analysis platform** to a **dynamic, AI-driven decision support system**:

- **🤖 AI Autonomy**: Agents can define their own analysis criteria
- **🎯 Domain Expertise**: Built-in evacuation planning knowledge  
- **⚡ Rapid Iteration**: Generate and test scenarios in minutes
- **🔄 Adaptive Analysis**: Metrics automatically optimized for scenario types
- **📊 Comprehensive Coverage**: Both metrics and scenarios generated together

This makes the system truly "agentic" - capable of autonomous analysis planning and execution based on natural language goals.
