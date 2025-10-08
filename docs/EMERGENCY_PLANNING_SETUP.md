# Emergency Planning AI Assistant - Setup Guide

## Overview

The Emergency Planning AI Assistant uses **DSPy** and **OpenAI GPT-4** to provide intelligent emergency response guidance for government officials during evacuations.

## Features

- 🔥 **Automatic Hotspot Detection** - Analyzes evacuation density to find critical areas
- 🏥 **POI Discovery** - Identifies nearby hospitals, buildings, shops, and transport
- 🤖 **LLM-Powered Analysis** - Uses DSPy Chain-of-Thought for priority ranking
- 💬 **Role-Specific Chat** - Tailored guidance for PM, DPM, Comms, Chief of Staff, CE, Permanent Secretary
- 📊 **Emergency Plans** - Generates comprehensive response plans automatically

## Prerequisites

1. **Python 3.10+** (for backend)
2. **Node.js 18+** (for frontend)
3. **OpenAI API Key** (required for LLM features)

## Installation

### 1. Install Backend Dependencies

```bash
# Install Python dependencies including DSPy
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
# Copy the template
cp .env.template .env

# Edit .env and add your OpenAI API key
# OPENAI_API_KEY=sk-proj-...
```

**Get your OpenAI API key:**
- Sign up at https://platform.openai.com/
- Navigate to API Keys: https://platform.openai.com/api-keys
- Create a new secret key
- Copy and paste into `.env`

### 3. Verify Configuration

The system will automatically detect your API key on startup. Check the logs:

```bash
# Start backend
cd backend
python main.py
```

Look for:
```
✅ Successfully initialized DSPy with OpenAI
✅ DSPy emergency planner module ready
```

## Usage

### Running a Simulation with Emergency Planning

1. **Navigate to Plan Page**: http://localhost:3000/plan
2. **Select City**: Choose London or Manhattan
3. **Run Simulation**: Click "Run Evacuation Simulation"
4. **Wait for Completion**: System will:
   - Run evacuation simulation
   - Analyze hotspots
   - Find nearby POIs
   - Generate emergency plan (using LLM)
   - Store everything for later use

### Using the Emergency Chat Assistant

1. **Go to Results Page**: http://localhost:3000/results?city=london
2. **Click "🚨 Emergency Response Assistant"** (top right)
3. **Select Your Role**: PM, DPM, Comms, etc.
4. **Ask Questions**:
   - "What are the critical priorities?"
   - "How should we allocate resources?"
   - "What messaging should we use for the public?"
   - "Which hospitals are near the hotspots?"

### Example Questions by Role

**Prime Minister:**
- "What should be my key public statement?"
- "What are the critical decisions I need to make?"
- "How do we prioritize the critical hotspots?"

**Communications Director:**
- "What messaging should we use for the public?"
- "How do we communicate evacuation instructions?"
- "What are the key talking points for media?"

**Chief of Staff:**
- "How do we deploy resources across hotspots?"
- "What's the timeline for emergency response?"
- "Which teams need activation?"

## API Endpoints

### Emergency Planning

```bash
# Generate emergency plan for a city
POST /api/emergency/generate-plan
{
  "city": "london",
  "run_id": "optional-run-id"
}

# Get existing emergency plan
GET /api/emergency/plan/{city}?run_id=optional

# Chat with emergency assistant
POST /api/emergency/chat
{
  "city": "london",
  "user_role": "PM",
  "message": "What are our priorities?",
  "conversation_history": []
}

# Get available roles
GET /api/emergency/roles
```

## Architecture

### Data Flow

```
1. Evacuation Simulation
   ↓
2. Hotspot Analysis (EmergencyHotspotAnalyzer)
   ↓
3. POI Discovery (POIService)
   ↓
4. LLM Analysis (DSPy EmergencyPlannerModule)
   ↓
5. Emergency Plan Generation
   ↓
6. Storage (local_s3/runs/{run_id}/emergency_plan.json)
   ↓
7. Chat Interface (EmergencyChatPanel)
```

### Components

**Backend:**
- `services/emergency_planner.py` - Core DSPy planning logic
- `api/emergency_chat.py` - REST API endpoints
- `services/storage_service.py` - Plan persistence

**Frontend:**
- `components/EmergencyChatPanel.tsx` - Chat UI (slide-over)
- `components/ResultsGovUK.tsx` - Results page with chat integration

## DSPy Signatures

### 1. AnalyzeEmergencySituation
```python
Input:
- hotspot_data: Location, severity, density
- nearby_pois: Hospitals, buildings, shops
- city_context: City name and context

Output:
- priority_ranking: 1-10 score
- severity_assessment: Detailed analysis
- recommended_actions: List of actions
- resource_allocation: Personnel, vehicles, supplies
- risk_factors: Key vulnerabilities
```

### 2. GenerateRoleSpecificGuidance
```python
Input:
- role: Government role (PM, DPM, etc.)
- emergency_plan: Overall plan context
- city_context: City and situation

Output:
- guidance: Specific action items
- key_decisions: Decisions needed
- coordination_points: Who to coordinate with
- communication_strategy: Messaging approach
```

### 3. EmergencyResponseChat
```python
Input:
- conversation_history: Previous messages
- user_role: User's role
- user_question: Current question
- emergency_plan: Plan context

Output:
- response: Clear, actionable response
```

## Troubleshooting

### "No LLM API key found"
- Check `.env` file has `OPENAI_API_KEY=sk-proj-...`
- Restart backend server after adding key
- Verify key is valid at https://platform.openai.com/

### "Using mock planner"
- System falls back to mock responses without API key
- Mock responses provide basic guidance but no LLM reasoning
- Add valid API key for full functionality

### Chat not loading
- Check backend is running: `http://localhost:8000/docs`
- Check API endpoint: `http://localhost:8000/api/emergency/roles`
- Check browser console for errors

### Emergency plan not generating
- Ensure simulation completed successfully
- Check backend logs for errors
- Verify `local_s3/` directory has write permissions

## Development

### Adding New Roles

Edit `backend/api/emergency_chat.py`:

```python
{
    "id": "NEW_ROLE",
    "title": "New Role Title",
    "description": "Role description"
}
```

### Customizing LLM Model

Edit `backend/services/emergency_planner.py`:

```python
lm = dspy.OpenAI(
    model='gpt-4o',  # Change to gpt-4o for better quality
    max_tokens=2000,
    api_key=settings.OPENAI_API_KEY
)
```

### Adding Custom POI Types

Edit `POIService.find_pois_near_hotspot()` to query OSMnx:

```python
import osmnx as ox

pois = ox.geometries_from_point(
    (lat, lon),
    tags={'amenity': ['hospital', 'police', 'fire_station']},
    dist=radius_meters
)
```

## Cost Estimation

**OpenAI GPT-4o-mini pricing (as of 2024):**
- Input: $0.15 per 1M tokens
- Output: $0.60 per 1M tokens

**Per simulation:**
- Emergency plan generation: ~2,000 tokens ≈ $0.001
- Chat message: ~500 tokens ≈ $0.0003

**Monthly estimate (100 simulations, 1000 chat messages):**
- Emergency plans: $0.10
- Chat: $0.30
- **Total: ~$0.40/month**

Very affordable for government use! 🎉

## Support

For issues or questions:
1. Check logs: Backend console and browser DevTools
2. Review API docs: http://localhost:8000/docs
3. Test endpoints directly in Swagger UI

## License

Part of the Civilian Evacuation Simulation system.
