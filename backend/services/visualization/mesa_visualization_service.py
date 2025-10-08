"""
Mesa Agent Visualization Service.
Generates Folium maps showing Mesa agent evacuation routes.
"""

import folium
from typing import Dict, List, Any
import networkx as nx
import structlog
import random

logger = structlog.get_logger(__name__)


class MesaVisualizationService:
    """Service for generating Mesa agent path visualizations."""
    
    def generate_agent_route_map(
        self,
        graph: nx.MultiDiGraph,
        agent_data: List[Dict[str, Any]],
        city_name: str
    ) -> str:
        """
        Generate Folium map showing Mesa agent evacuation routes.
        
        Args:
            graph: NetworkX street network graph
            agent_data: List of agent configs with routes
            city_name: Name of city for map title
            
        Returns:
            HTML string of folium map
        """
        logger.info(f"Generating Mesa agent route visualization for {city_name}")
        
        # Get map center from graph
        nodes = list(graph.nodes())
        if not nodes:
            return "<p>No graph data available</p>"
            
        lats = [graph.nodes[n]['y'] for n in nodes[:100]]
        lons = [graph.nodes[n]['x'] for n in nodes[:100]]
        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)
        
        # Create folium map
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=14,
            tiles='OpenStreetMap'
        )
        
        # Add agent routes (sample to avoid overcrowding)
        sample_size = min(50, len(agent_data))  # Show up to 50 agent routes
        sampled_agents = random.sample(agent_data, sample_size) if len(agent_data) > sample_size else agent_data
        
        colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 'darkblue', 'darkgreen']
        
        for i, agent in enumerate(sampled_agents):
            route = agent.get('route', [])
            if not route or len(route) < 2:
                continue
                
            try:
                # Convert route node IDs to coordinates
                route_coords = []
                for node_id in route[:20]:  # Limit to first 20 nodes per route for clarity
                    if node_id in graph.nodes:
                        node_data = graph.nodes[node_id]
                        route_coords.append([node_data['y'], node_data['x']])
                
                if len(route_coords) < 2:
                    continue
                    
                # Add route polyline
                color = colors[i % len(colors)]
                folium.PolyLine(
                    route_coords,
                    color=color,
                    weight=2,
                    opacity=0.6,
                    popup=f"Agent {agent.get('unique_id')} - Speed: {agent.get('speed', 0):.1f}m/s"
                ).add_to(m)
                
                # Add start marker
                if i < 10:  # Only show markers for first 10 agents to avoid clutter
                    folium.CircleMarker(
                        route_coords[0],
                        radius=4,
                        color=color,
                        fill=True,
                        popup=f"Agent {agent.get('unique_id')} Start"
                    ).add_to(m)
                    
            except Exception as e:
                logger.warning(f"Failed to visualize agent {agent.get('unique_id')}: {e}")
                continue
        
        # Add title
        title_html = f'''
        <div style="position: fixed; 
                    top: 10px; left: 50px; width: 400px; height: 60px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:14px; padding: 10px;">
        <b>Mesa Agent Evacuation Routes - {city_name.title()}</b><br>
        Showing {sample_size} agent paths from city center to boundaries
        </div>
        '''
        m.get_root().html.add_child(folium.Element(title_html))
        
        logger.info(f"Generated Mesa visualization with {sample_size} agent routes")
        return m._repr_html_()
