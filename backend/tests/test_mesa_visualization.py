"""
Visualize Mesa evacuation paths on London street network.
Creates an HTML map showing agent routes.
"""

import asyncio
import networkx as nx
from services.simulation_service import LondonGraphService
from services.mesa_simulation.mesa_executor import MesaSimulationExecutor
import folium
import random


async def create_path_visualization():
    """Create an HTML visualization of evacuation paths."""
    
    print("🗺️  Creating evacuation path visualization...\n")
    
    # Load London graph
    graph_service = LondonGraphService()
    graph = await graph_service.get_london_graph()
    
    print(f"✓ Loaded graph: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges\n")
    
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
    
    # Generate small number of agents for visualization
    print("Generating agent routes...\n")
    
    # Sample some nodes as origins and destinations
    nodes = list(graph.nodes())
    origins = random.sample(nodes, min(10, len(nodes)))
    destinations = random.sample(nodes, min(5, len(nodes)))
    
    agents_config = []
    colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 'lightred', 'beige', 'darkblue', 'darkgreen']
    
    for i, origin in enumerate(origins):
        dest = random.choice(destinations)
        
        try:
            route = nx.shortest_path(graph, origin, dest, weight='length')
            
            agents_config.append({
                'unique_id': i,
                'current_node': origin,
                'target_node': dest,
                'route': route,
                'speed': 1.2,
                'start_time': 0.0,
                'color': colors[i % len(colors)]
            })
        except nx.NetworkXNoPath:
            continue
    
    print(f"✓ Generated {len(agents_config)} agent routes\n")
    
    # Draw routes on map
    for agent in agents_config:
        route = agent['route']
        color = agent['color']
        
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
        
        # Draw route
        folium.PolyLine(
            route_coords,
            color=color,
            weight=3,
            opacity=0.7,
            popup=f"Agent {agent['unique_id']}: {len(route)} nodes"
        ).add_to(m)
        
        # Mark origin
        folium.CircleMarker(
            route_coords[0],
            radius=8,
            color=color,
            fill=True,
            fillColor=color,
            fillOpacity=0.8,
            popup=f"Agent {agent['unique_id']} Start"
        ).add_to(m)
        
        # Mark destination
        folium.CircleMarker(
            route_coords[-1],
            radius=8,
            color=color,
            fill=True,
            fillColor='white',
            fillOpacity=0.8,
            popup=f"Agent {agent['unique_id']} End",
            icon=folium.Icon(color=color, icon='flag')
        ).add_to(m)
    
    # Save map
    output_file = 'mesa_evacuation_paths.html'
    m.save(output_file)
    
    print(f"\n✅ Visualization saved to: {output_file}")
    print(f"\n📊 Summary:")
    print(f"  - Total agents visualized: {len(agents_config)}")
    print(f"  - Average route length: {sum(len(a['route']) for a in agents_config) / len(agents_config):.1f} nodes")
    
    # Print route details
    print(f"\n🛣️  Route Details:")
    for agent in agents_config:
        route_length = len(agent['route'])
        
        # Calculate total distance
        total_distance = 0
        for i in range(len(agent['route']) - 1):
            u, v = agent['route'][i], agent['route'][i+1]
            if v in graph[u]:
                edge_data = list(graph[u][v].values())[0]
                total_distance += edge_data.get('length', 0)
        
        print(f"  Agent {agent['unique_id']:2d}: {route_length:3d} nodes, {total_distance:7.1f}m ({total_distance/1000:.2f}km)")
    
    print(f"\n💡 Open '{output_file}' in your browser to view the evacuation paths!")
    
    return output_file


if __name__ == '__main__':
    asyncio.run(create_path_visualization())
