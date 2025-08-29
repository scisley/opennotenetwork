# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FastAPI backend for the AI-powered climate fact-checking system that generates and submits Community Notes to X.com. This service handles post ingestion, classification via LangGraph agents, fact-check generation, and note submission.

## Development Commands

```bash
# Setup and run
poetry install                    # Install dependencies
poetry run python run.py         # Start dev server (localhost:8000)

# Code quality
poetry run ruff check            # Lint code
poetry run ruff format           # Format code  
poetry run mypy .                # Type checking
poetry run black .               # Alternative formatter

# Testing (when available)
poetry run pytest                # Run all tests
poetry run pytest -v -s          # Verbose with print statements
```

## API Documentation

- **Swagger UI**: `http://localhost:8000/api/docs` - Interactive API testing
- **ReDoc**: `http://localhost:8000/api/redoc` - Alternative documentation view
- **OpenAPI Schema**: `http://localhost:8000/api/openapi.json`

## Architecture

### Application Structure

```
app/
├── main.py                 # FastAPI app initialization
├── config.py              # Settings via pydantic-settings
├── database.py            # SQLAlchemy async setup, init_db()
├── models.py              # SQLAlchemy ORM models
├── schemas/               # Pydantic request/response models
│   ├── public.py         # Public API schemas
│   └── admin.py          # Admin API schemas
├── routers/               # API endpoint definitions
│   ├── public.py         # Read-only public endpoints
│   └── admin.py          # Admin CRUD operations
├── services/              # Business logic layer
│   ├── ingestion.py      # X.com API integration
│   ├── classification.py # Classifier orchestration
│   ├── notegen.py        # LangGraph fact-check generation
│   └── submission.py     # Community Notes submission
└── classifiers/           # LangGraph classifier implementations
    ├── base.py           # BaseClassifier abstract class
    ├── registry.py       # Classifier registration system
    └── *_v1.py          # Individual classifier implementations
```

### Database Models

#### Core Tables
- `posts` - Ingested posts with `raw_json` JSONB storage
- `classifiers` - Classifier definitions with `output_schema` JSONB
- `classifications` - Results with `classification_data` JSONB
- `draft_notes` - Generated fact-checks (full_body, concise_body)
- `submissions` - Tracking with X.com submission IDs

#### Key Patterns
- **Post UID**: Format `platform--platform_post_id` (e.g., `x--1234567890`)
- **JSONB Storage**: Flexible schema for classifications and raw data
- **Async Sessions**: All DB operations use `AsyncSession`
- **Auto-initialization**: `init_db()` creates tables and seed data on startup

### API Endpoints

#### Public Routes (`/api/public/`)
```python
GET /posts                 # List posts with search/pagination
GET /posts/{post_uid}      # Get post with classifications
GET /notes                 # List submitted/accepted notes
```

#### Admin Routes (`/api/admin/`)
```python
# Ingestion
POST /ingest               # Trigger X.com ingestion
GET /test-x-auth          # Test X.com credentials

# Classification  
GET /classifiers          # List available classifiers
POST /posts/{post_uid}/classify  # Run classifiers (Query params for array)

# Note Generation
POST /generate-draft      # Create fact-check draft
PUT /drafts/{draft_id}    # Edit draft content

# Submission
POST /submit-note         # Submit to X.com
POST /reconcile           # Check submission status
```

### Service Layer

Services are async functions, not classes:

```python
# Example service pattern
async def classify_post(
    post_uid: str,
    session: AsyncSession,
    classifier_slugs: Optional[List[str]] = None
) -> Dict[str, Any]:
    # Implementation
```

### Classifier System

#### Base Pattern
```python
class BaseClassifier(ABC):
    slug: str
    display_name: str
    
    @abstractmethod
    async def classify(self, post_data: Dict) -> ClassificationResult:
        pass
```

#### Registration
Classifiers auto-register on import via `@register_classifier` decorator.

## X.com Integration

### Authentication
- Uses `xurl` CLI tool via subprocess
- OAuth1 with environment variables:
  - `X_API_KEY`, `X_API_KEY_SECRET`
  - `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET`

### Rate Limiting
- 90 requests per 15 minutes for Community Notes
- Built-in 1-second delays between requests
- Smart duplicate detection (80% threshold stops ingestion)

### Data Processing
- Handles expanded user/media includes
- Processes reply chains and quoted tweets
- Stores full response in `raw_json` JSONB

## Environment Variables

```bash
# Database
DATABASE_URL="postgresql+asyncpg://user:pass@host/db"

# X.com API
X_API_KEY="..."
X_API_KEY_SECRET="..."
X_ACCESS_TOKEN="..."
X_ACCESS_TOKEN_SECRET="..."

# Authentication
CLERK_PUBLISHABLE_KEY="..."
CLERK_SECRET_KEY="..."

# Scheduling
INGEST_SECRET="..."
RECONCILE_SECRET="..."

# LangGraph
LANGGRAPH_API_KEY="..."
LANGGRAPH_API_URL="..."
```

## Database Operations

Development mode - use Neon tool for schema changes:
```sql
-- Add column with auto-update
ALTER TABLE classifications 
  ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE 
  DEFAULT CURRENT_TIMESTAMP;

-- Create update trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_classifications_updated_at 
  BEFORE UPDATE ON classifications 
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

## Testing Strategy

```bash
# Test X.com auth
curl -X POST http://localhost:8000/api/admin/test-x-auth

# Trigger ingestion
curl -X POST "http://localhost:8000/api/admin/ingest?batch_size=5&max_total_posts=15" \
  -H "x-ingest-secret: your-secret"

# Run specific classifier
curl -X POST "http://localhost:8000/api/admin/posts/x--123/classify?classifier_slugs=climate_misinformation_v1&force=true"
```

## Common Patterns

### Query Parameter Arrays
Use `Query` annotation for repeated parameters:
```python
classifier_slugs: Optional[List[str]] = Query(None)
```

### Error Handling
```python
try:
    result = await service_function()
except Exception as e:
    logger.error("Operation failed", error=str(e))
    raise HTTPException(status_code=500, detail=str(e))
```

### JSONB Queries
```python
# Query JSONB fields
query = select(Classification).where(
    Classification.classification_data["type"].astext == "single"
)
```

## Service Status

- ✅ **Ingestion**: Fully implemented with X.com API
- ✅ **Classification**: LangGraph agent integration working
- 🟡 **Note Generation**: Stubbed (returns mock content)
- 🟡 **Submission**: Stubbed (returns mock IDs)
- 🟡 **Authentication**: Bypassed for development

## Dependencies

- **FastAPI**: Web framework with async support
- **SQLAlchemy 2.0**: Async ORM with PostgreSQL
- **Pydantic v2**: Data validation
- **structlog**: Structured logging
- **httpx**: Async HTTP client
- **LangGraph**: Agent orchestration
- **xurl**: X.com API CLI tool (external)