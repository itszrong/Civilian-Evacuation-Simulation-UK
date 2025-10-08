# API Documentation - Civilian Evacuation Simulation System

## Table of Contents
1. [API Overview](#api-overview)
2. [Authentication & Headers](#authentication--headers)
3. [Core Simulation API](#core-simulation-api)
4. [Evacuation Planning API](#evacuation-planning-api)
5. [Agentic AI API](#agentic-ai-api)
6. [Emergency Response API](#emergency-response-api)
7. [Metrics & Analytics API](#metrics--analytics-api)
8. [Data Models](#data-models)
9. [Error Handling](#error-handling)
10. [Rate Limiting & Performance](#rate-limiting--performance)

## API Overview

**Base URL**: `http://localhost:8000` (development) / `https://your-domain.com` (production)

**API Version**: v1

**Response Format**: JSON

**Architecture**: RESTful API with Server-Sent Events (SSE) for real-time updates

## Authentication & Headers

### Required Headers
```http
Content-Type: application/json
Accept: application/json
```

### Optional Headers
```http
X-Request-ID: unique-request-identifier
X-Client-Version: frontend-version
```

## Core Simulation API

### Get Supported Cities
```http
GET /api/simulation/cities
```

**Response**:
```json
{
  "cities": [
    "westminster",
    "city of london", 
    "kensington and chelsea",
    "camden",
    "southwark",
    "hackney",
    "islington",
    "manhattan"
  ],
  "default": "westminster"
}
```

### Get City Visualization
```http
GET /api/simulation/{city}/visualisation?force_refresh=false
```

**Parameters**:
- `city` (path): City identifier (e.g., "westminster")
- `force_refresh` (query): Force new simulation if true

**Response**:
```json
{
  "city": "westminster",
  "simulation_type": "comprehensive_suite",
  "simulation_engine": "real_evacuation_science",
  "astar_routes": [
    {
      "coordinates": [[-0.1387, 51.5018], [-0.1377, 51.5047]],
      "estimated_walking_time_minutes": 17.35,
      "capacity_people_per_minute": 30.82,
      "route_id": "route_0",
      "safety_score": 0.826
    }
  ],
  "random_walks": {
    "num_walks": 10,
    "avg_path_length": 28.0,
    "density_data": {
      "x": [-0.1387, -0.1377],
      "y": [51.5018, 51.5047],
      "density": [0.8, 1.2]
    }
  },
  "network_graph": {
    "nodes": [
      {"id": "0", "x": -0.1366, "y": 51.5033}
    ],
    "edges": [
      {"source": "0", "target": "1", "length": 150.5}
    ],
    "bounds": {
      "min_x": -0.1525,
      "max_x": -0.1287,
      "min_y": 51.4894,
      "max_y": 51.5126
    }
  },
  "interactive_map_html": "<div>Folium map HTML</div>",
  "metrics": {
    "num_astar_routes": 5,
    "total_network_nodes": 100,
    "clearance_time_p50": 14.2,
    "clearance_time_p95": 38.5,
    "evacuation_efficiency": 0.72
  },
  "run_id": "uuid-string",
  "status": "completed",
  "timestamp": "2025-10-06T10:59:00Z"
}
```

### Start City Simulation
```http
POST /api/simulation/{city}/run
```

**Request Body**:
```json
{
  "num_simulations": 10,
  "num_routes": 5,
  "scenario_config": {
    "population_size": 1000,
    "emergency_type": "fire"
  }
}
```

**Response**:
```json
{
  "run_id": "uuid-string",
  "status": "started",
  "city": "westminster",
  "message": "Simulation started in background",
  "timestamp": "2025-10-06T10:59:00Z"
}
```

### Get City Status
```http
GET /api/simulation/{city}/status
```

**Response**:
```json
{
  "city": "westminster",
  "supported": true,
  "capabilities": {
    "network_type": "osmnx_street_network",
    "routing_algorithm": "a_star_pathfinding_with_real_safe_zones",
    "behavioral_modeling": "realistic_human_evacuation_behavior",
    "data_source": "openstreetmap_with_real_london_locations",
    "features": [
      "real_safe_zones",
      "population_centers", 
      "behavioral_modeling",
      "bottleneck_analysis"
    ],
    "visualisation_types": [
      "interactive_map",
      "route_analysis",
      "behavioral_heatmaps"
    ]
  },
  "last_updated": "2025-10-06T10:59:00Z"
}
```

## Evacuation Planning API

### Start Evacuation Planning Run
```http
POST /api/runs
```

**Request Body**:
```json
{
  "intent": {
    "objective": "minimise_clearance_time_and_improve_fairness",
    "city": "westminster",
    "constraints": {
      "max_scenarios": 8,
      "compute_budget_minutes": 3,
      "must_protect_pois": ["StThomasHospital", "KingsCollegeHospital"]
    },
    "hypotheses": ["Westminster cordon 2h", "Two Thames bridges closed"],
    "preferences": {
      "fairness_weight": 0.35,
      "clearance_weight": 0.5,
      "robustness_weight": 0.15
    },
    "freshness_days": 7,
    "tiers": ["gov_primary"]
  }
}
```

**Response**: Server-Sent Events (SSE) stream
```
event: run.started
data: {"run_id": "uuid", "status": "started", "timestamp": "2025-10-06T10:59:00Z"}

event: planner.scenario
data: {"scenario_id": "scenario_1", "description": "Westminster cordon scenario"}

event: worker.result  
data: {"status": "completed", "message": "Completed simulation for westminster"}

event: run.complete
data: {"run_id": "uuid", "best_scenario": "scenario_1", "status": "completed"}
```

### List Evacuation Runs
```http
GET /api/runs
```

**Response**:
```json
{
  "runs": [
    {
      "run_id": "uuid-string",
      "status": "completed",
      "created_at": "2025-10-06T10:59:00Z",
      "city": "westminster",
      "scenario_count": 3
    }
  ]
}
```

### Get Specific Run Results
```http
GET /api/runs/{run_id}
```

**Response**:
```json
{
  "run_id": "uuid-string",
  "status": "completed",
  "created_at": "2025-10-06T10:59:00Z",
  "completed_at": "2025-10-06T11:05:00Z",
  "scenario_count": 3,
  "best_scenario_id": "scenario_1",
  "city": "westminster",
  "scenarios": [
    {
      "scenario_id": "scenario_1",
      "scenario_name": "Westminster cordon scenario",
      "metrics": {
        "clearance_time": 25.5,
        "max_queue": 150,
        "fairness_index": 0.82,
        "robustness": 0.75
      },
      "status": "completed",
      "rank": 1,
      "score": 0.82,
      "description": "2-hour cordon around Westminster with bridge closures"
    }
  ],
  "decision_memo": {
    "recommendation": "Best scenario: scenario_1",
    "justification": "Optimal balance of clearance time and fairness",
    "citations": [
      {
        "title": "Emergency Planning Guidelines",
        "source": "gov.uk",
        "relevance": "Supports cordon strategy"
      }
    ],
    "confidence": 0.85
  },
  "user_intent": {
    "objective": "minimise_clearance_time_and_improve_fairness",
    "city": "westminster"
  }
}
```

## Agentic AI API

### Generate AI Scenario
```http
POST /api/agentic/generate-scenario
```

**Request Body**:
```json
{
  "scenario_intent": "Create a fire evacuation scenario for Westminster during rush hour",
  "city_context": "westminster",
  "constraints": "Must protect hospitals and schools",
  "use_framework": true,
  "framework_template": "fire_emergency"
}
```

**Response**:
```json
{
  "scenario_id": "ai_scenario_1",
  "specification": {
    "name": "Westminster Rush Hour Fire Evacuation",
    "hazard_type": "fire",
    "population_affected": 15000,
    "duration_minutes": 120,
    "severity": "high",
    "protected_areas": ["hospitals", "schools"],
    "evacuation_zones": ["zone_a", "zone_b"]
  },
  "framework_compliant": true,
  "executable": true,
  "reasoning": "AI analysis of scenario requirements and constraints"
}
```

### Generate AI Metrics
```http
POST /api/agentic/generate-metrics
```

**Request Body**:
```json
{
  "analysis_goal": "Evaluate evacuation efficiency and safety for elderly populations",
  "context": "Westminster fire evacuation scenario"
}
```

**Response**:
```json
{
  "metrics_id": "ai_metrics_1",
  "specification": {
    "metrics": {
      "elderly_evacuation_time": {
        "description": "Time to evacuate elderly population",
        "unit": "minutes",
        "target": "< 30 minutes"
      },
      "accessibility_compliance": {
        "description": "Percentage of accessible evacuation routes",
        "unit": "percentage", 
        "target": "> 95%"
      }
    }
  },
  "reasoning": "Focused on vulnerable population needs"
}
```

### Create Analysis Package
```http
POST /api/agentic/analysis-package
```

**Request Body**:
```json
{
  "analysis_goal": "Comprehensive Westminster evacuation analysis",
  "scenario_intent": "Multi-hazard evacuation planning",
  "city_context": "westminster",
  "use_framework": true,
  "framework_template": "comprehensive_evacuation"
}
```

**Response**:
```json
{
  "package_id": "analysis_package_1",
  "scenarios": [
    {
      "scenario_id": "scenario_1",
      "specification": {...}
    }
  ],
  "metrics": {
    "metrics_id": "metrics_1", 
    "specification": {...}
  },
  "framework_compliant": true,
  "executable_scenarios": [...],
  "execution_results": {
    "run_id": "uuid",
    "status": "completed",
    "real_metrics": {...}
  },
  "has_real_metrics": true
}
```

### Execute Framework Scenario
```http
POST /api/agentic/execute-framework-scenario
```

**Request Body**:
```json
{
  "package_id": "analysis_package_1"
}
```

**Response**:
```json
{
  "execution_id": "exec_1",
  "status": "completed",
  "results": {
    "scenario_results": [...],
    "real_metrics": {...},
    "simulation_data": {...}
  }
}
```

## Emergency Response API

### Generate Emergency Plan
```http
POST /api/emergency/generate-plan
```

**Request Body**:
```json
{
  "city": "westminster",
  "run_id": "uuid-string"
}
```

**Response**:
```json
{
  "plan_id": "emergency_plan_1",
  "city": "westminster",
  "emergency_type": "fire",
  "evacuation_procedures": [
    {
      "step": 1,
      "action": "Activate emergency alert system",
      "timeline": "0-5 minutes",
      "responsible": "Emergency Control Centre"
    }
  ],
  "resource_allocation": {
    "emergency_vehicles": 15,
    "evacuation_centers": 3,
    "personnel_required": 50
  },
  "communication_plan": {
    "public_alerts": ["mobile", "radio", "social_media"],
    "coordination_channels": ["emergency_radio", "secure_comms"]
  }
}
```

### Emergency Chat
```http
POST /api/emergency/chat
```

**Request Body**:
```json
{
  "city": "westminster",
  "run_id": "uuid-string",
  "user_role": "emergency_coordinator",
  "message": "What are the priority evacuation routes?",
  "conversation_history": [
    {
      "role": "user",
      "content": "Previous message",
      "timestamp": "2025-10-06T10:59:00Z"
    }
  ]
}
```

**Response**:
```json
{
  "response": "Based on the Westminster simulation, priority routes are...",
  "suggestions": [
    "Review route capacity constraints",
    "Check emergency vehicle access"
  ],
  "relevant_data": {
    "routes": ["route_1", "route_2"],
    "bottlenecks": ["intersection_a"]
  }
}
```

### Send Government Alert
```http
POST /api/notifications/government-alert
```

**Request Body**:
```json
{
  "message": "🚨 EMERGENCY EVACUATION ALERT\nRun ID: uuid\nLocation: Westminster\nImmediate action required.",
  "priority": "critical"
}
```

**Response**:
```json
{
  "alert_id": "alert_1",
  "status": "sent",
  "delivery_method": "whatsapp",
  "timestamp": "2025-10-06T10:59:00Z"
}
```

## Metrics & Analytics API

### Get Dashboard Metrics
```http
GET /api/metrics
```

**Response**:
```json
{
  "metrics": {
    "total_simulations": 150,
    "avg_clearance_time": 25.5,
    "cities_analyzed": 8,
    "success_rate": 0.95
  },
  "recent_activity": [
    {
      "run_id": "uuid",
      "city": "westminster", 
      "timestamp": "2025-10-06T10:59:00Z"
    }
  ]
}
```

### Calculate Metrics
```http
POST /api/metrics/calculate
```

**Request Body**:
```json
{
  "simulation_data": {
    "routes": [...],
    "agent_paths": [...],
    "network_data": {...}
  },
  "metrics_specification": {
    "clearance_time": true,
    "fairness_index": true,
    "bottleneck_analysis": true
  }
}
```

**Response**:
```json
{
  "calculated_metrics": {
    "clearance_time_p50": 18.5,
    "clearance_time_p95": 35.2,
    "fairness_index": 0.78,
    "bottleneck_count": 3,
    "evacuation_efficiency": 0.82
  },
  "analysis": {
    "bottlenecks": [
      {
        "location": "Westminster Bridge",
        "severity": "high",
        "impact": "15% capacity reduction"
      }
    ]
  }
}
```

## Data Models

### UserIntent Model
```typescript
interface UserIntent {
  objective: string;
  city: string;
  constraints: {
    max_scenarios: number;
    compute_budget_minutes: number;
    must_protect_pois: string[];
  };
  hypotheses: string[];
  preferences: {
    fairness_weight: number;
    clearance_weight: number;
    robustness_weight: number;
  };
  freshness_days: number;
  tiers: string[];
}
```

### SimulationResult Model
```typescript
interface SimulationResult {
  city: string;
  simulation_type: string;
  simulation_engine: string;
  astar_routes: Route[];
  random_walks: RandomWalkData;
  network_graph: NetworkGraph;
  interactive_map_html?: string;
  metrics: SimulationMetrics;
  run_id: string;
  status: string;
  timestamp: string;
}
```

### Route Model
```typescript
interface Route {
  coordinates: [number, number][];
  estimated_walking_time_minutes: number;
  capacity_people_per_minute: number;
  route_id: string;
  safety_score: number;
}
```

### NetworkGraph Model
```typescript
interface NetworkGraph {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
  bounds: {
    min_x: number;
    max_x: number;
    min_y: number;
    max_y: number;
  };
}

interface NetworkNode {
  id: string;
  x: number;
  y: number;
}

interface NetworkEdge {
  source: string;
  target: string;
  length: number;
}
```

## Error Handling

### Standard Error Response
```json
{
  "detail": "Error description",
  "error_code": "SIMULATION_FAILED",
  "timestamp": "2025-10-06T10:59:00Z",
  "request_id": "uuid-string"
}
```

### Common Error Codes

| Code | Status | Description |
|------|--------|-------------|
| `CITY_NOT_SUPPORTED` | 400 | Requested city not in supported list |
| `SIMULATION_FAILED` | 500 | Simulation execution failed |
| `INVALID_PARAMETERS` | 400 | Request parameters validation failed |
| `RESOURCE_NOT_FOUND` | 404 | Requested resource not found |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `GRAPH_LOAD_FAILED` | 500 | Failed to load OSMnx graph |
| `AGENTIC_GENERATION_FAILED` | 500 | AI scenario/metrics generation failed |

### Error Handling Examples

#### City Not Supported
```http
GET /api/simulation/invalid_city/visualisation
```
```json
{
  "detail": "Unsupported city: invalid_city. Supported cities: westminster, city of london, ...",
  "error_code": "CITY_NOT_SUPPORTED"
}
```

#### Simulation Failed
```http
POST /api/simulation/westminster/run
```
```json
{
  "detail": "Failed to load street network for westminster after trying multiple geocoding strategies",
  "error_code": "SIMULATION_FAILED"
}
```

## Rate Limiting & Performance

### Rate Limits
- **Simulation Endpoints**: 10 requests/minute per IP
- **Visualization Endpoints**: 30 requests/minute per IP  
- **Agentic AI Endpoints**: 5 requests/minute per IP
- **Emergency Endpoints**: 20 requests/minute per IP

### Performance Guidelines
- **Simulation Response Time**: < 30 seconds for cached results
- **Visualization Loading**: < 5 seconds for pre-computed maps
- **AI Generation**: < 60 seconds for scenario/metrics generation
- **Real-time Updates**: SSE events within 1 second

### Caching Strategy
- **Graph Cache**: OSMnx graphs cached for 24 hours
- **Simulation Results**: Cached for 1 hour
- **Visualization Data**: Cached for 30 minutes
- **AI Responses**: Cached for 15 minutes

### Optimization Tips
1. **Use force_refresh=false** for visualization endpoints when possible
2. **Cache simulation results** on client side for repeated access
3. **Implement request debouncing** for real-time interactions
4. **Use SSE for long-running operations** instead of polling
5. **Batch multiple requests** when possible

---

This API documentation provides comprehensive coverage of all endpoints, data models, and integration patterns for the Civilian Evacuation Simulation System.
