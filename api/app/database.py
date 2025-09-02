from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
import structlog

from app.config import settings
from app.models import Base

logger = structlog.get_logger()

# Create async engine with URL cleanup for asyncpg
def clean_database_url(url: str) -> str:
    """Clean database URL for asyncpg compatibility"""
    # Convert to asyncpg format
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://")
    
    # Remove sslmode parameter as asyncpg handles SSL differently
    if "?sslmode=" in url:
        url = url.split("?sslmode=")[0]
    elif "&sslmode=" in url:
        # Remove sslmode from query string
        import re
        url = re.sub(r'[&?]sslmode=[^&]*', '', url)
    
    return url

engine = create_async_engine(
    clean_database_url(settings.database_url),
    echo=False,  # Disable SQLAlchemy query logging
    pool_pre_ping=True,
    pool_recycle=300,
)

# Create session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session():
    """Get database session"""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database tables"""
    try:
        async with engine.begin() as conn:
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise

# Utility functions for post_uid handling
def build_post_uid(platform: str, platform_post_id: str) -> str:
    """Build post_uid from platform and platform_post_id"""
    return f"{platform.lower()}--{platform_post_id}"


def parse_post_uid(post_uid: str) -> tuple[str, str]:
    """Parse post_uid into platform and platform_post_id"""
    parts = post_uid.split("--", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid post_uid format: {post_uid}")
    return parts[0], parts[1]