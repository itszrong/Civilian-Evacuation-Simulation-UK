"""
City Resolver Service
Handles city name resolution, geocoding query generation, and UK location validation.
Extracted from multi_city_orchestrator.py to improve code organization.
"""

from typing import List, Dict, Optional
import structlog
import osmnx as ox

logger = structlog.get_logger(__name__)


# London boroughs (32 boroughs + City of London)
LONDON_BOROUGHS = [
    "city of london",
    "westminster",
    "kensington and chelsea",
    "hammersmith and fulham",
    "wandsworth",
    "lambeth",
    "southwark",
    "tower hamlets",
    "hackney",
    "islington",
    "camden",
    "brent",
    "ealing",
    "hounslow",
    "richmond upon thames",
    "kingston upon thames",
    "merton",
    "sutton",
    "croydon",
    "bromley",
    "lewisham",
    "greenwich",
    "bexley",
    "havering",
    "redbridge",
    "newham",
    "waltham forest",
    "haringey",
    "enfield",
    "barnet",
    "harrow",
    "hillingdon",
    "barking and dagenham",
]

# Known bounding boxes for problematic cities
CITY_BOUNDING_BOXES = {
    'islington': {'north': 51.5741, 'south': 51.5186, 'east': -0.0759, 'west': -0.1441},
    'city of london': {'north': 51.5225, 'south': 51.5065, 'east': -0.0759, 'west': -0.1180},
    'westminster': {'north': 51.5355, 'south': 51.4875, 'east': -0.1078, 'west': -0.1766},
    'camden': {'north': 51.5741, 'south': 51.5186, 'east': -0.1078, 'west': -0.1766}
}


class CityResolverService:
    """Service for resolving city names and generating OSMnx query variations."""
    
    def __init__(self):
        """Initialize the city resolver service."""
        self.london_boroughs = LONDON_BOROUGHS.copy()
        self.city_bounding_boxes = CITY_BOUNDING_BOXES.copy()
    
    def sanitize_city_name(self, city: str) -> str:
        """
        Clean up city name by removing common suffixes like ', UK', ', England', etc.
        
        Args:
            city: Raw city name string
            
        Returns:
            Sanitized city name
        """
        city_lower = city.lower().strip()

        # Remove common suffixes
        suffixes_to_remove = [', uk', ', england', ', scotland', ', wales', ', northern ireland']
        for suffix in suffixes_to_remove:
            if city_lower.endswith(suffix):
                city_lower = city_lower[:-len(suffix)].strip()
                break

        return city_lower
    
    def get_query_variations(self, city: str) -> List[str]:
        """
        Get various query strings to try for a city for OSMnx geocoding.
        
        Args:
            city: City name (should be pre-sanitized)
            
        Returns:
            List of query variations to try, ordered by likelihood of success
        """
        city_lower = city.lower()
        city_title = city.title()
        
        # Special cases for known problematic cities
        if city_lower == 'islington':
            return [
                "London Borough of Islington, London, England",
                "Islington, London, England", 
                "Islington, Greater London, England",
                "Islington Borough, London, UK",
                "Islington, London, UK",
                city_title
            ]
        elif city_lower == 'city of london':
            return [
                "City of London, London, England",
                "City of London, Greater London, England",
                "City of London, UK",
                city_title
            ]
        elif city_lower in ['cardiff']:
            return [
                f"{city_title}, Wales",
                f"{city_title}, Cardiff, Wales",
                city_title
            ]
        elif city_lower in ['belfast']:
            return [
                f"{city_title}, Northern Ireland",
                f"{city_title}, Belfast, Northern Ireland",
                city_title
            ]
        elif city_lower in ['edinburgh', 'glasgow']:
            return [
                f"{city_title}, Scotland",
                f"{city_title}, Edinburgh, Scotland" if city_lower == 'edinburgh' else f"{city_title}, Glasgow, Scotland",
                city_title
            ]
        elif city_lower in self.london_boroughs:
            # London borough variations
            return [
                f"London Borough of {city_title}, London, England",
                f"{city_title}, London, England",
                f"{city_title}, Greater London, England", 
                f"{city_title}, UK",
                city_title
            ]
        else:
            # General UK city variations (non-London)
            return [
                f"{city_title}, England",
                f"{city_title}, UK",
                city_title
            ]
    
    def load_by_bounding_box(self, city: str):
        """
        Load city using bounding box coordinates as final fallback.
        
        Args:
            city: City name
            
        Returns:
            OSMnx graph or None if city not in bounding box database
            
        Raises:
            Exception: If no bounding box available for city
        """
        city_lower = city.lower()
        
        if city_lower in self.city_bounding_boxes:
            bounds = self.city_bounding_boxes[city_lower]
            logger.info(f"Using bounding box for {city}", bounds=bounds)
            
            return ox.graph_from_bbox(
                north=bounds['north'], 
                south=bounds['south'], 
                east=bounds['east'], 
                west=bounds['west'],
                network_type='walk'
            )
        else:
            raise Exception(f"No bounding box available for {city}")
    
    def is_uk_location(self, location: str) -> bool:
        """
        Check if a location can be resolved in the UK via OSMnx.
        
        Args:
            location: Location name to check
            
        Returns:
            True (we'll try to resolve any location via OSMnx)
        
        Note:
            This method returns True for any location, allowing the system
            to attempt resolving any UK location via OSMnx's geocoding.
            The actual validation happens during graph loading.
        """
        return True
    
    def get_supported_cities(self) -> List[str]:
        """
        Get list of London boroughs (default supported cities).
        
        Returns:
            List of London borough names
        """
        return self.london_boroughs.copy()
    
    def get_uk_cities(self) -> List[str]:
        """
        Get list of London boroughs (backward compatibility).
        
        Returns:
            List of London borough names
        """
        return self.london_boroughs.copy()
    
    def is_london_borough(self, city: str) -> bool:
        """
        Check if a city is a London borough.
        
        Args:
            city: City name to check
            
        Returns:
            True if city is in London boroughs list
        """
        return city.lower() in self.london_boroughs
    
    def get_place_mapping(self, city: str) -> Optional[str]:
        """
        Get OSMnx place query mapping for specific boroughs.
        
        Args:
            city: City name
            
        Returns:
            OSMnx place query string or None if no specific mapping
        """
        place_mapping = {
            "london": "City of Westminster, London, England",
            "westminster": "City of Westminster, London, England",
            "city of london": "City of London, London, England", 
            "kensington and chelsea": "Royal Borough of Kensington and Chelsea, London, England",
            "hammersmith and fulham": "Hammersmith and Fulham, London, UK",
            "wandsworth": "Wandsworth, London, UK",
            "lambeth": "Lambeth, London, UK",
            "southwark": "Southwark, London, UK",
            "tower hamlets": "Tower Hamlets, London, UK",
            "hackney": "Hackney, London, UK",
            "islington": "Islington, London, UK",
            "camden": "Camden, London, UK",
            "brent": "Brent, London, UK",
            "ealing": "Ealing, London, UK",
            "hounslow": "Hounslow, London, UK",
            "richmond upon thames": "Richmond upon Thames, London, UK",
            "kingston upon thames": "Kingston upon Thames, London, UK",
            "merton": "Merton, London, UK",
            "sutton": "Sutton, London, UK",
            "croydon": "Croydon, London, UK",
            "bromley": "Bromley, London, UK",
            "lewisham": "Lewisham, London, UK",
            "greenwich": "Greenwich, London, UK"
        }
        
        return place_mapping.get(city.lower())
