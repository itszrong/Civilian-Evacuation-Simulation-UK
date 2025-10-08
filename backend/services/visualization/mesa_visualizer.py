"""
Mesa Visualization Service for generating agent route maps.

This service wraps the test_mesa_visualization.py logic into a reusable service
that generates static HTML maps showing evacuation routes on street networks.
"""

import asyncio
import random
from pathlib import Path
from typing import Dict, List, Any, Optional
import networkx as nx
import folium
import structlog

logger = structlog.get_logger(__name__)


class MesaVisualizationService:
    """Service for generating Mesa agent route visualizations."""
    
    def __init__(self, output_dir: str = "visualizations"):
        """
        Initialize the Mesa visualization service.
        
        Args:
            output_dir: Directory to save generated HTML files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def create_routes_visualization(
        self,
        agents_data: List[Dict[str, Any]],
        graph: nx.MultiDiGraph,
        simulation_id: str,
        title: str = "Evacuation Agent Routes"
    ) -> str:
        """
        Create a static HTML visualization showing agent routes on map.
        
        Args:
            agents_data: List of agent dictionaries with route information
            graph: NetworkX graph representing street network
            simulation_id: Unique identifier for this simulation
            title: Title for the visualization
            
        Returns:
            Path to generated HTML file
        """
        logger.info("Creating Mesa routes visualization",
                   simulation_id=simulation_id,
                   num_agents=len(agents_data))
        
        try:
            # Get graph center for map
            lats = [data['y'] for node, data in graph.nodes(data=True) if 'y' in data]
            lons = [data['x'] for node, data in graph.nodes(data=True) if 'x' in data]
            
            if not lats or not lons:
                logger.error("No valid coordinates found in graph")
                return ""
            
            center_lat = sum(lats) / len(lats)
            center_lon = sum(lons) / len(lons)
            
            # Create base map
            m = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=14,
                tiles='OpenStreetMap'
            )
            
            # Add borough boundaries if available
            self._add_borough_boundaries(m, graph)
            
            # Add title with auto-sizing
            title_html = f'''
                <div style="position: fixed; 
                            top: 10px; left: 50px; 
                            min-width: 300px; max-width: 600px;
                            width: auto; height: auto;
                            background-color: white; border: 2px solid grey;
                            z-index: 9999; font-size: 14px; padding: 15px;
                            box-shadow: 0 0 10px rgba(0,0,0,0.3);
                            border-radius: 5px;">
                    <b style="font-size: 16px;">{title}</b><br>
                    <span style="font-size: 12px; color: #666;">
                        Agents: {len(agents_data)} | Simulation ID: {simulation_id[:12]}
                    </span>
                </div>
            '''
            m.get_root().html.add_child(folium.Element(title_html))
            
            # Color palette for routes
            colors = [
                'red', 'blue', 'green', 'purple', 'orange', 
                'darkred', 'lightred', 'beige', 'darkblue', 'darkgreen',
                'cadetblue', 'darkpurple', 'pink', 'lightblue', 'lightgreen'
            ]
            
            # Track statistics
            total_distance = 0
            total_nodes = 0
            valid_routes = 0
            
            # Draw routes on map
            for i, agent in enumerate(agents_data):
                route = agent.get('route', [])
                if not route or len(route) < 2:
                    continue
                
                color = colors[i % len(colors)]
                
                # Get coordinates for route
                route_coords = []
                for node in route:
                    if node in graph.nodes() and 'y' in graph.nodes[node] and 'x' in graph.nodes[node]:
                        route_coords.append([
                            graph.nodes[node]['y'],
                            graph.nodes[node]['x']
                        ])
                
                if len(route_coords) < 2:
                    continue
                
                # Calculate route distance
                route_distance = 0
                for j in range(len(route) - 1):
                    u, v = route[j], route[j+1]
                    if v in graph[u]:
                        edge_data = list(graph[u][v].values())[0]
                        route_distance += edge_data.get('length', 0)
                
                total_distance += route_distance
                total_nodes += len(route)
                valid_routes += 1
                
                # Draw route
                folium.PolyLine(
                    route_coords,
                    color=color,
                    weight=3,
                    opacity=0.7,
                    popup=f"Agent {agent.get('unique_id', i)}: {len(route)} nodes, {route_distance/1000:.2f}km"
                ).add_to(m)
                
                # Mark origin
                folium.CircleMarker(
                    route_coords[0],
                    radius=8,
                    color=color,
                    fill=True,
                    fillColor=color,
                    fillOpacity=0.8,
                    popup=f"Agent {agent.get('unique_id', i)} Start"
                ).add_to(m)
                
                # Mark destination
                folium.CircleMarker(
                    route_coords[-1],
                    radius=8,
                    color=color,
                    fill=True,
                    fillColor='white',
                    fillOpacity=0.8,
                    popup=f"Agent {agent.get('unique_id', i)} End"
                ).add_to(m)
            
            # Add legend with statistics
            if valid_routes > 0:
                avg_distance = total_distance / valid_routes / 1000
                avg_nodes = total_nodes / valid_routes
                
                legend_html = f'''
                    <div style="position: fixed; 
                                bottom: 50px; left: 50px; width: 250px;
                                background-color: white; border: 2px solid grey;
                                z-index: 9999; font-size: 12px; padding: 10px;
                                box-shadow: 0 0 10px rgba(0,0,0,0.3);">
                        <b>Route Statistics</b><br>
                        <b>Total Routes:</b> {valid_routes}<br>
                        <b>Avg Distance:</b> {avg_distance:.2f} km<br>
                        <b>Avg Path Length:</b> {avg_nodes:.1f} nodes<br>
                        <hr style="margin: 5px 0;">
                        <b>Legend:</b><br>
                        ● Filled circle = Origin<br>
                        ○ White circle = Destination<br>
                        ─ Colored line = Route
                    </div>
                '''
                m.get_root().html.add_child(folium.Element(legend_html))
            
            # Save map
            output_file = self.output_dir / f"{simulation_id}_mesa_routes.html"
            m.save(str(output_file))
            
            logger.info("Mesa visualization created successfully",
                       simulation_id=simulation_id,
                       file=str(output_file),
                       valid_routes=valid_routes)
            
            return str(output_file)
            
        except Exception as e:
            logger.error("Failed to create Mesa visualization",
                        simulation_id=simulation_id,
                        error=str(e))
            return ""
    
    async def create_routes_from_mesa_results(
        self,
        mesa_results: Dict[str, Any],
        graph: nx.MultiDiGraph,
        simulation_id: str
    ) -> str:
        """
        Create visualization from Mesa simulation results.
        
        Args:
            mesa_results: Results dictionary from Mesa simulation
            graph: NetworkX graph
            simulation_id: Unique simulation identifier
            
        Returns:
            Path to generated HTML file
        """
        # Extract agent data from Mesa results
        agents_data = mesa_results.get('agent_data', [])
        
        if not agents_data:
            logger.warning("No agent data in Mesa results, generating sample routes",
                         simulation_id=simulation_id)
            # Generate sample routes for visualization
            agents_data = await self._generate_sample_routes(graph, num_agents=10)
        
        return await self.create_routes_visualization(
            agents_data=agents_data,
            graph=graph,
            simulation_id=simulation_id,
            title="Mesa Agent Evacuation Routes"
        )
    
    async def _generate_sample_routes(
        self,
        graph: nx.MultiDiGraph,
        num_agents: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Generate sample agent routes for visualization when no agent data available.
        
        Args:
            graph: NetworkX graph
            num_agents: Number of sample agents to generate
            
        Returns:
            List of agent dictionaries with route information
        """
        logger.info("Generating sample routes for visualization", num_agents=num_agents)
        
        nodes = list(graph.nodes())
        if len(nodes) < 2:
            return []
        
        # Sample origins and destinations
        num_agents = min(num_agents, len(nodes) // 2)
        origins = random.sample(nodes, num_agents)
        destinations = random.sample(nodes, min(5, len(nodes)))
        
        agents_data = []
        colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 
                 'lightred', 'beige', 'darkblue', 'darkgreen']
        
        for i, origin in enumerate(origins):
            dest = random.choice(destinations)
            
            try:
                route = nx.shortest_path(graph, origin, dest, weight='length')
                
                agents_data.append({
                    'unique_id': i,
                    'current_node': origin,
                    'target_node': dest,
                    'route': route,
                    'speed': 1.2,
                    'start_time': 0.0,
                    'color': colors[i % len(colors)]
                })
            except nx.NetworkXNoPath:
                # Skip if no path exists
                continue
        
        logger.info("Sample routes generated", count=len(agents_data))
        return agents_data
    
    def _add_borough_boundaries(self, m: folium.Map, graph: nx.MultiDiGraph) -> None:
        """
        Add borough boundaries to the map by identifying borough regions.
        
        Args:
            m: Folium map object
            graph: NetworkX graph with borough information
        """
        try:
            from scipy.spatial import ConvexHull
            import numpy as np
            
            # Extract nodes by borough
            borough_nodes = {}
            for node, data in graph.nodes(data=True):
                if 'y' not in data or 'x' not in data:
                    continue
                
                # Try to get borough from node or edges
                borough = None
                
                # Check if node has borough attribute
                if 'borough' in data:
                    borough = data['borough']
                else:
                    # Check outgoing edges for borough info
                    for neighbor in graph.neighbors(node):
                        for edge_key in graph[node][neighbor]:
                            edge_data = graph[node][neighbor][edge_key]
                            if 'borough' in edge_data:
                                borough = edge_data['borough']
                                break
                        if borough:
                            break
                
                if borough and borough != "":
                    if borough not in borough_nodes:
                        borough_nodes[borough] = []
                    borough_nodes[borough].append([data['y'], data['x']])
            
            # Define colors for boroughs
            borough_colors = {
                'Westminster': '#e74c3c',
                'Camden': '#3498db',
                'Islington': '#2ecc71',
                'Hackney': '#f39c12',
                'Tower_Hamlets': '#9b59b6',
                'Southwark': '#1abc9c',
                'Lambeth': '#e67e22',
                'Wandsworth': '#34495e',
            }
            
            # Draw convex hull for each borough
            for borough, nodes in borough_nodes.items():
                if len(nodes) < 3:  # Need at least 3 points for a hull
                    continue
                
                try:
                    points = np.array(nodes)
                    hull = ConvexHull(points)
                    
                    # Get hull boundary points
                    boundary_points = points[hull.vertices].tolist()
                    
                    # Close the polygon
                    boundary_points.append(boundary_points[0])
                    
                    # Use black for all borough boundaries for better visibility
                    color = 'black'
                    
                    # Draw borough boundary with thick black outline
                    folium.PolyLine(
                        boundary_points,
                        color=color,
                        weight=5,
                        opacity=1.0,
                        dash_array='10, 5',
                        popup=f"Borough: {borough}"
                    ).add_to(m)
                    
                    # Add borough label at centroid with better visibility
                    label_color = borough_colors.get(borough, '#333333')
                    centroid = points[hull.vertices].mean(axis=0)
                    folium.Marker(
                        location=[centroid[0], centroid[1]],
                        icon=folium.DivIcon(html=f'''
                            <div style="font-size: 12pt; color: {label_color}; 
                                        font-weight: bold; 
                                        text-shadow: 2px 2px 4px white, -1px -1px 2px white;">
                                {borough.replace('_', ' ')}
                            </div>
                        ''')
                    ).add_to(m)
                    
                except Exception as e:
                    logger.debug(f"Could not create boundary for {borough}: {e}")
                    continue
            
            logger.info(f"Added {len(borough_nodes)} borough boundaries to map")
            
        except ImportError:
            logger.warning("scipy not available, skipping borough boundaries")
        except Exception as e:
            logger.warning(f"Could not add borough boundaries: {e}")
    
    async def create_density_heatmap(
        self,
        agents_data: List[Dict[str, Any]],
        graph: nx.MultiDiGraph,
        simulation_id: str
    ) -> str:
        """
        Create interactive HTML heatmap showing route density and congestion.
        
        Args:
            agents_data: List of agent dictionaries with route information
            graph: NetworkX graph representing street network
            simulation_id: Unique identifier for this simulation
            
        Returns:
            Path to generated HTML file
        """
        logger.info("Creating route density heatmap",
                   simulation_id=simulation_id,
                   num_agents=len(agents_data))
        
        try:
            from collections import Counter
            import numpy as np
            
            # Count edge usage
            edge_usage = Counter()
            for agent in agents_data:
                route = agent.get('route', [])
                for i in range(len(route) - 1):
                    edge = (route[i], route[i+1])
                    edge_usage[edge] += 1
            
            if not edge_usage:
                logger.warning("No route data for density heatmap")
                return ""
            
            # Get graph center for map
            lats = [data['y'] for node, data in graph.nodes(data=True) if 'y' in data]
            lons = [data['x'] for node, data in graph.nodes(data=True) if 'x' in data]
            
            center_lat = sum(lats) / len(lats)
            center_lon = sum(lons) / len(lons)
            
            # Create base map
            m = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=14,
                tiles='OpenStreetMap'
            )
            
            # Add borough boundaries
            self._add_borough_boundaries(m, graph)
            
            # Calculate color scale
            usage_values = list(edge_usage.values())
            max_usage = max(usage_values)
            min_usage = min(usage_values)
            
            # Draw edges with color based on usage
            for (u, v), count in edge_usage.items():
                if u not in graph.nodes() or v not in graph.nodes():
                    continue
                
                if 'y' not in graph.nodes[u] or 'x' not in graph.nodes[u]:
                    continue
                if 'y' not in graph.nodes[v] or 'x' not in graph.nodes[v]:
                    continue
                
                coords = [
                    [graph.nodes[u]['y'], graph.nodes[u]['x']],
                    [graph.nodes[v]['y'], graph.nodes[v]['x']]
                ]
                
                # Normalize usage to 0-1 scale
                normalized = (count - min_usage) / (max_usage - min_usage) if max_usage > min_usage else 0.5
                
                # Color from green (low) to yellow to red (high)
                if normalized < 0.5:
                    # Green to yellow
                    r = int(255 * (normalized * 2))
                    g = 255
                    b = 0
                else:
                    # Yellow to red
                    r = 255
                    g = int(255 * (1 - (normalized - 0.5) * 2))
                    b = 0
                
                color = f'#{r:02x}{g:02x}{b:02x}'
                
                # Line weight based on usage
                weight = 2 + (normalized * 8)  # 2-10 pixels
                
                # Determine congestion level
                percentile_90 = np.percentile(usage_values, 90)
                percentile_75 = np.percentile(usage_values, 75)
                
                if count >= percentile_90:
                    level = "CRITICAL"
                elif count >= percentile_75:
                    level = "HIGH"
                else:
                    level = "MODERATE"
                
                folium.PolyLine(
                    coords,
                    color=color,
                    weight=weight,
                    opacity=0.7,
                    popup=f"Edge Usage: {count} agents<br>Congestion: {level}"
                ).add_to(m)
            
            # Add title
            title_html = f'''
                <div style="position: fixed; 
                            top: 10px; left: 50px; 
                            min-width: 350px; max-width: 600px;
                            width: auto; height: auto;
                            background-color: white; border: 2px solid grey;
                            z-index: 9999; font-size: 14px; padding: 15px;
                            box-shadow: 0 0 10px rgba(0,0,0,0.3);
                            border-radius: 5px;">
                    <b style="font-size: 16px;">Route Density Heatmap</b><br>
                    <span style="font-size: 12px; color: #666;">
                        Total Edges: {len(edge_usage)} | Max Usage: {max_usage} agents
                    </span>
                </div>
            '''
            m.get_root().html.add_child(folium.Element(title_html))
            
            # Add legend
            legend_html = f'''
                <div style="position: fixed; 
                            bottom: 50px; left: 50px; width: 280px;
                            background-color: white; border: 2px solid grey;
                            z-index: 9999; font-size: 12px; padding: 15px;
                            box-shadow: 0 0 10px rgba(0,0,0,0.3);
                            border-radius: 5px;">
                    <b style="font-size: 14px;">Congestion Levels</b><br><br>
                    <div style="display: flex; align-items: center; margin: 5px 0;">
                        <div style="width: 40px; height: 4px; background: #00ff00; margin-right: 10px;"></div>
                        <span>Low (Green)</span>
                    </div>
                    <div style="display: flex; align-items: center; margin: 5px 0;">
                        <div style="width: 40px; height: 4px; background: #ffff00; margin-right: 10px;"></div>
                        <span>Moderate (Yellow)</span>
                    </div>
                    <div style="display: flex; align-items: center; margin: 5px 0;">
                        <div style="width: 40px; height: 4px; background: #ff0000; margin-right: 10px;"></div>
                        <span>High/Critical (Red)</span>
                    </div>
                    <hr style="margin: 10px 0;">
                    <b>Statistics:</b><br>
                    <b>Total Routes:</b> {len(agents_data)}<br>
                    <b>Edges Used:</b> {len(edge_usage)}<br>
                    <b>Max Usage:</b> {max_usage} agents<br>
                    <b>Avg Usage:</b> {np.mean(usage_values):.1f} agents<br>
                    <small style="color: #666; margin-top: 5px; display: block;">
                        Line thickness = usage intensity
                    </small>
                </div>
            '''
            m.get_root().html.add_child(folium.Element(legend_html))
            
            # Save map
            output_file = self.output_dir / f"{simulation_id}_density_heatmap.html"
            m.save(str(output_file))
            
            logger.info("Density heatmap created successfully",
                       simulation_id=simulation_id,
                       file=str(output_file),
                       edges_visualized=len(edge_usage))
            
            return str(output_file)
            
        except Exception as e:
            logger.error("Failed to create density heatmap",
                        simulation_id=simulation_id,
                        error=str(e))
            return ""
