from pydantic_settings import BaseSettings
from typing import List


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
    
    # External Services - LangGraph runs locally as Python functions
    # No external URL needed
    
    # Scheduling secrets
    ingest_secret: str
    reconcile_secret: str
    
    # CORS
    allowed_origins: List[str] = ["http://localhost:3000", "http://localhost:3001"]
    allowed_hosts: List[str] = ["localhost", "127.0.0.1"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Create global settings instance
settings = Settings()