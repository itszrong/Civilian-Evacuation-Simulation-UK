"""
Context-Aware Chat API
Handles chat requests with page context injection for emergency planning assistance
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import structlog

from services.emergency_planner import EmergencyPlanningService
from services.storage_service import StorageService

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])

# Initialize services
emergency_service = EmergencyPlanningService()
storage_service = StorageService()

class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: str

class ChatContext(BaseModel):
    page: Optional[str] = None
    tab: Optional[str] = None
    timestamp: str

class ChatRequest(BaseModel):
    message: str
    role: str = "Prime Minister"
    context: Optional[ChatContext] = None
    conversation_history: List[ChatMessage] = []

class ChatResponse(BaseModel):
    response: str
    context_used: bool
    timestamp: str

@router.post("/chat", response_model=ChatResponse)
async def chat_with_context(request: ChatRequest):
    """
    Handle chat requests with page context integration using real LLM
    """
    try:
        logger.info("Context-aware chat request",
                   role=request.role,
                   context_page=request.context.page if request.context else None,
                   message_length=len(request.message))

        # Extract context data from the message if it contains context
        context_data = None
        actual_message = request.message
        
        if "## Current Page Context" in request.message:
            # Split the message to separate context from user question
            parts = request.message.split("---")
            if len(parts) >= 2:
                context_section = parts[0]
                actual_message = parts[1].replace("User Question:", "").strip()
                
                # Parse context data for intelligent responses
                context_data = parse_context_data(context_section)

        # Get emergency plan context (try to find existing plan)
        try:
            runs = await storage_service.list_all_runs()
            # Fix: Handle None city values properly
            london_runs = [r for r in runs if r.get('city') and r.get('city').lower() == 'london']
            
            plan = None
            if london_runs:
                plan = await storage_service.get_run_artifact(
                    run_id=london_runs[0]['run_id'],
                    artifact_type="emergency_plan"
                )
        except Exception as e:
            logger.warning(f"Could not load emergency plan: {e}")
            plan = None

        # Create enhanced context for LLM
        enhanced_context = create_enhanced_context(
            request.context, 
            context_data, 
            actual_message,
            plan
        )

        # Convert conversation history to dict format
        history = [
            {"role": msg.role, "content": msg.content, "timestamp": msg.timestamp}
            for msg in request.conversation_history
        ]

        # Get LLM response using existing emergency service with enhanced context
        response_text = await emergency_service.chat_response(
            role=request.role,
            question=actual_message,
            plan_context=enhanced_context,
            conversation_history=history
        )

        return ChatResponse(
            response=response_text,
            context_used=request.context is not None,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        # Fallback to contextual response if LLM fails
        fallback_response = generate_contextual_response(
            request.message, 
            request.role, 
            request.context,
            request.conversation_history
        )
        return ChatResponse(
            response=fallback_response,
            context_used=request.context is not None,
            timestamp=datetime.now().isoformat()
        )

def generate_contextual_response(
    message: str, 
    role: str, 
    context: Optional[ChatContext],
    history: List[ChatMessage]
) -> str:
    """
    Generate a contextual response based on the user's message and current page context
    """
    
    # Extract actual context data from the message if it contains context
    context_data = None
    actual_message = message
    
    if "## Current Page Context" in message:
        # Split the message to separate context from user question
        parts = message.split("---")
        if len(parts) >= 2:
            context_section = parts[0]
            actual_message = parts[1].replace("User Question:", "").strip()
            
            # Parse context data for intelligent responses
            context_data = parse_context_data(context_section)
    
    # Context-aware responses based on current page and actual data
    if context and context.page:
        page = context.page.lower()
        
        if "data sources" in page or "sources" in page:
            return generate_sources_response(actual_message, context_data, context, role)
        
        elif "borough" in page:
            return generate_borough_response(actual_message, context_data, context, role)
        
        elif "results" in page:
            return generate_results_response(actual_message, context_data, context, role)
    
    # Continue with other page handlers...
        
        elif "dashboard" in page:
            return f"""Welcome to the Emergency Planning Dashboard, {role}. This is your central command center for:

• Real-time threat detection from government and news sources
• Network simulation using A* pathfinding on real street data  
• Multi-agent AI for scenario generation and evaluation
• Performance metrics with traffic light indicators

Key capabilities at your disposal:
- Borough-level traffic light status monitoring
- Advanced simulation planning and execution
- Comprehensive results analysis and visualization
- Real-time data source management

What emergency planning task can I assist you with today?"""
        
        elif "results" in page:
            return """I can see you're reviewing simulation results. This section provides:

• Detailed evacuation scenario outcomes
• Performance metrics and success rates
• Visualization of evacuation routes and bottlenecks
• Comparative analysis across different scenarios

Key metrics to focus on:
- Evacuation completion time
- Population coverage and success rates
- Critical bottlenecks and failure points
- Resource utilization efficiency

Would you like help interpreting specific results or comparing scenarios?"""
        
        elif "plan" in page or "agentic" in page:
            return """You're in the Planning section where you can:

• Generate realistic evacuation scenarios using AI
• Configure simulation parameters and constraints
• Run advanced multi-agent simulations
• Optimize evacuation strategies

The agentic planner can help you:
- Create scenarios based on real threat intelligence
- Optimize resource allocation and routing
- Generate comparative studies
- Provide evidence-based recommendations

What type of evacuation scenario would you like to plan or analyze?"""
    
    # General responses for common queries
    if "help" in message.lower() or "what can you do" in message.lower():
        return f"""I'm your Emergency Response Assistant, {role}. I can help you with:

🚨 **Emergency Planning**
- Interpret evacuation simulation results
- Analyze public safety incidents and risk scores
- Review data source status and health
- Guide you through simulation planning

📊 **Data Analysis** 
- Explain performance metrics and trends
- Help interpret traffic light status indicators
- Analyze civil unrest detection results
- Review simulation queue priorities

🎯 **Decision Support**
- Provide context-aware recommendations
- Help prioritize emergency responses
- Explain system capabilities and limitations
- Guide you through complex workflows

I have access to your current page context, so I can provide specific guidance based on what you're viewing. What would you like assistance with?"""
    
    # Default contextual response
    if context and context.page:
        return f"""I can see you're currently on the {context.page} page{f' ({context.tab} tab)' if context.tab else ''}. 

I have access to the current page data and can help you understand:
- What the information means for emergency planning
- How to interpret the data and metrics
- What actions you can take from this page
- How this connects to other parts of the system

Please let me know what specific aspect you'd like help with, and I'll provide guidance based on your current context."""
    
    return f"""Hello {role}, I'm here to assist with emergency planning and evacuation coordination. 

While I don't have specific page context right now, I can help you with:
- Understanding simulation results and metrics
- Interpreting public safety incident analysis
- Managing data sources and feeds
- Planning and running evacuation scenarios

What would you like to know more about?"""

def parse_context_data(context_section: str) -> dict:
    """Parse context data from the formatted context string"""
    data = {}
    
    lines = context_section.split('\n')
    for line in lines:
        line = line.strip()
        if 'Data Sources:' in line:
            # Extract source counts: "2/6 operational"
            parts = line.split(':')[1].strip().split('/')
            if len(parts) >= 2:
                data['healthy_sources'] = int(parts[0])
                data['total_sources'] = int(parts[1].split()[0])
        
        elif 'Last Refresh:' in line:
            data['last_refresh'] = line.split(':', 1)[1].strip()
        
        elif 'Public Safety Incidents:' in line:
            # Extract incident counts: "5/100 articles flagged"
            parts = line.split(':')[1].strip().split('/')
            if len(parts) >= 2:
                data['unrest_articles'] = int(parts[0])
                data['total_articles'] = int(parts[1].split()[0])
        
        elif 'Simulation Candidates:' in line:
            # Extract candidate count: "3 requiring review"
            parts = line.split(':')[1].strip().split()
            if parts:
                data['simulation_candidates'] = int(parts[0])
        
        elif 'Highest Risk Score:' in line:
            # Extract risk score: "7.5/10"
            parts = line.split(':')[1].strip().split('/')
            if parts:
                data['highest_risk_score'] = float(parts[0])
        
        elif line.startswith('- ') and 'GOV.UK' in line or 'TfL' in line or 'BBC' in line:
            # Parse individual source status
            if 'sources' not in data:
                data['sources'] = []
            data['sources'].append(line[2:])  # Remove "- " prefix
        
        # Parse visualization data
        elif '**Active Scenario**:' in line:
            data['active_scenario'] = line.split(':', 1)[1].strip()
        
        elif '**Hazard Type**:' in line:
            data['hazard_type'] = line.split(':', 1)[1].strip()
        
        elif '**Evacuation Direction**:' in line:
            data['evacuation_direction'] = line.split(':', 1)[1].strip()
        
        elif '**Population Affected**:' in line:
            pop_str = line.split(':', 1)[1].strip().replace(',', '')
            if pop_str != 'Unknown':
                try:
                    data['population_affected'] = int(pop_str)
                except ValueError:
                    pass
        
        elif 'Clearance Time:' in line and 'minutes' in line:
            time_str = line.split(':')[1].strip().split()[0]
            try:
                data['clearance_time'] = float(time_str)
            except ValueError:
                pass
        
        elif 'Fairness Index:' in line:
            fairness_str = line.split(':')[1].strip()
            if fairness_str != 'N/A':
                try:
                    data['fairness_index'] = float(fairness_str)
                except ValueError:
                    pass
        
        elif 'Robustness Score:' in line:
            robustness_str = line.split(':')[1].strip()
            if robustness_str != 'N/A':
                try:
                    data['robustness'] = float(robustness_str)
                except ValueError:
                    pass
        
        elif 'Evacuation Efficiency:' in line:
            eff_str = line.split(':')[1].strip().replace('%', '')
            if eff_str != 'N/A':
                try:
                    data['evacuation_efficiency'] = float(eff_str)
                except ValueError:
                    pass
        
        elif 'A* Routes:' in line:
            routes_str = line.split(':')[1].strip()
            try:
                data['astar_routes'] = int(routes_str)
            except ValueError:
                pass
        
        elif 'Random Walks:' in line:
            walks_str = line.split(':')[1].strip()
            try:
                data['random_walks'] = int(walks_str)
            except ValueError:
                pass
        
        elif 'Interactive Map:' in line:
            data['has_interactive_map'] = 'Yes' in line
    
    return data

def create_enhanced_context(context: Optional[ChatContext], context_data: dict, message: str, plan: dict = None) -> dict:
    """Create enhanced context that combines page context with emergency plan data for LLM"""
    
    enhanced_context = {
        "total_hotspots": 0,
        "critical_hotspots": 0,
        "page_context": {},
        "current_situation": ""
    }
    
    # Add emergency plan data if available
    if plan:
        enhanced_context.update(plan)
    
    # Add page context information
    if context:
        enhanced_context["page_context"] = {
            "current_page": context.page,
            "current_tab": context.tab,
            "timestamp": context.timestamp
        }
        
        # Build current situation description from context data
        situation_parts = []
        
        if context_data:
            # Data sources information
            if 'total_sources' in context_data:
                healthy = context_data.get('healthy_sources', 0)
                total = context_data.get('total_sources', 0)
                situation_parts.append(f"Data Sources: {healthy}/{total} operational")
                
                if healthy < total:
                    situation_parts.append(f"⚠️ {total - healthy} sources need attention")
            
            # Public safety incidents
            if 'unrest_articles' in context_data:
                unrest = context_data.get('unrest_articles', 0)
                total_articles = context_data.get('total_articles', 0)
                situation_parts.append(f"Public Safety: {unrest}/{total_articles} articles flagged")
                
                candidates = context_data.get('simulation_candidates', 0)
                if candidates > 0:
                    situation_parts.append(f"🚨 {candidates} articles require immediate simulation review")
                
                if 'highest_risk_score' in context_data:
                    score = context_data['highest_risk_score']
                    risk_level = "High Risk" if score >= 7 else "Medium Risk" if score >= 4 else "Low Risk"
                    situation_parts.append(f"Highest Risk: {score}/10 ({risk_level})")
            
            # Individual source status
            if 'sources' in context_data and context_data['sources']:
                situation_parts.append("Source Status:")
                for source in context_data['sources'][:3]:
                    situation_parts.append(f"  • {source}")
            
            # Visualization/simulation data
            if 'active_scenario' in context_data:
                scenario_name = context_data.get('active_scenario', 'Unknown Scenario')
                hazard_type = context_data.get('hazard_type', 'unknown')
                situation_parts.append(f"Current Simulation: {scenario_name} ({hazard_type} emergency)")
                
                if 'evacuation_direction' in context_data:
                    direction = context_data['evacuation_direction']
                    situation_parts.append(f"Evacuation Pattern: {direction} evacuation")
                
                if 'population_affected' in context_data:
                    pop = context_data['population_affected']
                    situation_parts.append(f"Population at Risk: {pop:,} people")
                
                # Performance metrics
                metrics_summary = []
                if 'clearance_time' in context_data:
                    time = context_data['clearance_time']
                    assessment = "excellent" if time < 30 else "good" if time < 60 else "concerning" if time < 90 else "critical"
                    metrics_summary.append(f"clearance time {time:.1f}min ({assessment})")
                
                if 'fairness_index' in context_data:
                    fairness = context_data['fairness_index']
                    assessment = "excellent" if fairness > 0.8 else "good" if fairness > 0.6 else "poor" if fairness > 0.4 else "critical"
                    metrics_summary.append(f"fairness {fairness:.3f} ({assessment})")
                
                if 'robustness' in context_data:
                    robustness = context_data['robustness']
                    assessment = "excellent" if robustness > 0.8 else "good" if robustness > 0.6 else "concerning" if robustness > 0.4 else "critical"
                    metrics_summary.append(f"robustness {robustness:.3f} ({assessment})")
                
                if metrics_summary:
                    situation_parts.append(f"Performance Metrics: {', '.join(metrics_summary)}")
                
                # Infrastructure
                infra_parts = []
                if 'astar_routes' in context_data:
                    infra_parts.append(f"{context_data['astar_routes']} optimal routes")
                if 'random_walks' in context_data:
                    infra_parts.append(f"{context_data['random_walks']} pedestrian simulations")
                if 'has_interactive_map' in context_data and context_data['has_interactive_map']:
                    infra_parts.append("interactive map available")
                
                if infra_parts:
                    situation_parts.append(f"Simulation Infrastructure: {', '.join(infra_parts)}")
        
        # Add page-specific context
        if context.page:
            page_lower = context.page.lower()
            if "sources" in page_lower:
                situation_parts.append("User is currently viewing the Data Sources & Feeds management page")
                if context.tab:
                    tab_descriptions = {
                        "sources": "monitoring data source operational status",
                        "unrest": "reviewing public safety incident analysis", 
                        "queue": "managing simulation queue requests"
                    }
                    tab_desc = tab_descriptions.get(context.tab.lower(), f"on the {context.tab} tab")
                    situation_parts.append(f"Currently {tab_desc}")
            elif "dashboard" in page_lower:
                situation_parts.append("User is on the Emergency Planning Dashboard")
            elif "results" in page_lower:
                situation_parts.append("User is reviewing simulation results")
        
        enhanced_context["current_situation"] = ". ".join(situation_parts)
    
    # Add context-aware guidance
    enhanced_context["context_guidance"] = f"""
The user is asking: "{message}"

Current Context:
- Page: {context.page if context else 'Unknown'}
- Tab: {context.tab if context and context.tab else 'N/A'}
- Situation: {enhanced_context['current_situation']}

Please provide a response that:
1. Acknowledges what the user can see on their current page
2. Uses the actual live data from their screen
3. Provides role-specific guidance and recommendations
4. Suggests specific actions they can take from their current context
5. Uses a professional, government-appropriate tone
"""
    
    return enhanced_context

def generate_sources_response(message: str, context_data: dict, context: ChatContext, role: str = 'PM') -> str:
    """Generate intelligent response for Sources page based on actual data"""
    
    # Get current tab from context
    current_tab = getattr(context, 'tab', 'sources')
    
    # Get role title for personalized responses
    role_titles = {
        'PM': 'Prime Minister',
        'DPM': 'Deputy Prime Minister', 
        'Comms': 'Communications Director',
        'Chief of Staff': 'Chief of Staff',
        'CE': 'Chief Executive',
        'Permanent Secretary': 'Permanent Secretary'
    }
    role_title = role_titles.get(role, 'Prime Minister')
    
    # Handle general "what do you know" or "hello" type questions
    if any(phrase in message.lower() for phrase in ['what do you know', 'hello', 'what can you see', 'what data']):
        response = f"Based on your current Sources page, here's what I can see:\n\n"
        
        if context_data:
            # Use actual live data
            if 'total_sources' in context_data:
                healthy = context_data.get('healthy_sources', 0)
                total = context_data.get('total_sources', 0)
                response += f"**Data Sources Status**: {healthy}/{total} sources are currently operational\n"
                
                if healthy < total:
                    response += f"⚠️ {total - healthy} sources need attention\n"
                elif healthy == total and total > 0:
                    response += "✅ All data sources are healthy\n"
            
            if 'last_refresh' in context_data:
                response += f"**Last Refresh**: {context_data['last_refresh']}\n"
            
            if 'unrest_articles' in context_data:
                unrest = context_data.get('unrest_articles', 0)
                total_articles = context_data.get('total_articles', 0)
                response += f"\n**Public Safety Incidents**: {unrest}/{total_articles} articles flagged for review\n"
                
                if context_data.get('simulation_candidates', 0) > 0:
                    candidates = context_data['simulation_candidates']
                    response += f"🚨 **{candidates} articles require immediate simulation review**\n"
                
                if 'highest_risk_score' in context_data:
                    score = context_data['highest_risk_score']
                    risk_level = "High Risk" if score >= 7 else "Medium Risk" if score >= 4 else "Low Risk"
                    response += f"**Highest Risk Score**: {score}/10 ({risk_level})\n"
            
            if 'sources' in context_data and context_data['sources']:
                response += f"\n**Individual Source Status**:\n"
                for source in context_data['sources'][:3]:  # Show first 3
                    response += f"• {source}\n"
                if len(context_data['sources']) > 3:
                    response += f"• ...and {len(context_data['sources']) - 3} more sources\n"
        
        else:
            # Fallback when no context data available
            response += "I can see you're on the Sources page, but I don't have access to the current live data. You can:\n"
            response += "• Check data source operational status\n"
            response += "• Review public safety incident analysis\n"
            response += "• Monitor the simulation queue\n"
        
        response += f"\n**Current Tab**: {current_tab.title()}\n"
        
        # Add role-specific guidance
        role_guidance = {
            'PM': "\n**As Prime Minister**, you should focus on:\n• Strategic oversight of critical incidents\n• Public communication decisions\n• Inter-agency coordination priorities",
            'DPM': "\n**As Deputy PM**, your priorities are:\n• Operational coordination between departments\n• Resource allocation decisions\n• Supporting PM with strategic implementation",
            'Comms': "\n**As Communications Director**, focus on:\n• Public messaging about any incidents\n• Media coordination strategy\n• Clear communication of evacuation procedures",
            'Chief of Staff': "\n**As Chief of Staff**, coordinate:\n• Resource deployment across departments\n• Timeline management for responses\n• Team activation and assignments",
            'CE': "\n**As Chief Executive**, oversee:\n• Emergency service deployment\n• Operational implementation\n• Service continuity planning",
            'Permanent Secretary': "\n**As Permanent Secretary**, ensure:\n• Protocol compliance\n• Departmental coordination\n• Long-term recovery planning"
        }
        
        response += role_guidance.get(role, "")
        response += "\n\nWhat specific aspect would you like me to help you with?"
        
        return response
    
    # Handle specific questions about incidents
    elif any(phrase in message.lower() for phrase in ['incident', 'unrest', 'risk', 'score']):
        if context_data and 'unrest_articles' in context_data:
            unrest = context_data.get('unrest_articles', 0)
            total = context_data.get('total_articles', 0)
            candidates = context_data.get('simulation_candidates', 0)
            
            response = f"**Public Safety Incident Analysis**:\n\n"
            response += f"• **{unrest}/{total} articles** show incident indicators\n"
            response += f"• **{candidates} articles** require simulation review\n"
            
            if 'highest_risk_score' in context_data:
                score = context_data['highest_risk_score']
                response += f"• **Highest risk score**: {score}/10\n"
                
                if score >= 7:
                    response += "\n🚨 **HIGH RISK DETECTED** - Immediate attention required\n"
                    response += "This indicates potential riots, violent protests, or emergency situations.\n"
                elif score >= 4:
                    response += "\n⚠️ **MEDIUM RISK** - Monitor closely\n"
                    response += "This suggests large protests, strikes, or confrontational situations.\n"
            
            response += "\n**Risk Assessment Scale**:\n"
            response += "• 7-10: High Risk (riots, violence, emergencies)\n"
            response += "• 4-6: Medium Risk (large protests, strikes)\n"
            response += "• 2-3: Low Risk (peaceful demonstrations)\n"
            response += "• 0-1: Minimal Risk (routine events)\n"
            
            if candidates > 0:
                response += f"\n**Action Required**: {candidates} articles need your review for potential evacuation simulations."
            
            return response
        else:
            return "I can see you're asking about incidents, but I don't have access to the current incident analysis data. Please check the Public Safety Incidents tab for the latest risk assessments."
    
    # Handle questions about data sources
    elif any(phrase in message.lower() for phrase in ['source', 'feed', 'status', 'health']):
        if context_data and 'total_sources' in context_data:
            healthy = context_data.get('healthy_sources', 0)
            total = context_data.get('total_sources', 0)
            
            response = f"**Data Sources Status**:\n\n"
            response += f"• **{healthy}/{total} sources operational**\n"
            
            if healthy == total:
                response += "✅ All systems are running normally\n"
            else:
                failed = total - healthy
                response += f"⚠️ {failed} source{'s' if failed != 1 else ''} need{'s' if failed == 1 else ''} attention\n"
            
            if 'last_refresh' in context_data:
                response += f"• **Last updated**: {context_data['last_refresh']}\n"
            
            response += "\n**Configured Sources**:\n"
            response += "• **Government Primary**: GOV.UK Alerts, TfL Updates, Environment Agency, Met Office\n"
            response += "• **Verified News**: BBC London, Sky News\n"
            
            response += "\n**Available Actions**:\n"
            response += "• Refresh all sources to get latest data\n"
            response += "• Add new RSS feeds to the system\n"
            response += "• Review data compliance and retention policies\n"
            
            return response
        else:
            return "I can see you're asking about data sources, but I don't have access to the current source status. Please check the Data Sources tab for the latest operational status."
    
    # Default response for Sources page
    return f"""I can see you're on the Sources page{f' ({current_tab} tab)' if current_tab != 'sources' else ''}. This page manages:

• **Data Sources**: Monitor government and news feed operational status
• **Public Safety Incidents**: Real-time analysis of civil unrest indicators  
• **Simulation Queue**: Manage evacuation simulation requests

What specific information would you like me to help you understand?"""

def generate_borough_response(message: str, context_data: dict, context: ChatContext, role: str = 'PM') -> str:
    """Generate intelligent response for Borough Dashboard based on actual data"""
    
    # Get role title for personalized responses
    role_titles = {
        'PM': 'Prime Minister',
        'DPM': 'Deputy Prime Minister', 
        'Comms': 'Communications Director',
        'Chief of Staff': 'Chief of Staff',
        'CE': 'Chief Executive',
        'Permanent Secretary': 'Permanent Secretary'
    }
    role_title = role_titles.get(role, 'Prime Minister')
    
    # Handle general overview questions
    if any(phrase in message.lower() for phrase in ['what do you know', 'hello', 'overview', 'status', 'what can you see']):
        response = f"Based on your Borough Dashboard, here's the current situation:\n\n"
        
        if context_data:
            total_boroughs = context_data.get('totalBoroughs', 0)
            red_status = context_data.get('redStatusBoroughs', 0)
            amber_status = context_data.get('amberStatusBoroughs', 0)
            green_status = context_data.get('greenStatusBoroughs', 0)
            active_sims = context_data.get('activeSimulations', 0)
            
            response += f"**Borough Status Overview**:\n"
            response += f"• **{total_boroughs} boroughs** being monitored\n"
            
            if red_status > 0:
                response += f"🔴 **{red_status} boroughs** showing RED status - require immediate attention\n"
            if amber_status > 0:
                response += f"🟡 **{amber_status} boroughs** showing AMBER status - need monitoring\n"
            if green_status > 0:
                response += f"🟢 **{green_status} boroughs** showing GREEN status - performing well\n"
            
            if active_sims > 0:
                response += f"\n**Active Operations**: {active_sims} simulations currently running\n"
            
            # Search context
            if context_data.get('searchActive'):
                filtered_count = context_data.get('filteredBoroughs', 0)
                response += f"\n**Current Filter**: Showing {filtered_count} matching boroughs\n"
        
        # Add role-specific guidance
        role_guidance = {
            'PM': f"\n**As {role_title}**, focus on:\n• Red status boroughs requiring immediate intervention\n• Strategic resource allocation decisions\n• Public communication about any critical situations",
            'DPM': f"\n**As {role_title}**, coordinate:\n• Operational responses to amber/red status boroughs\n• Inter-agency resource deployment\n• Support for local emergency services",
            'Comms': f"\n**As {role_title}**, prepare:\n• Public messaging about borough status\n• Media briefings on emergency preparedness\n• Clear communication of evacuation procedures if needed",
            'Chief of Staff': f"\n**As {role_title}**, manage:\n• Resource deployment across affected boroughs\n• Coordination between departments\n• Timeline for emergency responses",
            'CE': f"\n**As {role_title}**, oversee:\n• Emergency service deployment to critical boroughs\n• Operational implementation of response plans\n• Service continuity across all areas",
            'Permanent Secretary': f"\n**As {role_title}**, ensure:\n• Protocol compliance in emergency responses\n• Departmental coordination for borough support\n• Long-term recovery planning for affected areas"
        }
        
        response += role_guidance.get(role, "")
        response += "\n\nWhat specific borough or aspect would you like me to focus on?"
        
        return response
    
    # Handle questions about specific status levels
    elif any(phrase in message.lower() for phrase in ['red', 'critical', 'urgent', 'emergency']):
        if context_data and context_data.get('redStatusBoroughs', 0) > 0:
            red_count = context_data['redStatusBoroughs']
            response = f"**CRITICAL ALERT**: {red_count} borough{'s' if red_count != 1 else ''} showing RED status\n\n"
            response += "Red status indicates critical issues with:\n"
            response += "• Clearance time (evacuation taking too long)\n"
            response += "• Fairness index (unequal evacuation access)\n"
            response += "• Robustness (system vulnerability)\n\n"
            response += f"**Immediate Action Required as {role_title}**:\n"
            response += "• Review detailed borough metrics\n"
            response += "• Deploy additional emergency resources\n"
            response += "• Consider escalating to COBRA if multiple boroughs affected\n"
            response += "• Prepare public communication strategy\n"
            return response
        else:
            return "Good news - no boroughs are currently showing RED critical status. All areas are within acceptable parameters."
    
    # Handle questions about performance metrics
    elif any(phrase in message.lower() for phrase in ['metrics', 'performance', 'clearance', 'fairness', 'robustness']):
        response = "**Borough Performance Metrics Explained**:\n\n"
        response += "• **Clearance Time**: How quickly the borough can be evacuated\n"
        response += "• **Fairness Index**: Equal access to evacuation routes for all residents\n"
        response += "• **Robustness**: System resilience under stress conditions\n\n"
        response += "**Traffic Light System**:\n"
        response += "🟢 **GREEN**: Optimal performance, no action needed\n"
        response += "🟡 **AMBER**: Acceptable but monitor closely\n"
        response += "🔴 **RED**: Critical issues requiring immediate intervention\n\n"
        
        if context_data:
            total = context_data.get('totalBoroughs', 0)
            if total > 0:
                green_pct = round((context_data.get('greenStatusBoroughs', 0) / total) * 100)
                response += f"**Current System Performance**: {green_pct}% of boroughs at optimal levels"
        
        return response
    
    # Default borough dashboard response
    return f"""I can see you're on the Borough Dashboard monitoring London's emergency preparedness status.

This executive dashboard shows:
• **Traffic light status** for all London boroughs
• **Real-time performance metrics** (clearance time, fairness, robustness)
• **Active simulation tracking** and historical trends

As {role_title}, you can use this to:
- Identify boroughs needing immediate attention (RED status)
- Monitor system-wide emergency preparedness
- Make strategic resource allocation decisions
- Track the effectiveness of emergency planning

What specific aspect of the borough status would you like me to explain?"""

def generate_results_response(message: str, context_data: dict, context: ChatContext, role: str = 'PM') -> str:
    """Generate intelligent response for Results page based on actual data"""
    
    role_titles = {
        'PM': 'Prime Minister',
        'DPM': 'Deputy Prime Minister', 
        'Comms': 'Communications Director',
        'Chief of Staff': 'Chief of Staff',
        'CE': 'Chief Executive',
        'Permanent Secretary': 'Permanent Secretary'
    }
    role_title = role_titles.get(role, 'Prime Minister')
    
    # Handle general overview questions and any question when we have visualization data
    overview_phrases = ['what do you know', 'hello', 'overview', 'results', 'what can you see', 'what do these', 'simulation results', 'tell us']
    action_phrases = ['next steps', 'what should', 'what else', 'recommendations', 'what now', 'what next', 'advice', 'suggest']
    analysis_phrases = ['what do you see', 'analyze', 'assessment', 'evaluation', 'performance', 'effectiveness']
    
    # If we have visualization data, respond to any question with analysis
    has_viz_data = context_data and 'active_scenario' in context_data
    is_question = any(phrase in message.lower() for phrase in overview_phrases + action_phrases + analysis_phrases)
    
    if has_viz_data or is_question:
        response = f"Based on the current simulation results, here's what I can analyze:\n\n"
        
        if context_data:
            # Check for visualization data first (new format)
            if 'active_scenario' in context_data:
                response += f"**Current Scenario**: {context_data['active_scenario']}\n"
                
                if 'hazard_type' in context_data:
                    response += f"**Emergency Type**: {context_data['hazard_type'].title()} incident\n"
                
                if 'evacuation_direction' in context_data:
                    response += f"**Evacuation Pattern**: {context_data['evacuation_direction'].title()} evacuation\n"
                
                if 'population_affected' in context_data:
                    response += f"**Population at Risk**: {context_data['population_affected']:,} people\n"
                
                response += f"\n**Evacuation Performance Analysis**:\n"
                
                if 'clearance_time' in context_data:
                    clearance = context_data['clearance_time']
                    if clearance < 30:
                        assessment = "Excellent - Very rapid evacuation"
                    elif clearance < 60:
                        assessment = "Good - Acceptable evacuation time"
                    elif clearance < 90:
                        assessment = "Concerning - Slow evacuation"
                    else:
                        assessment = "Critical - Dangerously slow evacuation"
                    response += f"• **Clearance Time**: {clearance:.1f} minutes ({assessment})\n"
                
                if 'fairness_index' in context_data:
                    fairness = context_data['fairness_index']
                    if fairness > 0.8:
                        fairness_assessment = "Excellent - Very equitable evacuation routes"
                    elif fairness > 0.6:
                        fairness_assessment = "Good - Reasonably fair distribution"
                    elif fairness > 0.4:
                        fairness_assessment = "Poor - Uneven evacuation access"
                    else:
                        fairness_assessment = "Critical - Highly inequitable evacuation"
                    response += f"• **Fairness Index**: {fairness:.3f} ({fairness_assessment})\n"
                
                if 'robustness' in context_data:
                    robustness = context_data['robustness']
                    if robustness > 0.8:
                        robustness_assessment = "Excellent - Highly resilient plan"
                    elif robustness > 0.6:
                        robustness_assessment = "Good - Reasonably robust"
                    elif robustness > 0.4:
                        robustness_assessment = "Concerning - Vulnerable to disruptions"
                    else:
                        robustness_assessment = "Critical - Very fragile evacuation plan"
                    response += f"• **Robustness Score**: {robustness:.3f} ({robustness_assessment})\n"
                
                if 'evacuation_efficiency' in context_data:
                    efficiency = context_data['evacuation_efficiency']
                    response += f"• **Overall Efficiency**: {efficiency:.1f}%\n"
                
                response += f"\n**Simulation Infrastructure**:\n"
                if 'astar_routes' in context_data:
                    response += f"• {context_data['astar_routes']} optimal evacuation routes calculated\n"
                if 'random_walks' in context_data:
                    response += f"• {context_data['random_walks']} pedestrian flow simulations\n"
                if 'has_interactive_map' in context_data:
                    map_status = "Available" if context_data['has_interactive_map'] else "Not available"
                    response += f"• Interactive visualization: {map_status}\n"
            
            # Fallback to old format if new format not available
            else:
                total_results = context_data.get('totalResults', 0)
                selected_run = context_data.get('selectedRun')
                active_tab = context_data.get('activeTab', 'overview')
                view_mode = context_data.get('viewMode', 'list')
                
                response += f"**Simulation Results**: {total_results} completed runs available\n"
                
                if selected_run:
                    response += f"**Currently Viewing**: Run {selected_run.get('run_id', 'Unknown')}\n"
                    if selected_run.get('city'):
                        response += f"**Target Area**: {selected_run['city'].title()}\n"
                    if selected_run.get('status'):
                        response += f"**Status**: {selected_run['status'].title()}\n"
                    
                    # Add metrics if available
                    if selected_run.get('metrics'):
                        metrics = selected_run['metrics']
                        response += f"\n**Key Metrics**:\n"
                        if 'evacuation_time_minutes' in metrics:
                            response += f"• Evacuation Time: {metrics['evacuation_time_minutes']} minutes\n"
                        if 'success_rate' in metrics:
                            response += f"• Success Rate: {metrics['success_rate']}%\n"
                        if 'population_evacuated' in metrics:
                            response += f"• Population Evacuated: {metrics['population_evacuated']:,}\n"
                
                response += f"\n**Current View**: {active_tab.title()} tab in {view_mode} mode\n"
        
        # Add specific recommendations based on the question type
        if any(phrase in message.lower() for phrase in action_phrases):
            response += f"\n**Recommended Next Steps**:\n"
            
            if context_data and 'fairness_index' in context_data:
                fairness = context_data['fairness_index']
                if fairness < 0.6:
                    response += f"• **Priority**: Address evacuation equity - fairness index of {fairness:.3f} indicates uneven access\n"
                    response += f"• Review evacuation routes in underserved areas\n"
                    response += f"• Consider additional transport resources for vulnerable populations\n"
            
            if context_data and 'clearance_time' in context_data:
                clearance = context_data['clearance_time']
                if clearance > 60:
                    response += f"• **Urgent**: Reduce evacuation time - {clearance:.1f} minutes is concerning\n"
                    response += f"• Identify and address bottlenecks in evacuation routes\n"
                    response += f"• Consider additional exit points or route optimization\n"
            
            if context_data and 'robustness' in context_data:
                robustness = context_data['robustness']
                if robustness < 0.7:
                    response += f"• **Resilience**: Strengthen plan robustness - current score {robustness:.3f} needs improvement\n"
                    response += f"• Develop contingency plans for route failures\n"
                    response += f"• Add redundancy to critical evacuation infrastructure\n"
            
            response += f"• Conduct tabletop exercises to test these scenarios\n"
            response += f"• Engage with local emergency services for implementation planning\n"
        
        # Add role-specific guidance
        role_guidance = {
            'PM': f"\n**As {role_title}**, focus on:\n• Overall evacuation effectiveness and success rates\n• Strategic implications of the results\n• Public communication about emergency preparedness",
            'DPM': f"\n**As {role_title}**, analyze:\n• Operational bottlenecks and resource needs\n• Coordination requirements between agencies\n• Implementation feasibility of recommendations",
            'Comms': f"\n**As {role_title}**, consider:\n• How to communicate results to the public\n• Key messages about emergency preparedness\n• Media briefing points from the analysis",
            'Chief of Staff': f"\n**As {role_title}**, review:\n• Resource allocation implications\n• Timeline for implementing improvements\n• Coordination needs across departments",
            'CE': f"\n**As {role_title}**, examine:\n• Operational implementation requirements\n• Service delivery improvements needed\n• Emergency response capability gaps",
            'Permanent Secretary': f"\n**As {role_title}**, assess:\n• Policy implications of the results\n• Long-term planning requirements\n• Compliance with emergency planning protocols"
        }
        
        response += role_guidance.get(role, "")
        response += "\n\nWhat specific aspect of the results would you like me to help you understand?"
        
        return response
    
    # Handle questions about specific metrics or performance
    elif any(phrase in message.lower() for phrase in ['metrics', 'performance', 'evacuation time', 'success rate']):
        response = "**Simulation Results Metrics Explained**:\n\n"
        response += "• **Evacuation Time**: Total time to evacuate the target area\n"
        response += "• **Success Rate**: Percentage of population successfully evacuated\n"
        response += "• **Bottlenecks**: Critical points that slow down evacuation\n"
        response += "• **Route Efficiency**: Effectiveness of evacuation paths\n"
        response += "• **Resource Utilization**: How well emergency resources were used\n\n"
        
        if context_data and context_data.get('selectedRunMetrics'):
            metrics = context_data['selectedRunMetrics']
            response += "**Current Run Performance**:\n"
            for key, value in metrics.items():
                if isinstance(value, (int, float)):
                    response += f"• {key.replace('_', ' ').title()}: {value}\n"
        
        response += f"\nAs {role_title}, use these metrics to make informed decisions about emergency planning improvements."
        return response
    
    # Default results response
    return f"""I can see you're reviewing simulation results for emergency evacuation planning.

This page provides:
• **Detailed analysis** of evacuation scenarios
• **Performance metrics** and success rates
• **Visualization** of evacuation routes and bottlenecks
• **Comparative analysis** across different scenarios

As {role_title}, you can use these results to:
- Assess emergency preparedness effectiveness
- Identify areas needing improvement
- Make evidence-based policy decisions
- Plan resource allocation for emergency services

What specific aspect of the results would you like me to analyze for you?"""
