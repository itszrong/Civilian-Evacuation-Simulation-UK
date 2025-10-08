# Civilian Evacuation Simulation System - Complete Architecture Documentation

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture Components](#architecture-components)
3. [Data Flow](#data-flow)
4. [City Support & Geographic Data](#city-support--geographic-data)
5. [Simulation Engines](#simulation-engines)
6. [API Endpoints](#api-endpoints)
7. [Frontend Components](#frontend-components)
8. [Agentic AI System](#agentic-ai-system)
9. [Storage & Caching](#storage--caching)
10. [Visualization System](#visualization-system)
11. [Emergency Response Integration](#emergency-response-integration)
12. [Deployment & Configuration](#deployment--configuration)

## System Overview

The Civilian Evacuation Simulation System is a comprehensive emergency planning platform that combines real-world geographic data, advanced pathfinding algorithms, and AI-powered scenario generation to create realistic evacuation simulations for urban areas.

### Key Capabilities
- **Real Street Network Analysis**: Uses OpenStreetMap data via OSMnx for authentic street layouts
- **Multi-Algorithm Simulation**: A* pathfinding, biased random walks, and behavioral modeling
- **AI-Powered Planning**: Agentic system for scenario and metrics generation
- **Interactive Visualization**: Folium maps with real-time route overlays and borough boundaries
- **Emergency Response Integration**: WhatsApp alerts and emergency chat assistance
- **Multi-City Support**: London boroughs, Manhattan, and extensible to other cities

## Architecture Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React/TypeScript)              │
├─────────────────────────────────────────────────────────────┤
│  • PlanAndRunGovUK: Main planning interface               │
│  • CitySpecificVisualisation: Map & network display       │
│  • ResultsGovUK: Analysis results & decision memos        │
│  • AgenticPlannerPanel: AI scenario generation            │
│  • EmergencyChatPanel: Real-time emergency assistance     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Backend API (FastAPI)                    │
├─────────────────────────────────────────────────────────────┤
│  • /api/simulation: Core simulation endpoints              │
│  • /api/runs: Evacuation planning runs                     │
│  • /api/agentic: AI-powered scenario generation           │
│  • /api/emergency: Emergency response & chat              │
│  • /api/metrics: Performance analysis                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Simulation Services                       │
├─────────────────────────────────────────────────────────────┤
│  • MultiCityEvacuationService: Main simulation engine     │
│  • NetworkGraphService: OSMnx integration                 │
│  • RouteCalculatorService: A* pathfinding                 │
│  • RealEvacuationSimulation: Behavioral modeling          │
│  • AgenticBuilderService: AI scenario generation          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Data & Storage                           │
├─────────────────────────────────────────────────────────────┤
│  • OSMnx: Real street network data                        │
│  • Local S3: Simulation results & artifacts              │
│  • Graph Cache: Pre-loaded city networks                  │
│  • RSS Feeds: Real-time emergency data                    │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Evacuation Planning Run Flow
```
User Selects City → Frontend Updates Intent → POST /api/runs → 
MultiCityEvacuationService → OSMnx Graph Loading → 
A* Route Calculation → Behavioral Simulation → 
Folium Map Generation → Results Storage → Frontend Display
```

### 2. Quick Simulation Flow  
```
User Clicks Visualisation → GET /api/simulation/{city}/visualisation →
_run_uk_city_simulation → Real Street Network Analysis →
Interactive Map Generation → Immediate Display
```

### 3. Agentic Planning Flow
```
User Describes Scenario → POST /api/agentic/generateScenario →
AI Scenario Generation → Framework Execution → 
Real Metrics Calculation → Decision Memo Creation
```

## City Support & Geographic Data

### Supported Cities

#### London Boroughs
- **Westminster**: Primary test borough with full feature support
- **City of London**: Financial district with high-density network
- **Kensington and Chelsea**: Royal borough with complex street layout
- **Camden, Southwark, Hackney, Islington**: Additional London boroughs
- **32 Total London Boroughs**: Full coverage of Greater London

#### International Cities
- **Manhattan, NYC**: Grid-based street network for comparison studies

### Geographic Data Integration

```python
# OSMnx Integration
class NetworkGraphService:
    CITY_CONFIGS = {
        "westminster": {
            "place_name": "City of Westminster, London, England",
            "network_type": "drive",
            "center": (51.4975, -0.1357),
            "dist": 3000
        }
    }
```

### Borough Boundary Visualization
- Real administrative boundaries from OpenStreetMap
- Interactive boundary overlays on Folium maps
- Styled with light blue fill and dark blue borders
- Toggleable layer controls for user preference

## Simulation Engines

### 1. Real Evacuation Science Engine
**Location**: `backend/services/multi_city_simulation.py`

```python
class RealEvacuationSimulation:
    def run_real_simulation(self, scenario_config: dict) -> dict:
        # 1. A* optimal route planning
        # 2. Realistic agent behavior modeling  
        # 3. Real metrics calculation
```

**Features**:
- A* pathfinding with real safe zones
- Biased random walks with human behavioral factors
- Pedestrian flow calculations
- Bottleneck analysis
- Panic modeling integration

### 2. Multi-City Evacuation Service
**Location**: `backend/services/multi_city_simulation.py`

```python
class MultiCityEvacuationService:
    def _run_uk_city_simulation(self, city: str, config: Dict) -> Dict[str, Any]:
        # Comprehensive simulation suite:
        # - OSMnx graph loading
        # - A* routing + biased random walks
        # - Interactive Folium map generation
        # - Real metrics calculation
```

### 3. Network Graph Service
**Location**: `backend/services/network/graph_service.py`

- Stateless graph loading and caching
- OSMnx integration for real street networks
- Fallback synthetic graphs for testing
- Performance optimization with graph caching

## API Endpoints

### Core Simulation Endpoints
```
GET  /api/simulation/cities                    # List supported cities
GET  /api/simulation/{city}/visualisation      # Get/run city visualization  
POST /api/simulation/{city}/run               # Start background simulation
GET  /api/simulation/{city}/status            # Get city capabilities
```

### Evacuation Planning Endpoints
```
POST /api/runs                                # Start evacuation planning run
GET  /api/runs                                # List all runs
GET  /api/runs/{run_id}                       # Get specific run results
```

### Agentic AI Endpoints
```
POST /api/agentic/generate-scenario           # Generate AI scenarios
POST /api/agentic/generate-metrics           # Generate AI metrics
POST /api/agentic/analysis-package           # Create analysis package
POST /api/agentic/execute-framework-scenario  # Execute framework scenarios
```

### Emergency Response Endpoints
```
POST /api/emergency/generate-plan             # Generate emergency plan
POST /api/emergency/chat                     # Emergency chat assistance
POST /api/notifications/government-alert     # Send WhatsApp alerts
```

## Frontend Components

### 1. PlanAndRunGovUK Component
**Location**: `frontend/src/components/PlanAndRunGovUK.tsx`

**Purpose**: Main planning interface for configuring and starting evacuation runs

**Key Features**:
- City selection with proper borough support
- User intent configuration (objectives, constraints, preferences)
- Agentic AI planner integration
- Two run modes:
  - **Evacuation Planning Run**: Full scenario generation with intent object
  - **Quick Simulation**: Direct visualization for testing

**Data Flow**:
```typescript
interface UserIntent {
  objective: string;
  city: string;  // Synchronized with selectedCity
  constraints: {
    max_scenarios: number;
    compute_budget_minutes: number;
    must_protect_pois: string[];
  };
  preferences: {
    fairness_weight: number;
    clearance_weight: number;
    robustness_weight: number;
  };
}
```

### 2. CitySpecificVisualisation Component
**Location**: `frontend/src/components/CitySpecificVisualisation.tsx`

**Purpose**: Interactive map visualization with network analysis

**Key Features**:
- **Street View**: Interactive Folium map with real geography
- **Grid View**: Network graph visualization with zoom/pan controls
- **Borough Boundaries**: Administrative boundary overlays
- **Route Overlays**: A* routes, random walks, exit points
- **Layer Controls**: Toggle different visualization elements

**Visualization Modes**:
```typescript
const [viewMode, setViewMode] = useState<'network' | 'grid'>('network');

// Street View: Real geographic map with Folium
if (visualisationData?.interactive_map_html) {
  // Display Folium map with borough boundaries
}

// Grid View: Network graph with SVG rendering
if (viewMode === 'grid' && visualisationData?.network_graph) {
  // Render network nodes and edges
}
```

### 3. ResultsGovUK Component
**Location**: `frontend/src/components/ResultsGovUK.tsx`

**Purpose**: Display completed evacuation planning results

**Key Features**:
- Run selection and filtering
- City extraction from multiple data sources
- Decision memo display
- Emergency alert integration
- Scenario analysis and metrics

**City Resolution Logic**:
```typescript
const getTargetCityFromResults = (runResult: RunResult): string => {
  // Priority 1: Direct city field from API
  if (runResult.city) return runResult.city;
  
  // Priority 2: User intent city
  if (runResult.user_intent?.city) return runResult.user_intent.city;
  
  // Priority 3: Extract from scenario descriptions
  // Priority 4: Fallback to URL parameter or default
};
```

### 4. AgenticPlannerPanel Component
**Location**: `frontend/src/components/AgenticPlannerPanel.tsx`

**Purpose**: AI-powered scenario and metrics generation

**Key Features**:
- Natural language scenario description
- Framework template selection
- Automatic metrics generation
- Real-time execution with live results
- Analysis package creation

## Agentic AI System

### Architecture
```
User Input → Scenario Generation → Metrics Generation → 
Framework Execution → Real Simulation → Decision Analysis
```

### Key Components

#### 1. Scenario Builder
```python
class AgenticScenarioBuilder:
    def generate_scenario(self, intent: str, city_context: str) -> ScenarioSpec:
        # AI-powered scenario generation
        # Framework compliance checking
        # Executable configuration creation
```

#### 2. Metrics Builder  
```python
class AgenticMetricsBuilder:
    def generate_metrics(self, analysis_goal: str) -> MetricsSpec:
        # Custom metrics generation
        # Performance indicator selection
        # Evaluation criteria definition
```

#### 3. Framework Integration
- **Framework Compliance**: Ensures scenarios meet emergency planning standards
- **Executable Scenarios**: Converts AI descriptions to simulation parameters
- **Real Metrics**: Integrates with actual simulation engines for authentic results

## Storage & Caching

### Local S3 Structure
```
local_s3/
├── runs/                    # Simulation run results
│   └── {run_id}/
│       ├── city_results/    # City-specific simulation data
│       └── emergency_plans/ # Generated emergency plans
├── scenarios/               # Scenario definitions
├── images/                  # Generated visualizations
├── logs/                   # System logs and RSS data
└── cache/                  # Graph and computation cache
```

### Caching Strategy
- **Graph Caching**: Pre-loaded OSMnx graphs for fast simulation startup
- **Result Caching**: Simulation results cached for quick retrieval
- **Artifact Storage**: All run artifacts stored with provenance tracking

### Data Persistence
```python
class StorageService:
    async def store_run_artifact(self, run_id: str, artifact_type: str, 
                                data: Dict, producer_agent: str):
        # Structured artifact storage with metadata
        # Provenance tracking for audit trails
        # Efficient retrieval and indexing
```

## Visualization System

### Folium Map Integration

#### Borough Boundary Rendering
```python
def _add_borough_boundary_to_map(self, folium_map, city: str):
    # Get boundary geometry from OSMnx
    boundary_gdf = ox.geocode_to_gdf(place_query)
    
    # Add styled boundary to map
    folium.GeoJson(
        boundary_gdf.to_json(),
        style_function=lambda x: {
            'fillColor': 'lightblue',
            'color': 'darkblue',
            'weight': 3,
            'fillOpacity': 0.1,
            'opacity': 0.8
        }
    ).add_to(boundary_group)
```

#### Route Visualization
- **A* Routes**: Blue polylines showing optimal evacuation paths
- **Random Walks**: Red paths showing realistic human behavior
- **Exit Points**: Green markers at evacuation destinations
- **Density Heatmaps**: Orange circles showing agent concentration

### Network Graph Rendering
- **SVG-based**: Scalable vector graphics for crisp visualization
- **Interactive Controls**: Zoom, pan, and reset functionality
- **Performance Optimized**: Systematic sampling for large networks
- **Layer Management**: Separate groups for different data types

## Emergency Response Integration

### WhatsApp Alert System
```typescript
const sendWhatsAppAlert = async () => {
  const message = `🚨 EMERGENCY EVACUATION ALERT
Run ID: ${runResult.run_id}
Location: ${formattedCity}
Status: ${runResult.status}
Immediate action required.`;
  
  await fetch('/api/notifications/government-alert', {
    method: 'POST',
    body: JSON.stringify({ message, priority: 'critical' })
  });
};
```

### Emergency Chat Assistant
- **Role-based Responses**: Different perspectives for different emergency roles
- **Context-aware**: Uses current run data and city information
- **Real-time Communication**: Live chat interface with AI assistance
- **Emergency Plan Generation**: Automatic plan creation based on simulation results

## Deployment & Configuration

### Environment Setup
```bash
# Backend Dependencies
cd backend
pip install -r requirements.txt

# Frontend Dependencies  
cd frontend
npm install

# Start Development Servers
make dev-backend    # FastAPI server on :8000
make dev-frontend   # React dev server on :3000
```

### Configuration Files
- `backend/core/config.py`: Core system configuration
- `frontend/src/config/api.js`: API endpoint configuration
- `backend/configs/sources.yml`: RSS feed sources
- Environment files for production deployment

### Key Environment Variables
```bash
# API Configuration
API_BASE_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000

# Storage Configuration
LOCAL_STORAGE_PATH=./local_s3
CACHE_ENABLED=true

# External Services
TWILIO_ACCOUNT_SID=your_twilio_sid
OPENAI_API_KEY=your_openai_key
```

## System Integration Points

### 1. City Selection Flow
```
Frontend City Selection → UserIntent Update → 
Backend Simulation → OSMnx Graph Loading → 
Result Storage → Frontend Display
```

### 2. Visualization Pipeline
```
Simulation Data → Folium Map Generation → 
Borough Boundary Addition → Route Overlays → 
Interactive HTML → Frontend Embedding
```

### 3. Agentic Planning Integration
```
Natural Language Input → AI Processing → 
Scenario Generation → Framework Validation → 
Real Simulation Execution → Decision Analysis
```

## Performance Considerations

### Graph Loading Optimization
- Pre-cached graphs for major cities
- Lazy loading for less common areas
- Fallback synthetic graphs for development

### Visualization Performance
- Systematic sampling for large networks (2000 edges, 1000 nodes max)
- Optimized SVG rendering with reduced opacity
- Progressive loading for complex maps

### API Response Times
- Cached simulation results for instant retrieval
- Background processing for long-running simulations
- Server-sent events for real-time updates

## Troubleshooting & Maintenance

### Common Issues

#### City Parameter Mismatch
**Problem**: Selected city not matching simulation results
**Solution**: Ensure UserIntent.city is synchronized with selectedCity

#### Missing Interactive Maps
**Problem**: Street view showing network graph instead of geographic map
**Solution**: Verify Folium map generation in _run_uk_city_simulation

#### Borough Boundary Not Displaying
**Problem**: Boundary overlay not appearing on map
**Solution**: Check OSMnx geocoding and GeoJSON conversion

### Monitoring & Logging
- Structured logging with run_id correlation
- Performance metrics for simulation execution
- Error tracking with full stack traces
- RSS feed health monitoring

## Future Enhancements

### Planned Features
1. **Real-time Traffic Integration**: Live traffic data for route optimization
2. **Weather Impact Modeling**: Weather effects on evacuation efficiency  
3. **Multi-hazard Scenarios**: Support for different emergency types
4. **Mobile Application**: Native mobile app for field use
5. **International Expansion**: Support for cities outside UK/US

### Technical Improvements
1. **Microservices Architecture**: Split monolithic backend
2. **Container Deployment**: Docker/Kubernetes deployment
3. **Database Integration**: Replace file storage with proper database
4. **Real-time Collaboration**: Multi-user planning sessions
5. **Advanced Analytics**: Machine learning for pattern recognition

---

This documentation provides a comprehensive overview of how all system components work together to create a powerful, AI-enhanced evacuation planning platform that combines real-world geographic data with advanced simulation techniques and emergency response capabilities.
