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
    clerk_jwks_url: Optional[str] = "https://secure-tomcat-84.clerk.accounts.dev/.well-known/jwks.json"
    
    # External Services
    openai_api_key: str
    
    # LangSmith observability (optional, used automatically by LangChain)
    langsmith_api_key: Optional[str] = None
    langsmith_tracing: Optional[str] = None
    langsmith_endpoint: Optional[str] = None
    langsmith_project: Optional[str] = None
    
    # Firecrawl
    firecrawl_api_key: Optional[str] = None

    # CORS
    allowed_origins: List[str] = [
        "http://localhost:3000", 
        "http://localhost:3001",
        "https://opennotenetwork.com",
        "https://www.opennotenetwork.com",
        "https://opennotenetwork.vercel.app",  # Stable Vercel URL
    ]
    allowed_hosts: List[str] = [
        "localhost", 
        "127.0.0.1",
        "opennotenetwork-api.fly.dev",
        # "api.opennotenetwork.com",  # Add this when you set up the domain
    ]
    
    class Config:
        env_file = ".env.local"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields in env file


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