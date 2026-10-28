import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# Ollama Settings
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral:7b")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "10.0"))

# Agent Settings
MAX_AGENT_ITERATIONS = int(os.getenv("MAX_AGENT_ITERATIONS", "6"))
AGENT_TEMPERATURE = float(os.getenv("AGENT_TEMPERATURE", "0.1"))

# Database Settings
DATA_DIR = BASE_DIR / "database"
PG_DATA_FILE = DATA_DIR / "pg_data.json"

# Prompts Directory
PROMPTS_DIR = BASE_DIR / "prompts"
AGENT_PROMPT_FILE = PROMPTS_DIR / "agent_prompt.txt"
REFLECTION_PROMPT_FILE = PROMPTS_DIR / "reflection_prompt.txt"

# Default Demo Coordinates (e.g. Navrangpura / LD College of Engineering / Ahmedabad center)
DEFAULT_CITY = "Ahmedabad"
DEFAULT_LATITUDE = 23.0338
DEFAULT_LONGITUDE = 72.5463
