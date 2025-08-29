from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import structlog
from contextlib import asynccontextmanager

from app.database import init_db
from app.routers import public, admin
from app.config import settings


logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting up OpenNoteNetwork API")
    
    # Initialize database
    await init_db()
    
    yield
    
    logger.info("Shutting down OpenNoteNetwork API")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    
    app = FastAPI(
        title="OpenNoteNetwork API",
        description="Open-source AI-powered fact-checking system for Community Notes",
        version="1.0.0",
        lifespan=lifespan,
        openapi_url="/api/openapi.json" if not settings.production else None,
        docs_url="/api/docs" if not settings.production else None,
        redoc_url="/api/redoc" if not settings.production else None,
    )

    # Add middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*"],
    )
    
    if settings.production:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.allowed_hosts
        )

    # Include routers
    app.include_router(public.router, prefix="/api/public", tags=["public"])
    app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
    
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "version": "1.0.0"}
    
    @app.get("/api/health")
    async def api_health_check():
        return {"status": "healthy", "version": "1.0.0"}

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if not settings.production else False
    )