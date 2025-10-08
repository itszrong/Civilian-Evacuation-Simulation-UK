"""
Simulation Executor Service
Handles evacuation simulation execution, scenario generation, and multi-city coordination.
Extracted from multi_city_orchestrator.py to improve code organization.

This is the most complex service as it coordinates all other services to run simulations.
"""

from typing import Dict, List, Optional, Any, Tuple
import random
import asyncio
import numpy as np
from scipy.stats import gaussian_kde
from datetime import datetime
import networkx as nx
import osmnx as ox
import folium
import structlog

from services.geography.city_resolver_service import CityResolverService
from services.geography.graph_loader_service import GraphLoaderService
from services.visualization.map_visualization_service import MapVisualizationService
from services.metrics.evacuation_metrics_calculator import EvacuationMetricsCalculator

logger = structlog.get_logger(__name__)


class SimulationExecutorService:
    """
    Service for executing evacuation simulations with multiple scenarios and variations.
    
    This service coordinates graph loading, simulation execution, visualization generation,
    and metrics calculation to produce comprehensive evacuation simulation results.
    """
    
    def __init__(
        self,
        city_resolver: Optional[CityResolverService] = None,
        graph_loader: Optional[GraphLoaderService] = None,
        visualization: Optional[MapVisualizationService] = None,
        metrics_calculator: Optional[EvacuationMetricsCalculator] = None
    ):
        """
        Initialize the simulation executor with dependencies.
        
        Args:
            city_resolver: Service for city name resolution
            graph_loader: Service for graph loading and caching
            visualization: Service for map/plot generation
            metrics_calculator: Service for metrics calculation
        """
        self.city_resolver = city_resolver or CityResolverService()
        self.graph_loader = graph_loader or GraphLoaderService()
        self.visualization = visualization or MapVisualizationService()
        self.metrics_calculator = metrics_calculator or EvacuationMetricsCalculator()
    
    def biased_random_walk(
        self,
        graph: nx.MultiDiGraph,
        start_node,
        target_node,
        steps: int = 1000,
        bias_probability: float = 0.4
    ) -> List:
        """
        Perform biased random walk on street network graph.
        
        Args:
            graph: Street network graph
            start_node: Starting node
            target_node: Target node (e.g., southernmost)
            steps: Maximum steps to walk
            bias_probability: Probability of biased movement
            
        Returns:
            List of nodes traversed in the walk
        """
        current_node = start_node
        walk = [current_node]
        
        northernmost_node = max(graph.nodes, key=lambda n: graph.nodes[n]['y'])
        bias_directions = ['north', 'south', 'east', 'west']
        bias_direction = random.choice(bias_directions)
        change_bias_step = random.randint(50, 200)
        step_counter = 0
        
        for _ in range(steps):
            neighbors = list(graph.neighbors(current_node))
            
            if current_node == target_node or current_node == northernmost_node:
                break
            
            if step_counter >= change_bias_step:
                bias_direction = random.choice(bias_directions)
                step_counter = 0
                change_bias_step = random.randint(50, 200)
            
            if random.random() < bias_probability:
                current_lat = graph.nodes[current_node]['y']
                current_lon = graph.nodes[current_node]['x']
                
                if bias_direction == 'south':
                    neighbors = [n for n in neighbors if graph.nodes[n]['y'] < current_lat]
                elif bias_direction == 'north':
                    neighbors = [n for n in neighbors if graph.nodes[n]['y'] > current_lat]
                elif bias_direction == 'east':
                    neighbors = [n for n in neighbors if graph.nodes[n]['x'] > current_lon]
                elif bias_direction == 'west':
                    neighbors = [n for n in neighbors if graph.nodes[n]['x'] < current_lon]
            
            if neighbors:
                current_node = random.choice(neighbors)
            
            walk.append(current_node)
            step_counter += 1
        
        return walk
    
    async def run_city_simulation(
        self,
        city: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run comprehensive simulation suite for a UK city.
        
        Args:
            city: City name
            config: Simulation configuration including:
                - num_scenarios: Number of scenarios to generate
                - num_routes: Number of A* routes
                - num_walks: Number of random walks
                - steps: Steps per walk
                - bias_probability: Bias probability for walks
                
        Returns:
            Simulation results dictionary
        """
        # Check if we need multiple different simulations
        num_scenarios = config.get('num_scenarios', 1)
        if num_scenarios > 1:
            return await self.run_multiple_scenarios(city, config)
        
        # Single simulation case
        city = self.city_resolver.sanitize_city_name(city)
        
        num_routes = config.get('num_routes', 10)
        num_walks = config.get('num_walks', 1000)
        steps_per_walk = config.get('steps', 1000)
        bias_probability = config.get('bias_probability', 0.4)
        
        logger.info(f"Running comprehensive simulation suite for {city}")
        
        try:
            # Load graph
            graph = self.graph_loader.load_graph(city)
            if graph is None:
                return {
                    "error": f"Failed to load street network for {city}",
                    "city": city,
                    "timestamp": datetime.now().isoformat()
                }
            
            nodes = list(graph.nodes())
            if len(nodes) < 2:
                return {"error": f"Insufficient network data for {city}"}
            
            # Calculate network centroid and key nodes
            node_positions = np.array([[graph.nodes[n]['y'], graph.nodes[n]['x']] for n in nodes])
            centroid = np.mean(node_positions, axis=0)
            center_node = ox.nearest_nodes(graph, X=centroid[1], Y=centroid[0])
            southernmost_node = min(nodes, key=lambda n: graph.nodes[n]['y'])
            boundary_nodes = random.sample(nodes, min(num_routes * 2, len(nodes)//10))
            
            # Generate A* routes
            astar_routes = []
            for i in range(min(num_routes, len(boundary_nodes))):
                try:
                    target_node = boundary_nodes[i]
                    route = nx.shortest_path(graph, center_node, target_node, weight='length')
                    route_coords = [[graph.nodes[node]['x'], graph.nodes[node]['y']] for node in route]
                    astar_routes.append({
                        'route_id': i,
                        'coordinates': route_coords,
                        'length': len(route),
                        'start_node': center_node,
                        'end_node': target_node
                    })
                except Exception as e:
                    logger.warning(f"Failed to generate A* route {i} for {city}: {e}")
                    continue
            
            # Generate random walks
            random_walk_paths = []
            for i in range(num_walks):
                path = self.biased_random_walk(
                    graph, center_node, southernmost_node,
                    steps=steps_per_walk,
                    bias_probability=bias_probability
                )
                random_walk_paths.append(path)
            
            # Calculate enhanced density for heatmap with 1000 walks
            final_points = [graph.nodes[path[-1]] for path in random_walk_paths if path and len(path) > 0 and path[-1] in graph.nodes]
            x_coords = [point['x'] for point in final_points]
            y_coords = [point['y'] for point in final_points]
            
            if len(x_coords) > 1:
                xy = np.vstack([x_coords, y_coords])
                # Use adaptive bandwidth for better density estimation with 1000 points
                kde = gaussian_kde(xy)
                kde.set_bandwidth(kde.factor * 0.5)  # Reduce bandwidth for finer detail
                density = kde(xy)
                
                # Normalize density for better visualization
                density_normalized = (density - density.min()) / (density.max() - density.min())
                
                idx = density.argsort()
                x_sorted = np.array(x_coords)[idx]
                y_sorted = np.array(y_coords)[idx]
                density_sorted = density_normalized[idx]
            else:
                x_sorted = np.array(x_coords)
                y_sorted = np.array(y_coords)
                density_sorted = np.ones(len(x_coords))
            
            # Create Folium map with controls hidden but zoom functionality enabled
            m = folium.Map(
                location=[centroid[0], centroid[1]],
                zoom_start=13,
                tiles='OpenStreetMap',
                zoom_control=False,  # Hide zoom buttons but keep zoom working
                scrollWheelZoom=True,  # Enable zoom via scroll wheel
                dragging=True,
                attributionControl=False  # Hide "Leaflet" attribution
            )
            
            # Add borough boundary
            self.visualization.add_borough_boundary(m, city)
            
            # Add center marker
            folium.Marker(
                [centroid[0], centroid[1]],
                popup=f"{city.title()} Evacuation Center",
                icon=folium.Icon(color='green', icon='info-sign')
            ).add_to(m)

            # LAYER ORDER MATTERS: Add in reverse z-order (bottom to top)
            # 1. First: Density heatmap (background)
            density_group = folium.FeatureGroup(name='Exit Density Heatmap')
            
            # Create proper heatmap using HeatMap plugin
            try:
                from folium.plugins import HeatMap
                
                # Prepare heatmap data: [lat, lng, intensity]
                heat_data = []
                for i in range(len(x_sorted)):
                    heat_data.append([y_sorted[i], x_sorted[i], density_sorted[i]])
                
                # Add heatmap layer
                HeatMap(
                    heat_data,
                    min_opacity=0.2,
                    max_zoom=18,
                    radius=15,
                    blur=10,
                    gradient={0.2: 'blue', 0.4: 'cyan', 0.6: 'lime', 0.8: 'yellow', 1.0: 'red'}
                ).add_to(density_group)
                
            except ImportError:
                # Fallback to enhanced circle markers if HeatMap not available
                logger.warning("HeatMap plugin not available, using enhanced circle markers")
                for i in range(len(x_sorted)):
                    # Use color gradient based on density
                    intensity = density_sorted[i]
                    if intensity > 0.8:
                        color, fillColor = 'red', 'red'
                    elif intensity > 0.6:
                        color, fillColor = 'orange', 'orange'
                    elif intensity > 0.4:
                        color, fillColor = 'yellow', 'yellow'
                    elif intensity > 0.2:
                        color, fillColor = 'lightgreen', 'lightgreen'
                    else:
                        color, fillColor = 'blue', 'blue'
                    
                    folium.CircleMarker(
                        location=[y_sorted[i], x_sorted[i]],
                        radius=max(3, int(10 * intensity)),  # Size based on density
                        color=color,
                        fill=True,
                        fillColor=fillColor,
                        fillOpacity=0.7,
                        popup=f"Density: {intensity:.3f}"
                    ).add_to(density_group)

            density_group.add_to(m)

            # 2. Middle: Random walks (stochastic paths)
            random_walk_group = folium.FeatureGroup(name='Biased Random Walks')
            for path in random_walk_paths:
                path_coords = [[graph.nodes[node]['y'], graph.nodes[node]['x']] for node in path]
                folium.PolyLine(
                    path_coords,
                    color='red',
                    weight=2,
                    opacity=0.3
                ).add_to(random_walk_group)
            random_walk_group.add_to(m)

            # 3. Top: A* routes (deterministic optimal paths) - added LAST so they appear ON TOP
            astar_group = folium.FeatureGroup(name='A* Optimal Routes')
            colors = ['blue', 'darkblue', 'purple', 'cadetblue']
            for i, route in enumerate(astar_routes):
                color = colors[i % len(colors)]
                coordinates = [[coord[1], coord[0]] for coord in route['coordinates']]
                folium.PolyLine(
                    coordinates,
                    color=color,
                    weight=5,  # Thicker lines to be more visible on top
                    opacity=0.9,  # Higher opacity for prominence
                    popup=f"A* Route {route['route_id']}"
                ).add_to(astar_group)
                if coordinates:
                    folium.Marker(
                        coordinates[-1],
                        popup=f"A* Exit {route['route_id']}",
                        icon=folium.Icon(color='blue', icon='ok-sign')
                    ).add_to(astar_group)
            astar_group.add_to(m)

            # LayerControl disabled for clean thumbnail display
            # folium.LayerControl().add_to(m)
            
            # Calculate metrics
            calculated_metrics = self.metrics_calculator.calculate_metrics(
                graph, astar_routes, random_walk_paths, city
            )
            
            # Calculate fairness and robustness
            fairness_index, robustness = await asyncio.gather(
                self.metrics_calculator.calculate_fairness_async(graph, astar_routes, random_walk_paths),
                self.metrics_calculator.calculate_robustness_async(graph, astar_routes)
            )
            
            calculated_metrics['fairness_index'] = round(fairness_index, 3)
            calculated_metrics['robustness'] = round(robustness, 3)
            
            logger.info(f"✅ REAL METRICS calculated for {city}",
                       fairness=fairness_index, robustness=robustness,
                       clearance=calculated_metrics.get('clearance_time_p50'))
            
            # Generate static plot
            try:
                static_plot_image = self.visualization.generate_static_plot(
                    graph, city, random_walk_paths=random_walk_paths, astar_routes=astar_routes
                )
            except Exception as e:
                logger.error(f"Failed to generate static plot for {city}: {e}")
                static_plot_image = None
            
            return {
                "city": city,
                "simulation_type": "comprehensive_suite",
                "astar_routes": astar_routes,
                "random_walks": {
                    "num_walks": len(random_walk_paths),
                    "avg_path_length": np.mean([len(p) for p in random_walk_paths]),
                    "density_data": {
                        "x": x_sorted.tolist(),
                        "y": y_sorted.tolist(),
                        "density": density_sorted.tolist()
                    }
                },
                "network_graph": {
                    "nodes": [{"id": str(node_id), "x": graph.nodes[node_id]['x'], "y": graph.nodes[node_id]['y']} for node_id in nodes],
                    "edges": [{"source": str(u), "target": str(v), "length": edge_data.get('length', 0)} for u, v, key, edge_data in graph.edges(keys=True, data=True)],
                    "bounds": {
                        "min_x": float(min(graph.nodes[n]['x'] for n in nodes)),
                        "max_x": float(max(graph.nodes[n]['x'] for n in nodes)),
                        "min_y": float(min(graph.nodes[n]['y'] for n in nodes)),
                        "max_y": float(max(graph.nodes[n]['y'] for n in nodes))
                    }
                },
                "interactive_map_html": self.visualization.generate_folium_html(m, city),
                "visualisation_image": static_plot_image,
                "scenarios": [],
                "calculated_metrics": calculated_metrics,
                "metrics": {
                    "num_astar_routes": len(astar_routes),
                    "num_random_walks": len(random_walk_paths),
                    "avg_random_walk_length": np.mean([len(p) for p in random_walk_paths]),
                    "total_network_nodes": len(nodes),
                    "network_coverage": f"{city.title()} metropolitan area",
                    "clearance_time_p50": calculated_metrics.get("clearance_time_p50", 0),
                    "clearance_time_p95": calculated_metrics.get("clearance_time_p95", 0),
                    "max_queue_length": calculated_metrics.get("max_queue_length", 0),
                    "evacuation_efficiency": calculated_metrics.get("evacuation_efficiency", 0)
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to simulate {city}: {e}")
            return {
                "error": f"Failed to load street network for {city}: {str(e)}",
                "city": city,
                "timestamp": datetime.now().isoformat()
            }
    
    async def run_multiple_scenarios(
        self,
        city: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run multiple DIFFERENT simulations with varied origins/exits.
        
        This method creates truly unique scenarios by varying:
        - Evacuation origins (different hazard locations)
        - Exit strategies (north, south, east, west, etc.)
        - Route patterns
        
        Args:
            city: City name
            config: Configuration with num_scenarios, custom_scenarios (optional)
            
        Returns:
            Results with multiple unique scenarios
        """
        city = self.city_resolver.sanitize_city_name(city)
        num_scenarios = config.get('num_scenarios', 10)

        logger.info(f"🔄 Running {num_scenarios} DIFFERENT simulations for {city} with varied evacuation patterns")

        # Load graph once
        graph = self.graph_loader.load_graph(city)
        if graph is None:
            return {"error": f"Failed to load street network for {city}"}

        nodes = list(graph.nodes())
        if len(nodes) < 10:
            return {"error": f"Insufficient network data for {city}"}

        node_positions = np.array([[graph.nodes[n]['y'], graph.nodes[n]['x']] for n in nodes])
        centroid = np.mean(node_positions, axis=0)

        # Define different evacuation scenarios
        evacuation_directions = ['north', 'south', 'east', 'west', 'northeast', 'northwest', 'southeast', 'southwest', 'center-out', 'perimeter']
        
        # Use custom scenarios if provided (from AI), otherwise use defaults
        if 'custom_scenarios' in config and config['custom_scenarios']:
            logger.info(f"🤖 Using {len(config['custom_scenarios'])} AI-generated custom scenarios")
            rich_scenarios = config['custom_scenarios']
        else:
            # Default rich scenarios
            rich_scenarios = [
                {'name': 'Thames fluvial flood – pan-London RWC', 'description': 'Mass evacuation scenario', 'hazard_type': 'flood', 'template_key': 'mass_fluvial_flood_rwc'},
                {'name': 'Central London chemical release', 'description': 'Large-scale chemical incident', 'hazard_type': 'chemical', 'template_key': 'large_chemical_release'},
                {'name': 'Central sudden impact – multi-site cordons', 'description': 'Terrorist incident', 'hazard_type': 'terrorist', 'template_key': 'terrorist_sudden_impact'},
                {'name': 'High-rise building fire evacuation', 'description': 'Major building fire', 'hazard_type': 'fire', 'template_key': 'fire_building'},
                {'name': 'Rising tide flood – Thames barrier failure', 'description': 'Tidal surge scenario', 'hazard_type': 'flood', 'template_key': 'rising_tide_flood'},
                {'name': 'Unexploded ordnance – planned evacuation', 'description': 'UXO disposal', 'hazard_type': 'uxo', 'template_key': 'medium_uxo_planned'},
                {'name': 'Gas leak – local area evacuation', 'description': 'Gas leak evacuation', 'hazard_type': 'gas', 'template_key': 'small_gas_leak'}
            ]

        all_scenarios = []
        aggregated_metrics = {
            'clearance_times': [],
            'fairness_indices': [],
            'robustness_scores': [],
            'total_nodes': len(nodes),
            'total_edges': len(graph.edges())
        }

        for scenario_idx in range(num_scenarios):
            # Select different origin point for each scenario
            if scenario_idx == 0:
                origin_node = ox.nearest_nodes(graph, X=centroid[1], Y=centroid[0])
            elif scenario_idx % 4 == 1:
                north_nodes = [n for n in nodes if graph.nodes[n]['y'] > centroid[0]]
                origin_node = random.choice(north_nodes) if north_nodes else nodes[scenario_idx % len(nodes)]
            elif scenario_idx % 4 == 2:
                south_nodes = [n for n in nodes if graph.nodes[n]['y'] < centroid[0]]
                origin_node = random.choice(south_nodes) if south_nodes else nodes[scenario_idx % len(nodes)]
            elif scenario_idx % 4 == 3:
                east_nodes = [n for n in nodes if graph.nodes[n]['x'] > centroid[1]]
                origin_node = random.choice(east_nodes) if east_nodes else nodes[scenario_idx % len(nodes)]
            else:
                west_nodes = [n for n in nodes if graph.nodes[n]['x'] < centroid[1]]
                origin_node = random.choice(west_nodes) if west_nodes else nodes[scenario_idx % len(nodes)]

            # Select exit strategy
            evacuation_dir = evacuation_directions[scenario_idx % len(evacuation_directions)]
            if evacuation_dir == 'north':
                target_node = max(nodes, key=lambda n: graph.nodes[n]['y'])
            elif evacuation_dir == 'south':
                target_node = min(nodes, key=lambda n: graph.nodes[n]['y'])
            elif evacuation_dir == 'east':
                target_node = max(nodes, key=lambda n: graph.nodes[n]['x'])
            elif evacuation_dir == 'west':
                target_node = min(nodes, key=lambda n: graph.nodes[n]['x'])
            else:
                target_node = random.choice(nodes)

            # Generate routes for this scenario
            boundary_nodes = random.sample(nodes, min(20, len(nodes)//10))
            num_routes = config.get('num_routes', 10)
            astar_routes = []
            for i in range(min(num_routes, len(boundary_nodes))):
                try:
                    exit_node = boundary_nodes[i]
                    route = nx.shortest_path(graph, origin_node, exit_node, weight='length')
                    route_coords = [[graph.nodes[node]['x'], graph.nodes[node]['y']] for node in route]
                    astar_routes.append({
                        'route_id': i,
                        'coordinates': route_coords,
                        'length': len(route),
                        'start_node': origin_node,
                        'end_node': exit_node
                    })
                except:
                    continue

            # Generate random walks for this scenario
            num_walks = config.get('num_walks', 1000)
            random_walk_paths = []
            for i in range(num_walks):
                path = self.biased_random_walk(graph, origin_node, target_node, steps=config.get('steps', 1000), bias_probability=config.get('bias_probability', 0.4))
                random_walk_paths.append(path)

            # Calculate REAL metrics for this scenario
            fairness_index, robustness = await asyncio.gather(
                self.metrics_calculator.calculate_fairness_async(graph, astar_routes, random_walk_paths),
                self.metrics_calculator.calculate_robustness_async(graph, astar_routes)
            )

            # Calculate clearance time
            clearance_time_p50 = 90.0
            if astar_routes:
                clearance_times_scenario = []
                for route in astar_routes:
                    route_length_m = sum([
                        ((route['coordinates'][j+1][0] - route['coordinates'][j][0])**2 +
                         (route['coordinates'][j+1][1] - route['coordinates'][j][1])**2)**0.5
                        for j in range(len(route['coordinates'])-1)
                    ]) * 111000
                    travel_time_min = route_length_m / (1.4 * 60)
                    clearance_times_scenario.append(travel_time_min)
                clearance_time_p50 = np.median(clearance_times_scenario) if clearance_times_scenario else 90.0

            aggregated_metrics['clearance_times'].append(clearance_time_p50)
            aggregated_metrics['fairness_indices'].append(fairness_index)
            aggregated_metrics['robustness_scores'].append(robustness)

            # Create map for this scenario with controls hidden but zoom functionality enabled
            scenario_map = folium.Map(
                location=[centroid[0], centroid[1]], 
                zoom_start=13, 
                tiles='OpenStreetMap',
                zoom_control=False,  # Hide zoom buttons but keep zoom working
                scrollWheelZoom=True,  # Enable zoom via scroll wheel
                dragging=True,
                attributionControl=False  # Hide "Leaflet" attribution
            )
            self.visualization.add_borough_boundary(scenario_map, city)
            
            folium.Marker([centroid[0], centroid[1]], popup=f"{city.title()} - Scenario {scenario_idx+1}", icon=folium.Icon(color='green', icon='info-sign')).add_to(scenario_map)
            
            # Add A* routes
            astar_group = folium.FeatureGroup(name='A* Optimal Routes')
            colors = ['blue', 'darkblue', 'purple', 'cadetblue']
            for i, route in enumerate(astar_routes):
                color = colors[i % len(colors)]
                coords = [[c[1], c[0]] for c in route['coordinates']]
                folium.PolyLine(
                    coords,
                    color=color,
                    weight=4,
                    opacity=0.7,
                    popup=f"A* Route {route['route_id']}"
                ).add_to(astar_group)
                if coords:
                    folium.Marker(
                        coords[-1],
                        popup=f"A* Exit {route['route_id']}",
                        icon=folium.Icon(color='blue', icon='ok-sign')
                    ).add_to(astar_group)
            astar_group.add_to(scenario_map)
            
            # Add random walks
            random_walk_group = folium.FeatureGroup(name='Biased Random Walks')
            for path in random_walk_paths:
                path_coords = [[graph.nodes[node]['y'], graph.nodes[node]['x']] for node in path if node in graph.nodes]
                if path_coords:
                    folium.PolyLine(
                        path_coords,
                        color='red',
                        weight=2,
                        opacity=0.3
                    ).add_to(random_walk_group)
            random_walk_group.add_to(scenario_map)
            
            # Add density heatmap
            density_group = folium.FeatureGroup(name='Exit Density Heatmap')
            if random_walk_paths:
                final_points = [graph.nodes[path[-1]] for path in random_walk_paths if path and len(path) > 0 and path[-1] in graph.nodes]
                if final_points:
                    for i, point in enumerate(final_points[:10]):  # Limit to 10 points for performance
                        folium.CircleMarker(
                            location=[point['y'], point['x']],
                            radius=6,
                            color='orange',
                            fill=True,
                            fillColor='red',
                            fillOpacity=0.6,
                            popup=f"Exit Point {i+1}"
                        ).add_to(density_group)
            density_group.add_to(scenario_map)
            
            # LayerControl disabled for clean thumbnail display
            # folium.LayerControl().add_to(scenario_map)
            scenario_map_html = self.visualization.generate_folium_html(scenario_map, f"{city}_scenario_{scenario_idx+1}")

            # Create scenario
            rich_scenario = rich_scenarios[scenario_idx % len(rich_scenarios)]
            scenario = {
                'id': f'{city}_scenario_{scenario_idx+1}',
                'scenario_name': f'{rich_scenario["name"]} ({evacuation_dir} evacuation)',
                'name': rich_scenario['name'],
                'description': rich_scenario['description'],
                'hazard_type': rich_scenario['hazard_type'],
                'template_key': rich_scenario['template_key'],
                'evacuation_direction': evacuation_dir,
                'expected_clearance_time': round(clearance_time_p50, 1),
                'fairness_index': round(fairness_index, 3),
                'robustness': round(robustness, 3),
                'compliance_rate': 0.7 + (scenario_idx * 0.02),
                'transport_disruption': 0.3 + (scenario_idx * 0.05),
                'population_affected': int(50000 + (scenario_idx * 5000)),
                'routes_calculated': len(astar_routes),
                'walks_simulated': len(random_walk_paths),
                'simulation_data': {
                    'interactive_map_html': scenario_map_html or "",
                    'astar_routes': astar_routes,
                    'random_walks': {'num_walks': len(random_walk_paths), 'paths': random_walk_paths[:5]}
                }
            }
            all_scenarios.append(scenario)
            logger.info(f"✅ Scenario {scenario_idx+1}/{num_scenarios}: {rich_scenario['name']}, clearance={clearance_time_p50:.1f}min")

        # Calculate aggregate metrics
        calculated_metrics = {
            'clearance_time_p50': round(np.median(aggregated_metrics['clearance_times']), 1),
            'clearance_time_min': round(np.min(aggregated_metrics['clearance_times']), 1),
            'clearance_time_max': round(np.max(aggregated_metrics['clearance_times']), 1),
            'fairness_index': round(np.mean(aggregated_metrics['fairness_indices']), 3),
            'robustness': round(np.mean(aggregated_metrics['robustness_scores']), 3),
            'total_nodes': aggregated_metrics['total_nodes'],
            'total_edges': aggregated_metrics['total_edges']
        }

        logger.info(f"🎯 Generated {len(all_scenarios)} UNIQUE scenarios")

        return {
            'city': city,
            'scenarios': all_scenarios,
            'calculated_metrics': calculated_metrics,
            'timestamp': datetime.now().isoformat(),
            'simulation_type': 'multi_varied_simulations',
            'status': 'completed'
        }
