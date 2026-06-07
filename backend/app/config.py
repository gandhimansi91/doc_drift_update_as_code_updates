import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    USE_MOCKS = os.getenv("USE_MOCKS", "True").lower() == "true"
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))
    
    LLM_API_KEY = os.getenv("LLM_API_KEY")
    LLM_API_BASE = os.getenv("LLM_API_BASE", "https://api.openai.com/v1")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    MOCK_LLM_DELAY = float(os.getenv("MOCK_LLM_DELAY", "0.4"))
    
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    GITHUB_API_BASE = os.getenv("GITHUB_API_BASE", "https://api.github.com")
    WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
    MOCK_GITHUB_REPO = os.getenv("MOCK_GITHUB_REPO", "acme/sample-app")

settings = Settings()