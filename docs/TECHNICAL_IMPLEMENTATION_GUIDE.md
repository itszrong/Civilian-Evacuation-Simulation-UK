# Technical Implementation Guide - Real Simulation Data

## Quick Reference for Developers

This guide provides technical details for developers working with the real simulation data system.

## Architecture Overview

### Data Flow Pipeline

```
Real Simulation Engine → API Layer → Frontend Components → User Interface
        ↓                   ↓            ↓                    ↓
OSMnx + A* Algorithm    JSON Response   Direct Extraction   Varied Metrics
Behavioral Modeling     10 Scenarios    No Processing       Real Values
Network Analysis        Real Metrics    Single Source       Science-Based
```

## API Endpoints

### Primary Endpoints (Use These)

| Endpoint | Method | Purpose | Returns |
|----------|--------|---------|---------|
| `/api/runs/{run_id}` | GET | Get complete run with scenarios | Real varied metrics |
| `/api/simulation/{city}/visualisation` | GET | Get simulation visualization | Real network data |
| `/api/runs` | GET | List all simulation runs | Run metadata |

### Deprecated Endpoints (Do Not Use)

| Endpoint | Issue | Replacement |
|----------|-------|-------------|
| `/api/runs/{run_id}/scenarios` | Returns null metrics | Use primary `/api/runs/{run_id}` |
| `/api/runs/{run_id}/scenarios.json` | File not found | Use primary API endpoint |

## Data Structures

### Real Scenario Structure

```typescript
interface ScenarioResult {
  scenario_id: string;
  scenario_name: string;
  metrics: {
    clearance_time: number;        // 13.1 - 79.5 minutes (REAL)
    fairness_index: number;        // 0.443 - 0.647 (Gini coefficient)
    robustness: number;            // 0.907 - 0.98 (network resilience)
    max_queue: number;             // Actual queue calculations
    total_evacuated: number;       // Population counts
    network_density: number;       // OSMnx analysis
  };
  status: 'completed';
  duration_ms: number;             // Actual simulation time
}
```

### Expected Value Ranges

| Metric              | Real Range         |
|---------------------|-------------------|
| **Clearance Time**  | 13.1 - 79.5 min   |
| **Fairness Index**  | 0.443 - 0.647     |
| **Robustness**      | 0.907 - 0.98      |
| **Population**      | 50,000 - 55,000   |

## Frontend Implementation Patterns

### ✅ Correct Data Extraction

```typescript
// Use actual simulation results
const clearanceTime = scenario?.metrics?.clearance_time || 0;
const fairnessIndex = scenario?.metrics?.fairness_index || 0;
const robustness = scenario?.metrics?.robustness || 0;

// For scenario comparison
const generateScenarioComparison = () => {
  return scenarioResults.map((scenario, index) => ({
    scenario: scenario?.scenario_name || `Scenario ${index + 1}`,
    clearance_time: scenario?.metrics?.clearance_time || 0,  // REAL values
    fairness_index: scenario?.metrics?.fairness_index || 0,  // REAL values
    robustness: scenario?.metrics?.robustness || 0,          // REAL values
  }));
};
```


### Data Loading Best Practices

```typescript
// Single source of truth - use primary API only
const fetchRunData = async (runId: string) => {
  const response = await fetch(`${API_CONFIG.baseUrl}/api/runs/${runId}`);
  if (!response.ok) throw new Error('Failed to fetch run data');
  
  const data = await response.json();
  
  // Use scenarios directly - no complex processing needed
  return {
    ...data,
    scenarios: data.scenarios || []  // Already contains real metrics
  };
};
```

## Backend Implementation Details

### Real Simulation Execution

```python
# backend/services/multi_city_simulation.py
async def _run_multiple_varied_simulations_async(
    city: str, 
    num_scenarios: int = 10
) -> List[Dict]:
    """Generate real varied scenarios with actual simulation results"""
    
    scenarios = []
    for i in range(num_scenarios):
        # Generate unique scenario parameters
        scenario_config = await _generate_unique_scenario_config(i)
        
        # Run REAL simulation with OSMnx and A* pathfinding
        simulation_result = await RealEvacuationSimulation.run_real_simulation(
            city=city,
            config=scenario_config
        )
        
        # Extract REAL calculated metrics
        real_metrics = {
            'clearance_time': simulation_result.clearance_time,      # From A* calculation
            'fairness_index': simulation_result.fairness_index,     # From Gini coefficient
            'robustness': simulation_result.robustness,             # From network analysis
            'max_queue': simulation_result.max_queue,               # From queue simulation
            'total_evacuated': simulation_result.total_evacuated,   # From population model
        }
        
        scenarios.append({
            'scenario_name': f'Scenario {i + 1}',
            'metrics': real_metrics,  # REAL values
            'expected_clearance_time': real_metrics['clearance_time']  # Store real value
        })
    
    return scenarios
```

### API Response Format

```python
# backend/api/simulation.py
@app.get("/api/runs/{run_id}")
async def get_run_details(run_id: str):
    """Return complete run with real scenario metrics"""
    
    # Get real simulation results
    scenarios = await get_real_scenarios(run_id)
    
    return {
        'run_id': run_id,
        'status': 'completed',
        'scenario_count': len(scenarios),
        'scenarios': [
            {
                'scenario_id': f'{run_id}_scenario_{i}',
                'scenario_name': scenario['scenario_name'],
                'metrics': scenario['metrics'],  # REAL calculated values
                'status': 'completed'
            }
            for i, scenario in enumerate(scenarios)
        ]
    }
```

## Component Integration Guide

### Borough Dashboard Implementation

```typescript
// Calculate averaged metrics across all scenarios
const calculateBoroughMetrics = (scenarios: ScenarioResult[]) => {
  const validScenarios = scenarios.filter(s => s.metrics && s.metrics.clearance_time);
  
  if (validScenarios.length === 0) return null;
  
  return {
    avgClearance: validScenarios.reduce((sum, s) => 
      sum + s.metrics.clearance_time, 0) / validScenarios.length,
    avgFairness: validScenarios.reduce((sum, s) => 
      sum + s.metrics.fairness_index, 0) / validScenarios.length,
    avgRobustness: validScenarios.reduce((sum, s) => 
      sum + s.metrics.robustness, 0) / validScenarios.length,
    scenarioCount: validScenarios.length
  };
};
```

### Scenario Comparison Charts

```typescript
// Generate chart data with real varied values
const generateChartData = (scenarios: ScenarioResult[]) => {
  return scenarios.map((scenario, index) => ({
    label: scenario.scenario_name || `Scenario ${index + 1}`,
    clearance: scenario.metrics.clearance_time,    // Real: 45.7, 33.3, 60.5, etc.
    fairness: scenario.metrics.fairness_index,     // Real: 0.443, 0.498, 0.536, etc.
    robustness: scenario.metrics.robustness,       // Real: 0.98, 0.954, 0.914, etc.
  }));
};
```

## Debugging and Validation

### Console Logging for Verification

```typescript
// Add debug logging to verify real data
console.log('🔍 Scenario metrics verification:', scenarios.map(s => ({
  name: s.scenario_name,
  clearance: s.metrics?.clearance_time,
  fairness: s.metrics?.fairness_index,
  robustness: s.metrics?.robustness,
  isReal: s.metrics?.clearance_time !== undefined && 
          s.metrics?.clearance_time > 0 &&
          s.metrics?.clearance_time < 200  // Reasonable range
})));
```

### Data Detection

```typescript
const validateRealData = (scenarios: ScenarioResult[]): boolean => {
  // Check for varied values (not identical)
  const clearanceTimes = scenarios.map(s => s.metrics?.clearance_time).filter(Boolean);
  const hasVariation = new Set(clearanceTimes).size > 1;
  
  // Check for reasonable value ranges
  const inReasonableRange = clearanceTimes.every(time => time > 10 && time < 200);
  
  // Check for non-null metrics
  const hasRealMetrics = scenarios.every(s => 
    s.metrics && 
    s.metrics.clearance_time !== null && 
    s.metrics.fairness_index !== null
  );
  
  return hasVariation && inReasonableRange && hasRealMetrics;
};
```

## Performance Considerations

### Efficient Data Loading

```typescript
// Use parallel API calls for multiple runs
const fetchMultipleRuns = async (runIds: string[]) => {
  const promises = runIds.map(id => 
    fetch(`${API_CONFIG.baseUrl}/api/runs/${id}`)
      .then(r => r.json())
  );
  
  return Promise.all(promises);
};

// Cache real simulation results
const simulationCache = new Map<string, ScenarioResult[]>();

const getCachedOrFetch = async (runId: string) => {
  if (simulationCache.has(runId)) {
    return simulationCache.get(runId);
  }
  
  const data = await fetchRunData(runId);
  simulationCache.set(runId, data.scenarios);
  return data.scenarios;
};
```

### Avoiding Performance Issues

```typescript
// DON'T: Infinite re-renders
useEffect(() => {
  loadData();
}, [scenario.scenario_id, runResult.run_id, city]); // Dependencies cause loops

// DO: Controlled loading
useEffect(() => {
  loadData();
}, []); // No dependencies

// DON'T: Auto-generate simulations
if (!visualizationData) {
  await fetch(`/api/simulation/${city}?force_refresh=true`); // Causes infinite loops
}

// DO: User-controlled generation
const handleRunSimulation = async () => {
  setLoading(true);
  await fetch(`/api/simulation/${city}?create_complete=true`);
  setLoading(false);
};
```

## Error Handling

### Robust Error Boundaries

```typescript
const handleDataLoading = async (runId: string) => {
  try {
    const response = await fetch(`${API_CONFIG.baseUrl}/api/runs/${runId}`);
    
    if (!response.ok) {
      throw new Error(`Failed to fetch run data: ${response.status}`);
    }
    
    const data = await response.json();
    
    // Validate real data
    if (!validateRealData(data.scenarios)) {
      console.warn('⚠️ Received potentially old data, check simulation pipeline');
    }
    
    return data;
    
  } catch (error) {
    console.error('❌ Data loading failed:', error);
    // Show user-friendly error, don't auto-retry
    setError('Failed to load simulation data. Please try again.');
    return null;
  }
};
```

## Testing Guidelines

### Unit Test Examples

```typescript
describe('Real Data Validation', () => {
  test('should detect real scenario data', () => {
    const realScenarios = [
      { metrics: { clearance_time: 45.7, fairness_index: 0.443 } },
      { metrics: { clearance_time: 33.3, fairness_index: 0.498 } },
      { metrics: { clearance_time: 60.5, fairness_index: 0.536 } }
    ];
    
    expect(validateRealData(realScenarios)).toBe(true);
  });
```

## Migration Checklist

When working with the system, ensure:

- [ ] No `Math.random()` calls in data generation
- [ ] Using primary API endpoints only
- [ ] Extracting from `scenario.metrics.*` not `scenario.expected_*`
- [ ] Validating data variation across scenarios
- [ ] Implementing proper error handling
- [ ] Adding debug logging for data flow
- [ ] Testing with real simulation runs
- [ ] Avoiding infinite polling loops

## Support and Troubleshooting

### Common Issues

1. **Identical Values Across Scenarios**
   - Check: Using `metrics.clearance_time` not `expected_clearance_time`
   - Check: Not calling corrupted `/scenarios` endpoint

2. **N/A Values in Dashboard**
   - Check: Fetching detailed run data with scenarios
   - Check: Proper metrics extraction from nested structure

3. **Infinite Loading/Polling**
   - Check: useEffect dependencies
   - Check: Not auto-triggering new simulations

### Debug Commands

```bash
# Verify API returns varied data
curl -s "http://localhost:8000/api/runs/{run_id}" | jq '.scenarios[0:3] | .[] | {name: .scenario_name, clearance: .metrics.clearance_time}'

# Check for corrupted endpoints
curl -s "http://localhost:8000/api/runs/{run_id}/scenarios" | jq '.scenarios[0].metrics'  # Should not be used

# Verify scenario count
curl -s "http://localhost:8000/api/runs/{run_id}" | jq '.scenarios | length'  # Should be 10
```

---

**Document Version**: 1.0  
**Last Updated**: October 7, 2025  
**Status**: Implementation Complete
