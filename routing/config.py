import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env from the same directory as this config file
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

DOUBLEGIS_API_KEY = os.getenv("DOUBLEGIS_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

print(f"DEBUG config.py: DOUBLEGIS_API_KEY loaded = {DOUBLEGIS_API_KEY is not None}")
print(f"DEBUG config.py: GEMINI_API_KEY loaded = {GEMINI_API_KEY is not None}")

# 2GIS API endpoints
DOUBLEGIS_BASE_URL = "https://catalog.api.2gis.com/3.0"
DOUBLEGIS_ROUTING_URL = "https://routing.api.2gis.com"
