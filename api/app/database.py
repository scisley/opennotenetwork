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
        
        # Only insert default data in development/testing
        # Skip in production (use Neon tools or migrations instead)
        if settings.environment in ["development", "testing"]:
            await insert_default_data()
        
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise


async def insert_default_data():
    """Insert default platforms, topics, and classifiers"""
    async with async_session_factory() as session:
        try:
            from app.models import Platform, Topic, Classifier
            
            # Check if platforms exist
            result = await session.execute(
                text("SELECT COUNT(*) FROM platforms WHERE platform_id = 'x'")
            )
            if result.scalar() == 0:
                # Insert default platform
                x_platform = Platform(
                    platform_id="x",
                    display_name="X (Twitter)",
                    config={
                        "max_note_length": 280,
                        "requires_link": True
                    },
                    status="active"
                )
                session.add(x_platform)
            
            # Check if topics exist (keep for backward compatibility)
            result = await session.execute(
                text("SELECT COUNT(*) FROM topics WHERE slug = 'climate'")
            )
            if result.scalar() == 0:
                # Insert default topic
                climate_topic = Topic(
                    slug="climate",
                    display_name="Climate Change",
                    config={
                        "description": "Posts related to climate change, global warming, and environmental issues"
                    },
                    status="active"
                )
                session.add(climate_topic)
            
            # Check if classifiers exist
            result = await session.execute(
                text("SELECT COUNT(*) FROM classifiers WHERE slug = 'climate-misinformation-v1'")
            )
            if result.scalar() == 0:
                # Insert sample classifiers
                
                # Single-choice climate classifier
                climate_classifier = Classifier(
                    slug="climate-misinformation-v1",
                    display_name="Climate Misinformation Detector",
                    description="Identifies posts containing climate change misinformation",
                    group_name="climate-classifiers",
                    is_active=True,
                    output_schema={
                        "type": "single",
                        "name": "Climate Misinformation Detector",
                        "description": "Identifies if post contains climate misinformation",
                        "choices": [
                            {
                                "value": "climate_misinformation",
                                "label": "Climate Misinformation",
                                "color": "#FF4444"
                            },
                            {
                                "value": "climate_accurate",
                                "label": "Climate Accurate",
                                "color": "#44FF44"
                            },
                            {
                                "value": "climate_neutral",
                                "label": "Climate Neutral",
                                "color": "#888888"
                            },
                            {
                                "value": "not_climate_related",
                                "label": "Not Climate Related",
                                "color": "#CCCCCC"
                            }
                        ],
                        "supports_confidence": True
                    },
                    config={}
                )
                session.add(climate_classifier)
                
                # Multi-choice topic tagger
                topic_tagger = Classifier(
                    slug="topic-tagger-v1",
                    display_name="Topic Tagger",
                    description="Tags posts with multiple relevant topics",
                    group_name="general-classifiers",
                    is_active=True,
                    output_schema={
                        "type": "multi",
                        "name": "Topic Tagger",
                        "description": "Tags posts with relevant topics",
                        "max_selections": 5,
                        "choices": [
                            {
                                "value": "climate",
                                "label": "Climate",
                                "icon": "🌍"
                            },
                            {
                                "value": "scientific",
                                "label": "Scientific",
                                "icon": "🔬"
                            },
                            {
                                "value": "political",
                                "label": "Political",
                                "icon": "🏛️"
                            },
                            {
                                "value": "misleading",
                                "label": "Misleading",
                                "icon": "⚠️"
                            },
                            {
                                "value": "satire",
                                "label": "Satire",
                                "icon": "😄"
                            }
                        ],
                        "supports_confidence": True
                    },
                    config={}
                )
                session.add(topic_tagger)
                
                # Hierarchical science classifier
                science_classifier = Classifier(
                    slug="science-domain-v1",
                    display_name="Scientific Domain Classifier",
                    description="Categorizes scientific claims by domain and accuracy",
                    group_name="science-classifiers",
                    is_active=False,  # Inactive by default for testing
                    output_schema={
                        "type": "hierarchical",
                        "name": "Scientific Domain Classifier",
                        "description": "Categorizes scientific claims by domain",
                        "levels": [
                            {
                                "level": 1,
                                "name": "Category",
                                "choices": [
                                    {"value": "scientific", "label": "Scientific"},
                                    {"value": "pseudoscience", "label": "Pseudoscience"},
                                    {"value": "non_scientific", "label": "Non-Scientific"}
                                ]
                            },
                            {
                                "level": 2,
                                "name": "Domain",
                                "parent_dependent": True,
                                "choices_by_parent": {
                                    "scientific": [
                                        {"value": "climate_science", "label": "Climate Science"},
                                        {"value": "medical", "label": "Medical"},
                                        {"value": "physics", "label": "Physics"}
                                    ],
                                    "pseudoscience": [
                                        {"value": "climate_denial", "label": "Climate Denial"},
                                        {"value": "anti_vax", "label": "Anti-Vaccine"},
                                        {"value": "flat_earth", "label": "Flat Earth"}
                                    ]
                                }
                            }
                        ],
                        "supports_confidence": True
                    },
                    config={}
                )
                session.add(science_classifier)
            
            await session.commit()
            logger.info("Default data inserted successfully")
            
        except Exception as e:
            await session.rollback()
            logger.error("Failed to insert default data", error=str(e))


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