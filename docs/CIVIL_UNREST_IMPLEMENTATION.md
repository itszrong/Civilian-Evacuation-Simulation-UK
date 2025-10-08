# Civil Unrest Detection & Simulation Queue Implementation

## Overview

This implementation adds comprehensive civil unrest detection capabilities to the RSS feed processing system, automatically identifying articles that suggest civil unrest or instability and creating a simulation queue with approval workflow for London evacuation planning.

## 🔍 Features Implemented

### 1. Civil Unrest Detection Engine

**Location**: `services/rss_ingestion/main.py`

- **Keyword-based Analysis**: Three-tier risk classification system
  - **High-risk keywords** (3.0 points each): riot, civil unrest, looting, emergency declared, etc.
  - **Medium-risk keywords** (1.5 points each): protest, demonstration, strike, confrontation, etc.
  - **Low-risk keywords** (0.5 points each): gathering, peaceful protest, vigil, etc.

- **London Region Detection**: Automatic identification of 35+ London boroughs and areas
- **Risk Scoring**: 0-10 scale with automatic simulation threshold at 4.0+
- **Geographic Targeting**: Boosts scores for London-specific content

### 2. Enhanced RSS Article Schema

**New Fields Added**:
```python
civil_unrest_score: Optional[float] = None          # 0-10 risk score
civil_unrest_indicators: List[str] = []             # Detected keywords
requires_simulation: bool = False                   # Auto-trigger flag
suggested_regions: List[str] = []                   # London areas affected
```

### 3. Simulation Queue System

**Backend API**: `backend/api/simulation_queue.py`

- **Request Management**: Create, approve, reject, track simulation requests
- **Status Workflow**: pending → approved/rejected → running → completed
- **Approval System**: Manual review with custom parameters and regions
- **Integration**: Automatic scenario and metrics configuration

**Key Endpoints**:
- `GET /api/simulation-queue/requests` - List all requests
- `GET /api/simulation-queue/requests/pending` - Pending requests only
- `POST /api/simulation-queue/requests/{id}/approve` - Approve/reject requests
- `GET /api/simulation-queue/stats` - Queue statistics

### 4. Civil Unrest Analysis API

**Backend API**: `backend/api/civil_unrest.py`

- **Analysis Dashboard**: Real-time unrest detection statistics
- **Candidate Management**: Articles requiring simulation review
- **Auto-queuing**: Bulk queue high-risk articles (score ≥ 6.0)
- **Integration**: Direct connection to RSS feed data

**Key Endpoints**:
- `GET /api/civil-unrest/analysis` - Full analysis with filtering
- `GET /api/civil-unrest/candidates` - Simulation candidates
- `POST /api/civil-unrest/queue-simulation/{article_id}` - Queue specific article
- `POST /api/civil-unrest/auto-queue` - Bulk queue high-risk articles

### 5. Frontend Simulation Queue Interface

**Component**: `frontend/src/components/SimulationQueue.tsx`

- **Tabbed Interface**: Queue, Candidates, Analysis views
- **Approval Workflow**: Review requests with custom parameters
- **Real-time Updates**: Auto-refresh every 30 seconds
- **GOV.UK Design**: Consistent government design system

**Features**:
- Visual risk indicators (Critical/High/Medium/Low tags)
- Regional customization for simulations
- Bulk approval/rejection capabilities
- Integration with Sources page via tabs

### 6. Scenario Builder Integration

**Integration Points**:
- Automatic scenario creation on approval
- Civil unrest hazard type with appropriate parameters
- Population estimation based on affected regions
- Severity mapping from risk scores:
  - Score ≥ 8.0 → Critical severity
  - Score ≥ 6.0 → High severity  
  - Score ≥ 4.0 → Medium severity
  - Score < 4.0 → Low severity

**Default Parameters for Civil Unrest**:
```python
{
    "compliance_rate": 0.6,        # Lower compliance during unrest
    "car_availability": 0.3,       # Reduced due to traffic/safety
    "walking_speed_reduction": 0.4, # Slower due to crowds/obstacles
    "transport_disruption": 0.8    # High disruption expected
}
```

### 7. Metrics Builder Integration

**Automatic Metrics Configuration**:
- **clearance_p50**: Time to 50% evacuation completion
- **clearance_p95**: Time to 95% evacuation completion  
- **max_queue_length**: Peak congestion levels
- Extensible for additional civil unrest specific metrics

## 🚀 Usage Workflow

### 1. Automatic Detection
1. RSS feeds are ingested every 15 minutes
2. Each article is analyzed for civil unrest indicators
3. Articles with score ≥ 4.0 and London relevance are flagged for simulation
4. High-risk articles (score ≥ 6.0) can be auto-queued

### 2. Manual Review Process
1. Emergency planners access **Sources → Simulation Queue** tab
2. Review pending simulation requests with risk scores and indicators
3. Customize affected regions and simulation parameters if needed
4. Approve or reject requests with reasoning

### 3. Simulation Execution
1. Approved requests automatically generate evacuation scenarios
2. Scenarios use civil unrest-specific parameters
3. Metrics are configured for comprehensive analysis
4. Results feed back into the planning system

## 📊 Testing Results

The system has been tested with realistic scenarios:

- **High-risk detection**: "Violent protests erupt in Central London" → Score 10.0/10 ✓
- **Critical incidents**: "Emergency declared in Tower Hamlets due to civil unrest" → Score 10.0/10 ✓
- **Low-risk filtering**: "Peaceful vigil held in Camden" → Score 1.5/10 (no simulation) ✓
- **Irrelevant content**: "Traffic delays on M25" → Score 0.0/10 (ignored) ✓

## 🔧 Configuration

### RSS Feed Sources
The system monitors these feeds for civil unrest:
- BBC News - London (Priority 10)
- BBC News - UK (Priority 9)
- Sky News - UK (Priority 8)
- The Guardian - UK (Priority 8)
- Reuters - Breaking News (Priority 9)
- AP News - Top Stories (Priority 8)

### Simulation Thresholds
- **Auto-detection threshold**: 4.0+ score with London relevance
- **Auto-queue threshold**: 6.0+ score (configurable)
- **Manual review**: All pending requests require approval

## 🎯 Benefits

1. **Proactive Planning**: Detect potential evacuation scenarios before they escalate
2. **Automated Triage**: Focus human attention on highest-risk situations
3. **Rapid Response**: Pre-configured scenarios ready for immediate deployment
4. **Evidence-based**: Decisions backed by real-time news analysis
5. **Scalable**: System handles multiple concurrent incidents across London

## 🔄 Future Enhancements

1. **Machine Learning**: Train models on historical civil unrest patterns
2. **Social Media Integration**: Monitor Twitter/X for real-time incident reports
3. **Geographic Clustering**: Detect spreading unrest across adjacent areas
4. **Predictive Analytics**: Forecast escalation probability
5. **Multi-city Support**: Extend beyond London to other UK cities

## 📁 File Structure

```
backend/
├── api/
│   ├── simulation_queue.py      # Simulation queue management API
│   └── civil_unrest.py          # Civil unrest analysis API
├── scenarios/
│   └── builder.py               # Integrated scenario generation
└── metrics/
    └── builder.py               # Integrated metrics configuration

frontend/src/components/
├── SimulationQueue.tsx          # Main queue interface
└── SourcesGovUK.tsx            # Updated with queue tab

services/rss_ingestion/
└── main.py                     # Enhanced with unrest detection
```

## 🚨 Emergency Planning Integration

This system integrates seamlessly with existing emergency planning workflows:

1. **Detection** → RSS feeds identify potential incidents
2. **Analysis** → AI-powered risk assessment and region identification  
3. **Review** → Human oversight ensures appropriate response
4. **Simulation** → Automated scenario generation for evacuation planning
5. **Response** → Results inform real-world emergency procedures

The implementation provides a complete end-to-end solution for proactive civil unrest detection and evacuation planning in London.
