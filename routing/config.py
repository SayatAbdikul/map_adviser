import os
from dotenv import load_dotenv

load_dotenv()

DOUBLEGIS_API_KEY = os.getenv("DOUBLEGIS_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# 2GIS API endpoints
DOUBLEGIS_BASE_URL = "https://catalog.api.2gis.com/3.0"
DOUBLEGIS_ROUTING_URL = "https://routing.api.2gis.com"
