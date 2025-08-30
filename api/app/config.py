from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    """Application settings"""
    
    # Environment
    environment: str = "development"
    production: bool = False
    
    # Database
    database_url: str
    
    # X.com API
    x_api_key: str
    x_api_key_secret: str
    x_access_token: str
    x_access_token_secret: str
    
    # Clerk Auth
    clerk_publishable_key: str
    clerk_secret_key: str
    
    # External Services
    openai_api_key: str
    
    # LangSmith observability (optional, used automatically by LangChain)
    langsmith_api_key: Optional[str] = None
    langsmith_tracing: Optional[str] = None
    langsmith_endpoint: Optional[str] = None
    langsmith_project: Optional[str] = None
    
    # Scheduling secrets
    ingest_secret: str
    reconcile_secret: str
    
    # CORS
    allowed_origins: List[str] = ["http://localhost:3000", "http://localhost:3001"]
    allowed_hosts: List[str] = ["localhost", "127.0.0.1"]
    
    class Config:
        env_file = ".env.local"
        case_sensitive = False


# Create global settings instance
settings = Settings()

# Set LangSmith environment variables for LangChain to use
import os
if settings.langsmith_api_key:
    os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
if settings.langsmith_tracing:
    os.environ["LANGSMITH_TRACING"] = settings.langsmith_tracing
if settings.langsmith_endpoint:
    os.environ["LANGSMITH_ENDPOINT"] = settings.langsmith_endpoint
if settings.langsmith_project:
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project