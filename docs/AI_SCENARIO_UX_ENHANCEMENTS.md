# AI Scenario Generation UX Enhancements

**Date**: January 7, 2025  
**Status**: Enhancement Roadmap  
**Context**: Post-Refactoring UX Improvements

---

## Overview

After completing the orchestrator refactoring, several UX enhancements have been identified to improve the AI scenario generation experience.

---

## 🎯 Enhancement 1: Dynamic Evacuation Origin Marker

### Current Behavior
- Evacuation center pin is placed at city centroid for all scenarios
- Pin location: `[centroid[0], centroid[1]]`
- Does not reflect actual evacuation origin

### Desired Behavior
- Pin should move to actual `origin_node` for each scenario
- Different scenarios = different pin locations
- Shows where evacuation actually starts

### Implementation
**File**: `backend/services/simulation/simulation_executor_service.py`

```python
# In run_multiple_scenarios(), replace:
folium.Marker([centroid[0], centroid[1]], 
              popup=f"{city.title()} - Scenario {scenario_idx+1}",
              ...)

# With:
origin_coords = [graph.nodes[origin_node]['y'], graph.nodes[origin_node]['x']]
folium.Marker(origin_coords,
              popup=f"{city.title()} - Evacuation Origin (Scenario {scenario_idx+1})",
              icon=folium.Icon(color='red', icon='exclamation-sign'))  # Red for hazard location
```

---

## 🎯 Enhancement 2: Expose AI Intent + Framework Template

### Current Behavior
Scenarios only show framework template output:
```python
scenario = {
    'name': 'Thames fluvial flood – pan-London RWC',
    'description': 'Mass evacuation scenario',
    'hazard_type': 'flood',
    'template_key': 'mass_fluvial_flood_rwc',
    ...
}
```

### Desired Behavior
Show BOTH user intent AND chosen framework:
```python
scenario = {
    'name': 'Thames fluvial flood – pan-London RWC',
    'description': 'Mass evacuation scenario',
    'hazard_type': 'flood',
    'template_key': 'mass_fluvial_flood_rwc',
    
    # NEW: AI Intent
    'ai_intent': 'Test evacuation efficiency for Westminster with security considerations focusing on transport hub coordination accounting for tourist populations while protecting Houses of Parliament',
    
    # NEW: Template Selection Reasoning
    'template_selection_reason': 'Chose Thames flood template due to proximity to river, high-density urban area, and need for coordinated transport hub evacuation',
    ...
}
```

### Implementation
**Files to Modify**:
1. `backend/agents/agentic_builders.py` - Add intent to scenario generation
2. `backend/services/simulation/simulation_executor_service.py` - Include intent in results
3. Frontend components - Display intent in UI

---

## 🎯 Enhancement 3: Frontend Clarity for Builders

### Current Issues
- Scenario Builder and Metrics Builder workflows unclear
- Users don't understand how AI generates scenarios
- Connection between intent → template → simulation unclear

### Desired Improvements

#### A. Scenario Builder UI
Add visual flow diagram:
```
User Intent → AI Analysis → Framework Template Selection → Simulation Parameters → Run Simulation
```

#### B. Metrics Builder UI
Show calculation pipeline:
```
Network Analysis → Route Efficiency → Fairness (Gini) → Robustness → Aggregation
```

#### C. Add Explainer Cards
**Scenario Builder Card**:
```
"The Scenario Builder uses AI to:
1. Analyze your evacuation intent
2. Match to framework templates (RWC, CBRN, etc.)
3. Generate realistic simulation parameters
4. Run varied evacuation patterns"
```

**Metrics Builder Card**:
```
"The Metrics Builder calculates:
- Clearance Times: How long to evacuate (P50/P95)
- Fairness Index: Route distribution equity (Gini coefficient)
- Robustness: Network resilience to disruptions
- Efficiency: Overall evacuation effectiveness"
```

### Implementation
**Files to Create/Modify**:
1. `frontend/src/components/ScenarioBuilderExplainer.tsx` - NEW
2. `frontend/src/components/MetricsBuilderExplainer.tsx` - NEW
3. `frontend/src/components/PlanAndRunGovUK.tsx` - Add explainers
4. `frontend/src/components/ResultsGovUK.tsx` - Show intent + template

---

## 🎯 Enhancement 4: AI Simulation Chat Interface

### Current Behavior
- "AI Simulation" button triggers scenario generation
- No interactive chat
- No conversational refinement

### Desired Behavior
Replace button with interactive chat modal:

```tsx
// When user clicks "AI Simulation" button:
<ChatModal>
  <ChatHistory>
    <BotMessage>
      👋 Hi! I'll help you create evacuation scenarios for Westminster.
      What type of evacuation situation would you like to simulate?
      
      Examples:
      • "Flood evacuation with tourist considerations"
      • "Chemical incident near transport hubs"
      • "Building fire with limited exits"
    </BotMessage>
    
    <UserMessage>
      Test evacuation efficiency for Westminster with security 
      considerations focusing on transport hub coordination accounting 
      for tourist populations while protecting Houses of Parliament
    </UserMessage>
    
    <BotMessage>
      ✅ Great! I'll create scenarios based on your intent.
      
      I'm analyzing:
      - Security considerations (high-profile targets)
      - Transport hub dependencies (rail/tube stations)
      - Tourist population dynamics (variable density)
      - Critical infrastructure (Parliament)
      
      Matching to framework templates...
      
      📋 Recommended scenarios:
      1. Thames fluvial flood (mass evacuation template)
      2. Central sudden impact (security template)
      3. Transport hub disruption (coordination template)
      
      Shall I generate these 3 scenarios? [Yes] [Customize]
    </BotMessage>
