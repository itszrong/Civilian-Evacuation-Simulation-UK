# User Guide - Civilian Evacuation Simulation System

## Table of Contents
1. [Getting Started](#getting-started)
2. [System Overview](#system-overview)
3. [Planning & Running Simulations](#planning--running-simulations)
4. [Visualization & Analysis](#visualization--analysis)
5. [AI-Powered Planning](#ai-powered-planning)
6. [Emergency Response Features](#emergency-response-features)
7. [Results Analysis](#results-analysis)
8. [Advanced Features](#advanced-features)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)

## Getting Started

### Accessing the System
1. **Web Interface**: Navigate to `http://localhost:3000` (development) or your deployed URL
2. **Login**: No authentication required for development (configurable for production)
3. **Dashboard**: Main overview of system status and recent activity

### First Steps
1. **Select a City**: Choose from supported cities (Westminster, Kensington and Chelsea, Manhattan, etc.)
2. **Run Quick Simulation**: Click "Quick Simulation Only" to see basic visualization
3. **Explore Results**: View interactive maps and network analysis
4. **Try AI Planning**: Use "Open AI Planner" for advanced scenario generation

## System Overview

### Main Components

#### 1. Dashboard
- **System Status**: Overview of simulation capabilities
- **Recent Activity**: Latest simulation runs and results
- **Quick Actions**: Direct access to planning and results

#### 2. Plan & Run Interface
- **City Selection**: Choose target area for evacuation planning
- **Intent Configuration**: Set objectives, constraints, and preferences
- **AI Integration**: Generate scenarios and metrics automatically
- **Simulation Execution**: Run comprehensive evacuation analysis

#### 3. Visualization System
- **Interactive Maps**: Real geographic maps with street networks
- **Network Analysis**: Graph-based visualization of evacuation routes
- **Borough Boundaries**: Administrative area overlays
- **Route Analysis**: A* optimal paths and realistic human behavior

#### 4. Results Analysis
- **Decision Memos**: AI-generated analysis and recommendations
- **Scenario Comparison**: Multi-scenario performance analysis
- **Emergency Planning**: Actionable evacuation procedures
- **Alert System**: WhatsApp integration for emergency notifications

## Planning & Running Simulations

### Basic Simulation Workflow

#### Step 1: City Selection
```
1. Navigate to "Plan & Run" page
2. Select target city from dropdown:
   - Westminster (London)
   - Kensington and Chelsea (London)
   - City of London
   - Manhattan (NYC)
   - Other supported boroughs
3. City selection automatically updates all simulation parameters
```

#### Step 2: Configure Intent
```
Objective Options:
- Minimise clearance time and improve fairness
- Maximise evacuation efficiency
- Protect vulnerable populations
- Optimise resource allocation

Constraints:
- Max scenarios: 1-20 (recommended: 8)
- Compute budget: 1-10 minutes (recommended: 3)
- Protected POIs: Hospitals, schools, transport hubs

Preferences (must sum to 1.0):
- Fairness weight: 0.0-1.0 (recommended: 0.35)
- Clearance weight: 0.0-1.0 (recommended: 0.50)
- Robustness weight: 0.0-1.0 (recommended: 0.15)
```

#### Step 3: Choose Simulation Type

**Evacuation Planning Run** (Recommended):
- Full scenario generation with AI assistance
- Multiple evacuation scenarios tested
- Comprehensive metrics and decision analysis
- Real-time progress updates via Server-Sent Events
- Complete emergency planning documentation

**Quick Simulation Only**:
- Direct visualization for testing
- Single scenario execution
- Immediate results display
- Useful for system verification and demos

### Advanced Configuration

#### Protected Points of Interest
```
Examples:
- StThomasHospital, KingsCollegeHospital
- Westminster_School, Imperial_College
- Victoria_Station, Westminster_Bridge
- Custom locations: "51.4975,-0.1357"
```

#### Hypotheses Testing
```
Example Scenarios:
- "Westminster cordon 2h" - 2-hour area lockdown
- "Two Thames bridges closed" - Infrastructure disruption
- "Rush hour evacuation" - Peak population scenario
- "Weekend emergency" - Reduced transport availability
```

## Visualization & Analysis

### Interactive Map Features

#### Street View (Primary)
- **Real Geography**: Authentic street layouts from OpenStreetMap
- **Borough Boundaries**: Administrative area overlays in light blue
- **Evacuation Routes**: 
  - Blue lines: A* optimal paths
  - Red paths: Realistic human behavior (random walks)
  - Green markers: Safe evacuation points
- **Density Analysis**: Orange circles showing population concentration
- **Layer Controls**: Toggle different visualization elements

#### Network Graph View
- **Node-Edge Visualization**: Street network as mathematical graph
- **Zoom Controls**: Interactive pan and zoom functionality
- **Performance Optimized**: Systematic sampling for large networks
- **Route Highlighting**: Evacuation paths overlaid on network structure

### Map Controls
```
Navigation:
- Zoom: Mouse wheel or +/- buttons
- Pan: Click and drag
- Reset: Return to default view
- Layers: Toggle route types and boundaries

Information:
- Click markers for evacuation point details
- Hover routes for capacity and timing information
- Borough boundary shows administrative details
```

### Data Interpretation

#### Route Analysis
- **Blue Routes (A* Optimal)**: Mathematically shortest/fastest paths
- **Red Paths (Random Walks)**: Realistic human evacuation behavior
- **Route Capacity**: People per minute throughput
- **Walking Time**: Estimated evacuation duration
- **Safety Score**: Route safety assessment (0.0-1.0)

#### Network Metrics
- **Clearance Time P50**: Median evacuation time
- **Clearance Time P95**: 95th percentile evacuation time
- **Fairness Index**: Equity of evacuation access (0.0-1.0)
- **Bottleneck Analysis**: Congestion point identification
- **Evacuation Efficiency**: Overall system performance

## AI-Powered Planning

### Accessing AI Features
1. Click "Open AI Planner" in the Plan & Run interface
2. Choose from three AI-powered options:
   - **Scenario Generation**: Create custom evacuation scenarios
   - **Metrics Generation**: Define performance measurements
   - **Analysis Package**: Complete end-to-end planning

### Scenario Generation

#### Natural Language Input
```
Example Prompts:
- "Create a fire evacuation scenario for Westminster during rush hour"
- "Model a terrorist incident requiring immediate area clearance"
- "Simulate flooding evacuation with limited bridge access"
- "Plan evacuation for elderly care facility during power outage"
```

#### AI Processing
The system will:
1. Analyze your natural language description
2. Generate structured scenario parameters
3. Validate against emergency planning frameworks
4. Create executable simulation configuration
5. Provide reasoning for scenario design choices

#### Generated Scenario Structure
```
Scenario Output:
- Name: "Westminster Rush Hour Fire Evacuation"
- Hazard Type: Fire, flood, security, infrastructure
- Population Affected: Estimated number of people
- Duration: Expected incident timeline
- Severity: Low, medium, high, critical
- Protected Areas: Hospitals, schools, vulnerable populations
- Evacuation Zones: Geographic areas requiring clearance
```

### Metrics Generation

#### Analysis Goals
```
Example Goals:
- "Evaluate evacuation efficiency for elderly populations"
- "Measure emergency vehicle access during evacuation"
- "Assess fairness of evacuation resource distribution"
- "Analyze bottleneck formation and resolution"
```

#### Custom Metrics Creation
The AI will generate:
- **Performance Indicators**: Quantitative measurements
- **Success Criteria**: Target values and thresholds
- **Evaluation Methods**: How metrics will be calculated
- **Reporting Format**: How results will be presented

### Analysis Package Creation

#### Comprehensive Planning
1. **Describe Overall Goal**: High-level planning objective
2. **Scenario Intent**: Specific situation to model
3. **Framework Selection**: Choose emergency planning template
4. **Automatic Execution**: AI runs complete analysis pipeline
5. **Real Results**: Integration with actual simulation engines

#### Framework Templates
- **Fire Emergency**: Building and area fire evacuations
- **Flood Response**: Water-related emergency evacuations
- **Security Incident**: Threat-based area clearance
- **Infrastructure Failure**: Transport/utility disruption response
- **Comprehensive Evacuation**: Multi-hazard planning

## Emergency Response Features

### WhatsApp Alert System

#### Sending Alerts
1. Navigate to Results page
2. Select completed evacuation run
3. Click "📱 Send WhatsApp Alert" button
4. System generates formatted emergency message
5. Alert sent to configured government contact

#### Alert Content
```
Example Alert:
🚨 EMERGENCY EVACUATION ALERT

Run ID: 42227a1d-3753-4fca-8d03-25929d0aac66
Location: 🇬🇧 Westminster
Status: Completed
Scenarios: 3
Best Scenario: scenario_1

View results: [URL]

Immediate action required.
```

### Emergency Chat Assistant

#### Accessing Chat
1. Click "🚨 Emergency Response Assistant" in Results
2. Select your emergency role:
   - Emergency Coordinator
   - First Responder
   - Government Official
   - Public Safety Officer

#### Chat Features
- **Context-Aware**: Uses current simulation data
- **Role-Based**: Responses tailored to your emergency role
- **Real-Time**: Immediate assistance and guidance
- **Scenario Generation**: Create new scenarios from chat
- **Emergency Plans**: Generate actionable response procedures

#### Example Interactions
```
User: "What are the priority evacuation routes for Westminster?"
Assistant: "Based on the Westminster simulation, priority routes are:
1. Route A: Victoria Street to Westminster Bridge (capacity: 150 people/min)
2. Route B: Whitehall to Embankment (capacity: 120 people/min)
Bottlenecks identified at Parliament Square intersection."

User: "Generate emergency plan for this scenario"
Assistant: [Creates comprehensive emergency response plan]
```

## Results Analysis

### Run Selection
1. **Available Runs**: List of completed evacuation planning runs
2. **Run Details**: ID, status, creation time, city, scenario count
3. **Quick Filters**: Filter by city, date, status
4. **Run Comparison**: Compare multiple runs side-by-side

### Decision Memo Analysis

#### Automated Analysis
Each completed run includes:
- **Best Scenario Identification**: AI-selected optimal evacuation plan
- **Performance Justification**: Reasoning for scenario selection
- **Supporting Evidence**: Citations and data sources
- **Confidence Score**: AI confidence in recommendation (0.0-1.0)
- **Alternative Options**: Other viable scenarios considered

#### Scenario Comparison
```
Scenario Metrics:
- Clearance Time: Minutes to complete evacuation
- Max Queue: Peak congestion point capacity
- Fairness Index: Equity of evacuation access
- Robustness: Performance under varying conditions
- Overall Score: Weighted composite performance
```

### Visualization Integration
- **City-Specific Maps**: Interactive visualization for each scenario
- **Route Comparison**: Side-by-side route analysis
- **Performance Heatmaps**: Geographic performance visualization
- **Bottleneck Analysis**: Congestion point identification

## Advanced Features

### Multi-City Analysis
- **Borough Comparison**: Compare evacuation efficiency across London boroughs
- **International Analysis**: Westminster vs Manhattan evacuation patterns
- **Scalability Testing**: Performance across different city sizes
- **Best Practice Identification**: Learn from high-performing areas

### Real-Time Data Integration
- **RSS Feed Monitoring**: Live emergency situation awareness
- **Traffic Data**: Real-time congestion impact on evacuation routes
- **Weather Integration**: Environmental impact on evacuation efficiency
- **Social Media**: Public sentiment and compliance monitoring

### Framework Compliance
- **Government Standards**: Alignment with official emergency planning guidelines
- **International Best Practices**: WHO, UN, and other international standards
- **Audit Trail**: Complete documentation for compliance verification
- **Regulatory Reporting**: Automated report generation for authorities

## Best Practices

### Simulation Planning

#### City Selection
- **Start with Westminster**: Most comprehensive data and testing
- **Consider Population Density**: Higher density areas require more detailed analysis
- **Account for Geography**: River, bridges, and terrain impact evacuation
- **Time of Day Matters**: Rush hour vs off-peak population distribution

#### Scenario Configuration
- **Realistic Constraints**: Use achievable resource and time limits
- **Balanced Preferences**: Avoid extreme weight distributions
- **Multiple Scenarios**: Test 5-8 scenarios for comprehensive analysis
- **Iterative Refinement**: Use results to improve subsequent runs

### AI Planning Usage

#### Effective Prompts
```
Good Prompts:
- "Create a fire evacuation scenario for Westminster during rush hour with limited bridge access"
- "Model evacuation for vulnerable populations during winter weather emergency"

Poor Prompts:
- "Make evacuation plan" (too vague)
- "Best scenario" (no context)
```

#### Framework Selection
- **Match Hazard Type**: Choose appropriate emergency framework
- **Consider Local Factors**: Account for specific geographic constraints
- **Validate Assumptions**: Review AI-generated parameters for accuracy
- **Test Multiple Approaches**: Compare different framework templates

### Results Interpretation

#### Metric Analysis
- **Context Matters**: Compare results within similar scenarios
- **Trend Analysis**: Look for patterns across multiple runs
- **Bottleneck Focus**: Address highest-impact congestion points first
- **Fairness Consideration**: Balance efficiency with equity

#### Decision Making
- **Multi-Criteria**: Consider all metrics, not just clearance time
- **Stakeholder Input**: Involve emergency planning professionals
- **Real-World Validation**: Test recommendations with local authorities
- **Continuous Improvement**: Update plans based on new data

## Troubleshooting

### Common Issues

#### Simulation Not Starting
```
Problem: Simulation fails to start
Possible Causes:
- City not supported
- Invalid parameters
- Network connectivity issues

Solutions:
1. Verify city is in supported list
2. Check parameter constraints (weights sum to 1.0)
3. Test with "Quick Simulation Only" first
4. Check browser console for errors
```

#### Visualization Not Loading
```
Problem: Maps or graphs not displaying
Possible Causes:
- Browser compatibility
- JavaScript errors
- Network timeouts

Solutions:
1. Refresh page and try again
2. Clear browser cache
3. Try different browser (Chrome recommended)
4. Check network connection
5. Verify backend API is running
```

#### AI Features Not Working
```
Problem: Scenario generation fails
Possible Causes:
- API key configuration
- Service availability
- Request timeout

Solutions:
1. Check system configuration
2. Try simpler prompts
3. Use framework templates
4. Contact system administrator
```

#### Performance Issues
```
Problem: Slow simulation execution
Possible Causes:
- Large network size
- High scenario count
- System resource constraints

Solutions:
1. Reduce number of scenarios
2. Use smaller geographic areas
3. Close other applications
4. Try during off-peak hours
```

### Getting Help

#### Documentation Resources
- **System Architecture**: Technical system overview
- **API Documentation**: Complete API reference
- **Deployment Guide**: Installation and configuration
- **This User Guide**: Comprehensive usage instructions

#### Support Channels
- **GitHub Issues**: Bug reports and feature requests
- **Documentation**: In-system help and tooltips
- **Community Forum**: User discussions and tips
- **Professional Support**: Contact system administrators

#### Reporting Issues
When reporting problems, include:
1. **Steps to Reproduce**: Exact sequence of actions
2. **Expected Behavior**: What should have happened
3. **Actual Behavior**: What actually occurred
4. **System Information**: Browser, OS, network conditions
5. **Screenshots**: Visual evidence of the issue
6. **Console Logs**: Browser developer console output

---

This user guide provides comprehensive instructions for effectively using the Civilian Evacuation Simulation System for emergency planning and analysis.
