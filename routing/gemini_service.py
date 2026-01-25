from google import genai
from typing import List
from config import GEMINI_API_KEY
from models import Place


class GeminiService:
    """Service for interacting with Google's Gemini AI"""
    
    def __init__(self):
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.model_name = 'gemini-2.0-flash'
    
    async def parse_user_request(self, description: str, city: str) -> List[str]:
        """
        Parse user's textual description and convert it to search queries for 2GIS
        
        Args:
            description: User's description of what they want to visit
            city: City context for the search
            
        Returns:
            List of search queries to use with 2GIS API
        """
        prompt = f"""
You are a travel assistant. A user wants to visit places in {city} and provided this description:
"{description}"

Extract and return a list of specific place types or categories that should be searched in 2GIS API.
Return ONLY a comma-separated list of search terms, nothing else.
Examples: "italian restaurants", "art museums", "parks"

Search terms:"""
        
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt
        )
        
        # Parse the response - expecting comma-separated values
        search_queries = [q.strip() for q in response.text.strip().split(',')]
        return search_queries
    
    async def select_best_places(self, description: str, all_places: List[Place], max_places: int = 5) -> tuple[List[Place], str]:
        """
        Analyze places returned by 2GIS and select the best ones based on user's description
        
        Args:
            description: Original user description
            all_places: All places found by 2GIS
            max_places: Maximum number of places to select
            
        Returns:
            Tuple of (selected places, explanation)
        """
        # Create a formatted list of places for Gemini
        places_text = "\n".join([
            f"{i+1}. {place.name} - {place.address} (ID: {place.id})"
            for i, place in enumerate(all_places)
        ])
        
        prompt = f"""
You are a travel route planner. A user wants: "{description}"

Here are the available places:
{places_text}

Task:
1. Select the top {max_places} places that best match the user's request
2. Order them in a logical visiting sequence
3. Provide a brief explanation of why you chose these places and this order

Response format:
SELECTED_IDS: id1,id2,id3,...
EXPLANATION: Your explanation here
"""
        
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt
        )
        response_text = response.text.strip()
        
        # Parse the response
        selected_ids = []
        explanation = ""
        
        for line in response_text.split('\n'):
            if line.startswith('SELECTED_IDS:'):
                ids_text = line.replace('SELECTED_IDS:', '').strip()
                selected_ids = [id.strip() for id in ids_text.split(',')]
            elif line.startswith('EXPLANATION:'):
                explanation = line.replace('EXPLANATION:', '').strip()
        
        # If parsing failed, use alternative parsing
        if not selected_ids:
            # Try to extract IDs from the response
            lines = response_text.split('\n')
            if lines:
                first_line = lines[0]
                # Assume first line contains IDs
                selected_ids = [id.strip() for id in first_line.replace('SELECTED_IDS:', '').split(',')]
                explanation = ' '.join(lines[1:])
        
        # Match IDs to places
        selected_places = []
        for place_id in selected_ids:
            for place in all_places:
                if place.id == place_id:
                    selected_places.append(place)
                    break
        
        # If no places matched, return top N places with default explanation
        if not selected_places and all_places:
            selected_places = all_places[:max_places]
            explanation = f"Selected {len(selected_places)} places based on your request."
        
        return selected_places, explanation
    
    async def generate_route_description(self, description: str, places: List[Place], route_info: dict) -> str:
        """
        Generate a natural language description of the created route
        
        Args:
            description: Original user request
            places: Selected places in route order
            route_info: Route information from 2GIS
            
        Returns:
            Natural language route description
        """
        places_list = "\n".join([
            f"{i+1}. {place.name} - {place.address}"
            for i, place in enumerate(places)
        ])
        
        distance_km = route_info.get('total_distance', 0) / 1000
        duration_min = route_info.get('total_duration', 0) / 60
        
        prompt = f"""
Create a friendly route description for a user who wanted: "{description}"

Route details:
{places_list}

Total distance: {distance_km:.1f} km
Estimated time: {duration_min:.0f} minutes

Write a brief, enthusiastic description (2-3 sentences) of this route."""
        
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt
        )
        return response.text.strip()
