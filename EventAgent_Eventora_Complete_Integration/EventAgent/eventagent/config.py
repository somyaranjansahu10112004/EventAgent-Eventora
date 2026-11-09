"""Environment-backed configuration. Never commit real API keys."""
import os
from dotenv import load_dotenv

load_dotenv()

SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "models/gemini-flash-lite-latest")

def require_api_key(value: str, name: str) -> str:
    if not value:
        raise RuntimeError(f"{name} is missing. Add it to your .env file; see .env.example.")
    return value
