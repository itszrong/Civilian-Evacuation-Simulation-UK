"""
DSPy Native Tool Implementation
Uses DSPy's built-in tool/function calling capabilities
"""

import structlog
from typing import Dict, Any, List
from datetime import datetime
import dspy

logger = structlog.get_logger(__name__)


def run_simulation_tool(city: str, hazard_type: str) -> str:
    """
    Trigger a new evacuation simulation.
    
    Args:
        city: The city to simulate (London, Westminster, Camden, etc.)
        hazard_type: Type of emergency (flood, fire, terrorist_attack, chemical_spill, earthquake)
    
    Returns:
        Status message with run_id
    """
    try:
        from api.simulation_queue import queue_service, SimulationRequest
        import uuid
        
        logger.info(f"DSPy tool: Queuing simulation for {city}, {hazard_type}")
        
        # Check for existing simulation with same city and hazard type
        existing_simulations = [
            req for req in queue_service.requests
            if req.suggested_regions and req.suggested_regions[0].lower() == city.lower()
            and req.status in ["pending", "approved", "running"]
        ]
        
        if existing_simulations:
            existing = existing_simulations[0]
            return f"ℹ️ A simulation for {city} is already {existing.status} (ID: {existing.id}). Please wait for it to complete before requesting a new one."
        
        # Create a simulation request
        sim_request = SimulationRequest(
            article_id=f"chat-{uuid.uuid4()}",
            article_title=f"{hazard_type.title()} Simulation for {city}",
            article_summary=f"Emergency evacuation simulation requested via chat tool",
            civil_unrest_score=7.0,
            suggested_regions=[city],
            status="pending"
        )
        
        # Add to queue using the synchronous service
        added_request = queue_service.add_request(sim_request)
        
        return f"✅ Queued {hazard_type} simulation for {city}. Run ID: {added_request.id}. The simulation will start shortly."
        
    except Exception as e:
        logger.error(f"Simulation tool failed: {e}", exc_info=True)
        return f"❌ Error: Could not queue simulation - {str(e)}"


def get_simulation_status_tool(run_id: str) -> str:
    """
    Check the status of a running simulation.
    
    Args:
        run_id: The unique identifier of the simulation run
    
    Returns:
        Status information
    """
    try:
        from api.simulation_queue import get_queue_status
        
        # Get queue status (handles async internally)
        status_data = get_queue_status()
        
        # Check if run_id is in pending or processing
        for req in status_data.get('pending', []):
            if req.get('run_id') == run_id:
                return f"⏳ Simulation {run_id} is pending in queue (position: {status_data['pending'].index(req) + 1})"
        
        for req in status_data.get('processing', []):
            if req.get('run_id') == run_id:
                return f"⚙️ Simulation {run_id} is currently processing..."
        
        # Check completed
        for req in status_data.get('completed', [])[:10]:  # Last 10
            if req.get('run_id') == run_id:
                return f"✅ Simulation {run_id} completed successfully!"
        
        return f"❓ Simulation {run_id} not found in queue. It may have completed and been archived."
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return f"❌ Error: Could not check status - {str(e)}"


def list_recent_simulations_tool(limit: int = 5) -> str:
    """
    List recent evacuation simulations.
    
    Args:
        limit: Maximum number of simulations to return (default 5)
    
    Returns:
        List of recent simulations
    """
    try:
        from api.simulation_queue import get_queue_status
        
        # Get queue status (handles async internally)
        status_data = get_queue_status()
        
        # Combine completed and processing simulations
        all_sims = []
        
        # Add completed (most recent first)
        completed = status_data.get('completed', [])[:limit]
        for sim in completed:
            all_sims.append({
                'run_id': sim.get('run_id', 'unknown')[:8],  # Short ID
                'city': sim.get('city', 'unknown'),
                'status': 'completed',
                'hazard': sim.get('hazard_type', 'N/A')
            })
        
        # Add processing
        for sim in status_data.get('processing', []):
            if len(all_sims) >= limit:
                break
            all_sims.append({
                'run_id': sim.get('run_id', 'unknown')[:8],
                'city': sim.get('city', 'unknown'),
                'status': 'processing',
                'hazard': sim.get('hazard_type', 'N/A')
            })
        
        # Add pending
        for sim in status_data.get('pending', []):
            if len(all_sims) >= limit:
                break
            all_sims.append({
                'run_id': sim.get('run_id', 'unknown')[:8],
                'city': sim.get('city', 'unknown'),
                'status': 'pending',
                'hazard': sim.get('hazard_type', 'N/A')
            })
        
        if not all_sims:
            return "📋 No recent simulations found. Try running a simulation first!"
        
        result = f"📋 Recent Simulations ({len(all_sims)}):\n"
        for sim in all_sims:
            status_icon = "✅" if sim['status'] == 'completed' else "⚙️" if sim['status'] == 'processing' else "⏳"
            result += f"{status_icon} {sim['run_id']}... - {sim['city'].title()} ({sim['hazard']}) - {sim['status']}\n"
        
        return result
        
    except Exception as e:
        logger.error(f"List simulations failed: {e}")
        return f"❌ Error: Could not list simulations - {str(e)}"


def get_borough_status_tool(borough_name: str) -> str:
    """
    Get emergency preparedness status of a London borough.
    
    Args:
        borough_name: Name of the borough (Westminster, Camden, etc.)
    
    Returns:
        Borough status information
    """
    try:
        # Mock data for now
        return f"🏙️ {borough_name}: Status=AMBER, Clearance=45min, Fairness=0.67, Robustness=0.82"
    except Exception as e:
        return f"❌ Error: {str(e)}"


# Register tools with DSPy
def get_dspy_tools() -> List:
    """Get list of DSPy-compatible tools."""
    return [
        dspy.Tool(
            func=run_simulation_tool,
            name="run_simulation",
            desc="Start a new evacuation simulation for a city with a specific hazard type"
        ),
        dspy.Tool(
            func=get_simulation_status_tool,
            name="get_simulation_status", 
            desc="Check the status and progress of a specific simulation run"
        ),
        dspy.Tool(
            func=list_recent_simulations_tool,
            name="list_recent_simulations",
            desc="List the most recent evacuation simulation runs"
        ),
        dspy.Tool(
            func=get_borough_status_tool,
            name="get_borough_status",
            desc="Get the emergency preparedness status of a London borough"
        )
    ]
