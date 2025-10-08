"""
Map Visualization Service
Handles Folium map generation, matplotlib plots, and visualization rendering.
Extracted from multi_city_orchestrator.py to improve code organization.
"""

from typing import List, Optional
import base64
from io import BytesIO
import structlog
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for server
import matplotlib.pyplot as plt
import folium
import osmnx as ox
import geopandas as gpd
import networkx as nx

from services.geography.city_resolver_service import CityResolverService

logger = structlog.get_logger(__name__)


class MapVisualizationService:
    """Service for generating map visualizations and plots."""
    
    def __init__(self, city_resolver: Optional[CityResolverService] = None):
        """
        Initialize the visualization service.
        
        Args:
            city_resolver: City resolver for place mappings
        """
        self.city_resolver = city_resolver or CityResolverService()
    
    def generate_folium_html(self, folium_map: folium.Map, city: str) -> Optional[str]:
        """
        Safely generate Folium map HTML with proper error handling.
        
        Args:
            folium_map: Folium map object
            city: City name for logging
            
        Returns:
            HTML string or None if generation fails
        """
        try:
            html_content = folium_map._repr_html_()
            if not html_content or html_content.strip() == "":
                logger.warning(f"Folium map HTML is empty for {city}")
                return None
            
            return html_content
            
        except Exception as e:
            logger.error(f"Failed to generate Folium map HTML for {city}: {e}")
            return None
    
    def generate_static_plot(
        self,
        graph: nx.MultiDiGraph,
        city_name: str,
        random_walk_paths: Optional[List] = None,
        astar_routes: Optional[List] = None
    ) -> Optional[str]:
        """
        Generate static matplotlib plot of city street network with evacuation paths.
        
        Args:
            graph: NetworkX graph of street network
            city_name: City name for title
            random_walk_paths: List of random walk paths (node lists)
            astar_routes: List of A* route dictionaries with 'coordinates'
            
        Returns:
            Base64-encoded image string or None if generation fails
        """
        try:
            # Convert graph to GeoDataFrames
            nodes_gdf, streets_gdf = ox.graph_to_gdfs(graph)

            fig, ax = plt.subplots(figsize=(12, 12))

            # Plot street network
            streets_gdf.plot(ax=ax, linewidth=0.1, color="black")

            # Plot A* routes
            if astar_routes:
                for route in astar_routes:
                    if 'coordinates' in route and route['coordinates']:
                        route_x = [coord[0] for coord in route['coordinates']]
                        route_y = [coord[1] for coord in route['coordinates']]
                        ax.plot(route_x, route_y, color='blue', linewidth=1.0, alpha=0.5, zorder=2)

            # Plot random walk paths
            if random_walk_paths:
                for path in random_walk_paths:
                    if path and len(path) > 0:
                        try:
                            path_x = [graph.nodes[node]['x'] for node in path if node in graph.nodes]
                            path_y = [graph.nodes[node]['y'] for node in path if node in graph.nodes]
                            if path_x and path_y:
                                ax.plot(path_x, path_y, color='red', linewidth=0.5, alpha=0.3, zorder=2)
                        except KeyError:
                            continue

                # Plot exit points
                final_points = []
                for path in random_walk_paths:
                    if path and len(path) > 0 and path[-1] in graph.nodes:
                        final_points.append(graph.nodes[path[-1]])
                
                if final_points:
                    exit_x = [point['x'] for point in final_points]
                    exit_y = [point['y'] for point in final_points]
                    ax.scatter(exit_x, exit_y, color="red", s=20, zorder=3, alpha=0.6, label='Exit Points')

            # Set plot properties
            ax.set_title(f"{city_name.title()} Evacuation Simulation", fontsize=16, fontweight='bold')
            ax.set_xlabel("Longitude")
            ax.set_ylabel("Latitude")
            ax.axis('equal')
            ax.grid(True, alpha=0.3)

            # Add legend
            legend_elements = []
            if astar_routes:
                legend_elements.append(plt.Line2D([0], [0], color='blue', linewidth=2, label='A* Routes'))
            if random_walk_paths:
                legend_elements.append(plt.Line2D([0], [0], color='red', linewidth=2, label='Random Walks'))
                legend_elements.append(plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='red', markersize=8, label='Exit Points'))
            if legend_elements:
                ax.legend(handles=legend_elements)

            # Save to base64
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            plt.close(fig)

            return f"data:image/png;base64,{image_base64}"

        except Exception as e:
            logger.error(f"Failed to generate street network plot for {city_name}: {e}")
            # Clean up matplotlib resources
            try:
                plt.close('all')
            except:
                pass
            return None
    
    def add_borough_boundary(self, folium_map: folium.Map, city: str):
        """
        Add borough boundary to Folium map.
        
        Args:
            folium_map: Folium map object to add boundary to
            city: City/borough name
        """
        try:
            # Get place query for this borough
            place_query = self.city_resolver.get_place_mapping(city)
            
            if place_query is None:
                # Fallback to generic query
                place_query = f"{city.title()}, London, UK"
            
            # Get the boundary geometry from OSMnx
            boundary_gdf = ox.geocode_to_gdf(place_query)
            
            # Add boundary to map
            boundary_group = folium.FeatureGroup(name=f'{city.title()} Borough Boundary')
            
            # Convert geometry to GeoJSON and add to map
            folium.GeoJson(
                boundary_gdf.to_json(),
                style_function=lambda x: {
                    'fillColor': 'lightblue',
                    'color': 'darkblue',
                    'weight': 3,
                    'fillOpacity': 0.1,
                    'opacity': 0.8
                },
                popup=folium.Popup(f"{city.title()} Borough Boundary", parse_html=True),
                tooltip=f"{city.title()} Borough"
            ).add_to(boundary_group)
            
            boundary_group.add_to(folium_map)
            logger.info(f"Added borough boundary for {city}")

        except Exception as e:
            logger.warning(f"Could not add borough boundary for {city}: {e}")
