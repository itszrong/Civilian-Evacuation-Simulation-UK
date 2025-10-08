# Civilian Evacuation Simulation System Architecture

## Simplified System Overview

```mermaid
graph TB
    User[User Request] --> DSPy[DSPy Framework - AI Orchestration]
    
    DSPy --> ScenarioBuilder[Scenario Builder]
    DSPy --> MetricBuilder[Metric Builder]
    
    ScenarioBuilder --> Agents[Agent System]
    MetricBuilder --> Agents
    
    Agents --> SimulationEngine[Simulation Engine]
    SimulationEngine --> Results[Results & Analysis]
    
    %% External Services
    subgraph ExternalMicroservices["External Microservices"]
        DSPyAgents[DSPy Agents Service]
        RSSIngestion[RSS Ingestion Service]
    end
    
    subgraph ExternalAPIs["External APIs"]
        LLMAPIs[OpenAI/Anthropic APIs]
        OSMnx[OSMnx/OpenStreetMap]
    end
    
    %% Key relationships
    DSPy -.->|"Natural Language to Specs"| ScenarioBuilder
    DSPy -.->|"Analysis Goals to Metrics"| MetricBuilder
    Agents -.->|"Orchestrate & Execute"| SimulationEngine
    DSPy --> LLMAPIs
    SimulationEngine --> OSMnx
    Agents --> DSPyAgents
    DSPyAgents --> RSSIngestion
    
    %% Styling
    classDef primary fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    classDef secondary fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef process fill:#e8f5e8,stroke:#388e3c,stroke-width:2px
    classDef output fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef microservices fill:#fff8e1,stroke:#f57c00,stroke-width:1px
    classDef apis fill:#fafafa,stroke:#666,stroke-width:1px
    
    class User,DSPy primary
    class ScenarioBuilder,MetricBuilder secondary
    class Agents,SimulationEngine process
    class Results output
    class DSPyAgents,RSSIngestion microservices
    class LLMAPIs,OSMnx apis
```

## How It Works

### **The Flow**
1. **User** makes a request in natural language: *"Create a flood scenario and analyze evacuation efficiency"*
2. **DSPy Framework** converts this into structured specifications using LLMs
3. **Scenario Builder** creates evacuation scenarios from the DSPy specs
4. **Metric Builder** generates analysis metrics from the DSPy specs  
5. **Agent System** orchestrates the simulation workflow (plan → execute → judge → explain)
6. **Simulation Engine** runs the actual evacuation simulations (Mesa agent-based modeling)
7. **Results** are analyzed and presented back to the user

### **Key Innovation**
- **DSPy** enables natural language → structured specifications
- **Agents** provide intelligent workflow orchestration
- **Dual engines** support both AI-generated and template-based scenarios
- **End-to-end** automation from user intent to simulation results

This simplified architecture shows how AI (DSPy) powers intelligent scenario and metrics generation, while agents orchestrate the execution through a robust simulation engine.
