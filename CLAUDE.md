# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OpenNoteNetwork is an open-source AI-powered fact-checking network that generates and submits Community Notes to X.com. The system follows a monorepo architecture with FastAPI backend (`/api`) and Next.js frontend (`/web`).

**Core Workflow:**

1. **Ingestion** - Fetch posts eligible for Community Notes from X.com API
2. **Classification** - Tag posts by topic (climate, politics, health, science, etc.)
3. **Generation** - Create both full fact-checks and 280-char concise notes via LangGraph
4. **Review** - Admin approval workflow with editing capabilities
5. **Submission** - Send approved notes to X.com Community Notes API
6. **Reconciliation** - Track outcomes and update database status

## Architecture

### Backend (`/api`)

- **FastAPI monolith** with async SQLAlchemy ORM and PostgreSQL (Neon cloud)
- **Poetry** for dependency management (`poetry install`, `poetry run`)
- **Two main routers:**
  - `public.py` - Read-only endpoints for submitted/accepted notes
  - `admin.py` - Authenticated endpoints for ingestion, classification, generation, review, submission

### Key Services (`/api/app/services/`)

- `ingestion.py` - X.com API integration with smart duplicate detection and pagination
- `classifier.py` - Topic classification (currently stubbed)
- `notegen.py` - LangGraph-based fact-checking agent integration (currently stubbed)
- `submission.py` - Community Notes submission to X.com (currently stubbed)
- `validation.py` - Note validation logic

### Database Schema

Uses `post_uid` pattern: `"platform--platform_post_id"` (e.g., `"x--1234567890"`). Key tables:

- `users` - Admin authentication via Clerk
- `platforms` - Supported social media platforms
- `posts` - Ingested posts with deduplication
- `topics` - Classification topics (climate, politics, health, science, etc.)
- `post_topics` - Many-to-many post/topic relationships
- `draft_notes` - Generated fact-checks (full + concise versions)
- `submissions` - Submitted notes with status tracking

### X.com API Integration

- Uses `xurl` command-line tool for authentication (OAuth1 via subprocess)
- Environment variables: `X_API_KEY`, `X_API_KEY_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET`
- Rate limits: 90 requests per 15 minutes for Community Notes endpoints

## Development Commands

### Backend Development

```bash
cd api
poetry install                    # Install dependencies
poetry run python run.py         # Start dev server (localhost:8000)
poetry run python -m pytest      # Run tests (when available)
poetry run ruff check             # Lint code
poetry run ruff format            # Format code
poetry run mypy .                 # Type checking
```

### Database Operations

```bash
# Database auto-initializes on startup via init_db()
# No manual migrations needed - uses SQLAlchemy create_all()
```

We are currently in development mode. Do not worry about writing database
migrations for now. Instead, use the Neon tool to make any necessary changes to
the database.

### API Testing

- Swagger UI available at `http://localhost:8000/api/docs`
- Admin endpoints require `x-ingest-secret` or `x-reconcile-secret` headers
- Test X.com auth: `POST /api/admin/test-x-auth`
- Trigger ingestion: `POST /api/admin/ingest?batch_size=5&max_total_posts=15`

## Key Technical Patterns

### Ingestion Logic

- Fetches posts in configurable batches (default 50, max 100 per X API)
- Stops automatically when high duplicate ratio detected (80% threshold)
- Uses PostgreSQL `ON CONFLICT DO UPDATE` for graceful duplicate handling
- Tracks `new_posts` vs `updated_posts` for intelligent stopping

### Post UID System

```python
from app.database import build_post_uid, parse_post_uid
post_uid = build_post_uid("x", "1234567890")  # "x--1234567890"
platform, post_id = parse_post_uid(post_uid) # ("x", "1234567890")
```

### Service Integration Points

- Services are designed as async functions, not classes
- Currently stubbed services return mock data with proper schemas
- External LangGraph agent integration point in `notegen.py`

### Classifier Output Specification

All classifiers must inherit from `BaseClassifier` and return one of three output formats from their `classify()` method:

#### 1. Single Classification

```python
{
    "type": "single",
    "value": "category_name",        # Single category value
    "confidence": 0.85                # Optional confidence score (0.0-1.0)
}
```

#### 2. Multi Classification

```python
{
    "type": "multi",
    "values": [
        {"value": "category1", "confidence": 0.9},
        {"value": "category2", "confidence": 0.75},
        {"value": "category3", "confidence": 0.6}
    ]
}
```

#### 3. Hierarchical Classification

```python
{
    "type": "hierarchical",
    "levels": [
        {"level": 1, "value": "main_category", "confidence": 0.95},
        {"level": 2, "value": "sub_category", "confidence": 0.8}
    ]
}
```

**Important Notes:**

- The `type` field is **required** and must be one of: `"single"`, `"multi"`, or `"hierarchical"`
- Values must match the choices defined in the classifier's database schema
- Confidence scores are optional but recommended
- The classifier wrapper validates output against the schema using `validate_output()`
- For `multi` type, respect the `max_selections` limit from the schema

### Classifier Code Structure

Classifiers are organized in subfolders under `/api/app/classifiers/`:

```
classifiers/
├── base.py                         # BaseClassifier abstract class
├── registry.py                     # Maps slugs to classifier implementations
├── domain_classifier_v1/
│   ├── __init__.py                # Package exports
│   └── classifier.py              # DomainClassifierV1 implementation
├── climate_misinformation_v1/
│   ├── __init__.py
│   └── classifier.py
└── [other classifiers...]
```

Each classifier folder can contain additional files as needed (helpers, prompts, utils, etc.).
The `__init__.py` file should export the main classifier class for clean imports.

## Configuration

### Environment Variables (.env)

```bash
# Database
DATABASE_URL="postgresql://user:pass@host/db"

# X.com API
X_API_KEY="..."
X_API_KEY_SECRET="..."
X_ACCESS_TOKEN="..."
X_ACCESS_TOKEN_SECRET="..."

# Clerk Authentication
CLERK_PUBLISHABLE_KEY="..."
CLERK_SECRET_KEY="..."

# Scheduling Secrets
INGEST_SECRET="..."
RECONCILE_SECRET="..."
```

## Important Implementation Details

- **Authentication**: Currently stubbed - admin endpoints bypass auth for development
- **Rate Limiting**: Built-in 1-second delays between X API requests
- **Error Handling**: Comprehensive logging with structlog
- **Database**: Auto-creates tables and inserts default data on startup
- **Pagination**: Smart duplicate detection prevents infinite loops
- **Post Processing**: Handles X.com's expanded user/media data structure
- **URL Encoding**: Properly handles pagination tokens with special characters

## External Dependencies

- **xurl**: Command-line tool for X.com API access (must be installed separately)
- **PostgreSQL**: Via Neon cloud service with asyncpg driver
- **Clerk**: Authentication service (integration stubbed)
- **LangGraph**: External fact-checking agent (integration stubbed)

## Service Status

- ✅ **Ingestion**: Fully implemented with X.com API and auto-classification
- ✅ **Classification**: LangGraph agents working for multiple topics
- 🟡 **Note Generation**: Stubbed (returns mock fact-check content)
- 🟡 **Submission**: Stubbed (returns mock submission IDs)
- 🟡 **Authentication**: Stubbed (bypassed for development)

# Notes

- The Neon project ID for this project is floral-mud-07640645
- When running the project yourself, don't use the standard port numbers.
  Reserve those for the operator.
