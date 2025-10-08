"""
Emergency Response Chat API
Provides LLM-powered chat interface for government officials during emergencies
"""

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import structlog

from services.emergency_planner import EmergencyPlanningService
from services.storage_service import StorageService
from models.schemas import AgentType

logger = structlog.get_logger(__name__)
router = APIRouter()

# Initialize services
emergency_service = EmergencyPlanningService()
storage_service = StorageService()


class ChatMessage(BaseModel):
    """Chat message model."""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: Optional[str] = None


class ChatRequest(BaseModel):
    """Chat request from frontend."""
    city: str
    run_id: Optional[str] = None
    user_role: str  # PM, DPM, Comms, Chief of Staff, CE, Permanent Secretary
    message: str
    conversation_history: List[ChatMessage] = []


class ChatResponse(BaseModel):
    """Chat response to frontend."""
    message: str
    role: str = "assistant"
    suggestions: Optional[List[str]] = None


class EmergencyPlanRequest(BaseModel):
    """Request to generate emergency plan."""
    city: str
    run_id: Optional[str] = None
    force_regenerate: bool = False


@router.post("/generate-plan")
async def generate_emergency_plan(request: EmergencyPlanRequest):
    """
    Generate emergency response plan from simulation data.
    Analyzes hotspots, nearby POIs, and generates LLM-powered recommendations.
    """
    try:
        logger.info("Generating emergency plan", city=request.city, run_id=request.run_id)

        # Get simulation data
        if request.run_id:
            simulation_data = await storage_service.get_run_artifact(
                run_id=request.run_id,
                artifact_type="city_simulation"
            )
        else:
            # Get most recent simulation for city
            runs = await storage_service.list_all_runs()
            city_runs = [r for r in runs if r.get('city') == request.city]

            if not city_runs:
                raise HTTPException(status_code=404, detail=f"No simulation found for {request.city}")

            simulation_data = await storage_service.get_run_artifact(
                run_id=city_runs[0]['run_id'],
                artifact_type="city_simulation"
            )

        if not simulation_data:
            raise HTTPException(status_code=404, detail="Simulation data not found")

        # Check if emergency plan already exists
        run_id = request.run_id or city_runs[0]['run_id']
        existing_plan = await storage_service.get_run_artifact(
            run_id=run_id,
            artifact_type="emergency_plan"
        )

        if existing_plan and not request.force_regenerate:
            logger.info("Returning cached emergency plan", run_id=run_id)
            return existing_plan

        # Generate new emergency plan
        plan = await emergency_service.generate_emergency_plan(simulation_data, request.city)

        # Store the plan
        await storage_service.store_run_artifact(
            run_id=run_id,
            artifact_type="emergency_plan",
            data=plan,
            producer_agent=AgentType.EMERGENCY_PLANNER
        )

        logger.info("Emergency plan generated", run_id=run_id, hotspots=plan.get('total_hotspots'))

        return plan

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to generate emergency plan", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to generate plan: {str(e)}")


@router.post("/chat", response_model=ChatResponse)
async def emergency_chat(request: ChatRequest):
    """
    Chat endpoint for role-specific emergency response guidance.

    Provides context-aware responses based on:
    - User's government role
    - Current emergency plan
    - Conversation history
    """
    try:
        logger.info("Emergency chat request",
                   city=request.city,
                   role=request.user_role,
                   message_length=len(request.message))

        # Get emergency plan context
        if request.run_id:
            plan = await storage_service.get_run_artifact(
                run_id=request.run_id,
                artifact_type="emergency_plan"
            )
        else:
            # Get most recent plan for city
            runs = await storage_service.list_all_runs()
            city_runs = [r for r in runs if r.get('city') == request.city]

            if city_runs:
                plan = await storage_service.get_run_artifact(
                    run_id=city_runs[0]['run_id'],
                    artifact_type="emergency_plan"
                )
            else:
                plan = None

        if not plan:
            # Generate plan first
            logger.info("No emergency plan found, generating one first")
            plan_request = EmergencyPlanRequest(city=request.city, run_id=request.run_id)
            plan = await generate_emergency_plan(plan_request)

        # Convert conversation history to dict format
        history = [msg.dict() for msg in request.conversation_history]

        # Get LLM response
        response_text = await emergency_service.chat_response(
            role=request.user_role,
            question=request.message,
            plan_context=plan,
            conversation_history=history
        )

        # Generate suggestions based on role
        suggestions = _get_role_suggestions(request.user_role, plan)

        return ChatResponse(
            message=response_text,
            suggestions=suggestions
        )

    except Exception as e:
        logger.error("Chat request failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@router.get("/plan/{city}")
async def get_emergency_plan(city: str, run_id: Optional[str] = None):
    """
    Get existing emergency plan for a city.

    Args:
        city: City name
        run_id: Optional specific run ID

    Returns:
        Emergency plan or 404 if not found
    """
    try:
        if run_id:
            plan = await storage_service.get_run_artifact(
                run_id=run_id,
                artifact_type="emergency_plan"
            )
        else:
            # Get most recent plan
            runs = await storage_service.list_all_runs()
            city_runs = [r for r in runs if r.get('city') == city]

            if not city_runs:
                raise HTTPException(status_code=404, detail=f"No plan found for {city}")

            plan = await storage_service.get_run_artifact(
                run_id=city_runs[0]['run_id'],
                artifact_type="emergency_plan"
            )

        if not plan:
            raise HTTPException(status_code=404, detail="Emergency plan not found")

        return plan

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get emergency plan", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/roles")
async def get_available_roles():
    """Get list of available government roles for chat."""
    return {
        "roles": [
            {
                "id": "PM",
                "title": "Prime Minister",
                "description": "Strategic oversight and public communication"
            },
            {
                "id": "DPM",
                "title": "Deputy Prime Minister",
                "description": "Operational coordination and inter-agency liaison"
            },
            {
                "id": "Comms",
                "title": "Communications Director",
                "description": "Public messaging and media coordination"
            },
            {
                "id": "Chief of Staff",
                "title": "Chief of Staff",
                "description": "Executive coordination and resource management"
            },
            {
                "id": "CE",
                "title": "Chief Executive",
                "description": "Operational implementation and service delivery"
            },
            {
                "id": "Permanent Secretary",
                "title": "Permanent Secretary",
                "description": "Departmental expertise and protocol compliance"
            }
        ]
    }


def _get_role_suggestions(role: str, plan: Dict) -> List[str]:
    """Generate role-specific question suggestions."""
    critical_count = plan.get('critical_hotspots', 0)
    total_hotspots = plan.get('total_hotspots', 0)

    role_suggestions = {
        'PM': [
            "What should be my key public statement?",
            "What are the critical decisions I need to make?",
            f"How do we prioritize the {critical_count} critical hotspots?"
        ],
        'DPM': [
            "Which departments need immediate coordination?",
            "What are the resource allocation priorities?",
            "What are the key operational bottlenecks?"
        ],
        'Comms': [
            "What messaging should we use for the public?",
            "How do we communicate evacuation instructions?",
            "What are the key talking points for media?"
        ],
        'Chief of Staff': [
            f"How do we deploy resources across {total_hotspots} hotspots?",
            "What's the timeline for emergency response?",
            "Which teams need activation?"
        ],
        'CE': [
            "What emergency services need deployment?",
            "What are the operational priorities?",
            "How do we ensure service continuity?"
        ],
        'Permanent Secretary': [
            "What protocols need to be followed?",
            "What are the long-term recovery considerations?",
            "What inter-governmental coordination is required?"
        ]
    }

    return role_suggestions.get(role, [
        "What are the priorities for this situation?",
        "What actions should be taken immediately?",
        "What resources are needed?"
    ])
