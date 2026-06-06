"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Feature flags
    USE_MOCKS: bool = True  # Set False to wire real integrations

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Qdrant (local, no key required)
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_IN_MEMORY: bool = True  # Use in-memory mode for local dev

    # Sample repo path — resolved relative to backend/app/core/config.py → ../../../sample_repo
    SAMPLE_REPO_PATH: str = os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "sample_repo")
    )

    # Mock LLM response delay (seconds)
    MOCK_LLM_DELAY: float = 0.4

    # Real LLM integration (optional)
    # Use any provider key and base URL compatible with the request schema.
    LLM_API_KEY: Optional[str] = None
    LLM_API_BASE: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-3.5-turbo"

    # Real GitHub integration (optional)
    GITHUB_TOKEN: Optional[str] = None
    GITHUB_API_BASE: str = "https://api.github.com"

    # GitHub mock
    MOCK_GITHUB_REPO: str = "acme/sample-app"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
