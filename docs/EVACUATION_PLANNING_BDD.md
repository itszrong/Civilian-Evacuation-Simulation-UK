# Civilian Evacuation Planning Tool - BDD Specifications

## Overview
This document defines the behavior-driven development (BDD) specifications for the Civilian Evacuation Planning Tool, a multi-agent system for government emergency planning.

## System Context
**Target Users**: Cabinet Office - Civil Contingencies Secretariat, London Resilience  
**Purpose**: Real-time agentic evacuation planning with streaming results  
**Technology**: React + GOV.UK Frontend, FastAPI + Multi-Agent System

---

## Feature: Multi-Agent Evacuation Planning Workflow

### Scenario: Emergency Planner starts evacuation planning for Central London
```gherkin
Given I am an emergency planner for the Cabinet Office
And I have access to the Civilian Evacuation Planning Tool
When I access the "Plan & Run" page
Then I should see a government-styled interface
And I should see city selection options for "London" and "Manhattan"
And I should see evacuation planning configuration options
```

### Scenario: Configuring evacuation parameters
```gherkin
Given I am on the Plan & Run page
When I select "London - Real street network" as the city
And I set the objective to "minimise_clearance_time_and_improve_fairness"
And I configure constraints:
  | Parameter | Value |
  | Max Scenarios | 8 |
  | Compute Budget | 3 minutes |
  | Protected POIs | StThomasHospital, KingsCollegeHospital |
And I set optimization weights:
  | Weight | Value |
  | Clearance | 0.5 |
  | Fairness | 0.35 |
  | Robustness | 0.15 |
And I add hypotheses:
  | Hypothesis |
  | Westminster cordon 2h |
  | Two Thames bridges closed |
Then the form should validate successfully
And the "Start evacuation planning" button should be enabled
```

### Scenario: Real-time streaming evacuation planning workflow
```gherkin
Given I have configured valid evacuation parameters
When I click "Start evacuation planning"
Then I should see a progress indicator appear
And I should receive real-time updates via Server-Sent Events
And the workflow should proceed through these phases:
  | Phase | Agent | Expected Update |
  | Planning | Planner | "Planning evacuation scenarios..." |
  | Simulation | Worker | "Running multi-agent simulations..." |
  | Evaluation | Judge | "Ranking and evaluating scenarios..." |
  | Explanation | Explainer | "Generating decision memo..." |
And each phase should show progress percentage
And I should see detailed event logs in an expandable section
```

### Scenario: Successful completion of evacuation planning
```gherkin
Given the evacuation planning workflow is running
When all agents complete their tasks successfully
Then I should see "Evacuation planning complete" message
And I should receive a success notification
And the progress bar should show 100%
And the system should generate:
  | Artifact | Description |
  | Scenarios | Generated evacuation scenarios |
  | Results | Simulation results with metrics |
  | Rankings | Judge's scenario evaluations |
  | Decision Memo | Explainer's justification with citations |
```

---

## Feature: Multi-City Support

### Scenario: London evacuation planning
```gherkin
Given I select "London - Real street network" as the city
When I start evacuation planning
Then the system should use:
  | Component | Technology |
  | Network | OSMnx street network |
  | Routing | A* pathfinding |
  | Features | Real streets, traffic-aware routing |
And simulation should handle real London geography
```

### Scenario: Manhattan evacuation planning
```gherkin
Given I select "Manhattan - Grid simulation" as the city
When I start evacuation planning
Then the system should use:
  | Component | Technology |
  | Network | Grid-based simulation |
  | Routing | Biased random walk |
  | Features | Density analysis, heatmap generation |
And simulation should handle Manhattan-style grid layout
```

---

## Feature: Government Design System Compliance

### Scenario: GOV.UK styling and accessibility
```gherkin
Given I access any page of the system
Then the interface should use official GOV.UK Design System
And all components should be WCAG 2.1 AA compliant
And I should see proper government branding
And keyboard navigation should work throughout
```

### Scenario: Department branding toggle
```gherkin
Given I am on any page with the header
When I use the department toggle dropdown
Then I should be able to switch between:
  | Department | Branding |
  | Cabinet Office | HM Government / Civilian Evacuation Planning Tool |
  | London Resilience | London Resilience / London Evacuation Planning |
And the styling should update accordingly
```

---

## Feature: API Endpoint Integration

### Scenario: City data retrieval
```gherkin
Given the frontend loads
When it requests available cities
Then it should call GET /api/simulation/cities
And receive:
```json
{
  "cities": ["london", "manhattan"],
  "default": "london",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### Scenario: Starting evacuation planning run
```gherkin
Given I have configured evacuation parameters
When I start a planning run
Then the frontend should POST to /api/runs with:
```json
{
  "intent": {
    "objective": "minimise_clearance_time_and_improve_fairness",
    "city": "london",
    "constraints": {
      "max_scenarios": 8,
      "compute_budget_minutes": 3,
      "must_protect_pois": ["StThomasHospital", "KingsCollegeHospital"]
    },
    "preferences": {
      "clearance_weight": 0.5,
      "fairness_weight": 0.35,
      "robustness_weight": 0.15
    },
    "hypotheses": ["Westminster cordon 2h", "Two Thames bridges closed"],
    "freshness_days": 7,
    "tiers": ["gov_primary"]
  },
  "city": "london"
}
```

### Scenario: Real-time event streaming
```gherkin
Given a planning run has started
When the backend processes the request
Then it should stream Server-Sent Events in this format:
```
event: run.started
data: {"run_id": "r_20241201_143022_abc123", "status": "started"}

event: planner.progress  
data: {"status": "completed", "num_scenarios": 8}

event: worker.result
data: {"scenario_id": "scenario_1", "metrics": {...}}

event: judge.summary
data: {"ranking": [...], "best_scenario_id": "scenario_3"}

event: explainer.answer
data: {"answer": "...", "citations": [...]}

event: run.complete
data: {"run_id": "r_20241201_143022_abc123", "status": "completed"}
```

---

## Feature: Error Handling and Resilience

### Scenario: Invalid evacuation parameters
```gherkin
Given I am configuring evacuation parameters
When I set preference weights that don't sum to 1.0
Then I should see a validation error
And the "Start evacuation planning" button should be disabled
And I should see helpful error message: "Weights must sum to 1.0"
```

### Scenario: Backend service unavailable
```gherkin
Given the backend service is unavailable
When I try to start evacuation planning
Then I should see an error notification
And I should see message: "Failed to start evacuation planning run"
And the system should not leave me in an inconsistent state
```

### Scenario: Streaming connection interrupted
```gherkin
Given a planning run is in progress with streaming updates
When the SSE connection is interrupted
Then the frontend should handle the disconnection gracefully
And show appropriate error messaging
And allow me to check run status separately
```

---

## Technical Acceptance Criteria

### API Endpoint Compliance
- [ ] GET /api/simulation/cities returns city list
- [ ] POST /api/runs accepts RunRequest schema and streams SSE
- [ ] All endpoints follow FastAPI + Pydantic patterns
- [ ] CORS properly configured for frontend-backend communication

### Frontend-Backend Data Flow
- [ ] Frontend sends UserIntent matching backend schema
- [ ] SSE events parsed correctly in React
- [ ] Real-time progress updates work smoothly
- [ ] Error states handled and displayed properly

### Government Standards
- [ ] GOV.UK Design System components used throughout
- [ ] WCAG 2.1 AA accessibility compliance
- [ ] Official government typography and spacing
- [ ] Proper service navigation and breadcrumbs

### Multi-Agent System Integration
- [ ] Planner generates realistic evacuation scenarios
- [ ] Worker simulates scenarios using city-appropriate algorithms
- [ ] Judge ranks scenarios based on user preferences
- [ ] Explainer provides citations and justifications
- [ ] All agent outputs stored for audit trail

### Performance and Reliability
- [ ] Streaming responses work without blocking UI
- [ ] System handles multiple concurrent planning runs
- [ ] Error recovery and retry mechanisms function
- [ ] All artifacts properly stored and retrievable

---

## Test Scenarios Priority

**High Priority (MVP)**
1. ✅ Basic evacuation planning workflow end-to-end
2. ✅ GOV.UK styling and government branding
3. ✅ Real-time streaming progress updates
4. 🔄 API endpoint alignment and data validation

**Medium Priority**
1. Multi-city support (London + Manhattan)
2. Error handling and resilience
3. Department branding toggle
4. Accessibility compliance testing

**Low Priority (Enhancement)**
1. Performance optimization
2. Advanced error recovery
3. Additional city support
4. Enhanced visualisations

---

This BDD specification serves as both documentation and acceptance criteria for the Civilian Evacuation Planning Tool development.
