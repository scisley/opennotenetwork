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
- **Three main routers:**
  - `public.py` - Read-only endpoints for submitted/accepted notes
  - `resources.py` - Role-adaptive endpoints (active items for guests, all for admins)
  - `admin.py` - Admin-only endpoints for ingestion, classification, generation, review, submission

### Key Services (`/api/app/services/`)

- `ingestion.py` - X.com API integration with smart duplicate detection and pagination
- `classification.py` - Classifier orchestration with batch processing
- `fact_checking.py` - LangGraph-based fact-checking agent integration
- `note_writing.py` - 280-character Community Note generation
- `submission.py` - Community Notes submission to X.com API
- `evaluation.py` - Note quality evaluation
- `posts.py` - Post queries and filtering
- `validation.py` - Note validation logic
- `x_api_client.py` - Shared X.com OAuth1 client

### Database Schema

Uses `post_uid` pattern: `"platform--platform_post_id"` (e.g., `"x--1234567890"`). Key tables:

- `users` - Admin authentication via Clerk
- `platforms` - Supported social media platforms
- `posts` - Ingested posts with `raw_json` JSONB storage for full X.com data
- `classifiers` - Classifier definitions with `output_schema` JSONB
- `classifications` - Classification results with JSONB storage (single/multi/hierarchical)
- `fact_checkers` - Fact-checker definitions (LangGraph agents)
- `fact_checks` - Fact-check results with full analysis
- `note_writers` - Note writer definitions (280-char note generators)
- `notes` - Generated notes ready for submission
- `submissions` - Submitted notes with X.com submission IDs and status tracking

### X.com API Integration

- Uses OAuth1 authentication via `requests-oauthlib` library
- Shared X API client in [x_api_client.py](api/app/services/x_api_client.py)
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

### Frontend Development

```bash
cd web
npm install                       # Install dependencies
npm run dev                       # Start dev server with Turbopack (localhost:3000)
npm run build                     # Build production application
npm run start                     # Start production server
npm run lint                      # Run ESLint
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
- Admin endpoints require JWT authentication via Clerk
- Test X.com auth: `POST /api/admin/test-x-auth`
- Trigger ingestion: `POST /api/admin/ingest?batch_size=5&max_total_posts=15`

## Authentication System

The application uses Clerk for authentication with JWT tokens. The system provides role-based access control with automatic user synchronization to the database.

### Frontend Authentication (`/web`)

#### Setup and Configuration
- **Clerk Provider**: Wraps the entire app in `layout.tsx`
- **Middleware**: Located at `/web/src/middleware.ts` - protects `/admin` routes
- **Environment Variables**:
  ```bash
  NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY="pk_test_..."
  CLERK_SECRET_KEY="sk_test_..."
  ```

#### Authentication Flow
1. **Public Pages**: All non-admin pages are publicly accessible
2. **Admin Routes**: Protected by middleware that checks:
   - User is authenticated (has valid JWT)
   - User has `admin` role in JWT metadata
   - Redirects to sign-in or home page if unauthorized

#### Making Authenticated API Calls
```typescript
// Use the authenticated API hook
import { useAuthenticatedApi } from '@/lib/auth-axios';

// In your component
const authApi = useAuthenticatedApi();
const response = await authApi.get('/api/admin/endpoint');

// Or use pre-built hooks that include auth
import { useClassifiers } from '@/hooks/use-api';
const { data } = useClassifiers();
```

**Important**: Never use raw `axios` for admin endpoints. Always use `useAuthenticatedApi()` or the pre-built hooks.

### Backend Authentication (`/api`)

#### Setup and Configuration
- **Library**: `fastapi-clerk-auth` for JWT verification
- **JWKS URL**: Configured in settings for JWT validation
- **Environment Variables**:
  ```bash
  CLERK_JWKS_URL="https://your-instance.clerk.accounts.dev/.well-known/jwks.json"
  ```

#### Authentication Flow
1. **JWT Validation**: `ClerkHTTPBearer` validates the JWT signature
2. **User Sync**: On each request, the system:
   - Extracts user info from JWT (email, role)
   - Creates or updates user in database
   - Returns user object for request context

#### Protected Endpoints
```python
from app.auth import require_admin, get_current_user

# For admin-only endpoints
@router.get("/admin-endpoint")
async def admin_endpoint(
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session)
):
    # user is guaranteed to be admin
    pass

# For any authenticated user
@router.get("/user-endpoint")
async def user_endpoint(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    # user is any authenticated user
    pass
```

### Clerk Dashboard Configuration

#### Session Token Template
Must be configured to include email and role:
```json
{
  "email": "{{user.primary_email_address}}",
  "metadata": "{{user.public_metadata}}"
}
```

#### User Metadata
Set user roles in public metadata:
```json
{
  "role": "admin"  // or "viewer"
}
```

### JWT Token Structure

Clerk JWTs include:
- `sub`: Clerk user ID
- `email`: User's email address (configured in session token)
- `metadata`: Contains role information
- `exp`, `iat`, `nbf`: Token timing fields

Tokens are short-lived (60 seconds) and automatically refreshed by Clerk SDK.

### Database User Management

Users are automatically synchronized to the database:
- **First Access**: Creates user record with email, display_name, and role
- **Subsequent Access**: Updates role if changed in Clerk
- **User Table Fields**:
  - `user_id`: UUID (internal)
  - `email`: From JWT (unique)
  - `display_name`: Defaults to email
  - `role`: Either "admin" or "viewer"

### Testing Authentication

#### Get JWT Token for Testing
```javascript
// In browser console at http://localhost:3000
await window.Clerk.session.getToken()
```

#### Test with Curl
```bash
# Test authentication
curl -X GET http://localhost:8000/api/admin/auth-test \
  -H "Authorization: Bearer YOUR_TOKEN"

# Test admin access
curl -X GET http://localhost:8000/api/admin/admin-test \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### Swagger UI Testing
1. Go to http://localhost:8000/api/docs
2. Click "Authorize" button
3. Enter: `Bearer YOUR_TOKEN`
4. All requests will include authentication

### Common Issues and Solutions

1. **403 Forbidden**: Check that:
   - JWT includes email field (configure in Clerk Dashboard)
   - User has admin role in public metadata
   - Frontend is using `useAuthenticatedApi()` not raw `axios`

2. **Token Expiry**: Tokens expire after 60 seconds
   - Frontend auto-refreshes via Clerk SDK
   - For testing, get fresh token with `getToken()`

3. **User Not Created**: Ensure:
   - Email is in JWT (check Clerk session token template)
   - Database connection is working
   - No transaction rollbacks occurring

## API Endpoint Architecture

### Design Philosophy

The API uses a **resource-based URL pattern with role-adaptive responses**. The same endpoint returns different data based on the caller's authentication status and role, rather than having separate endpoints for different user types.

### Endpoint Categories

#### 1. Public-Only Endpoints (`/api/public/*`)
- **Never require authentication**
- Return the same data for everyone
- Examples:
  - `GET /api/public/notes` - Submitted/accepted community notes
  - `GET /api/public/posts` - Public post feed with classifications

#### 2. Resource Endpoints (`/api/*`)
- **Adapt based on authentication**
- Same URL, different data based on role
- Examples:
  - `GET /api/classifiers` - Returns:
    - Guest users: Active classifiers only (same fields as admin)
    - Admin users: All classifiers (active and inactive)
  - `GET /api/classifiers/{slug}` - Returns:
    - Guest users: Classifier details (only if active)
    - Admin users: Classifier details (regardless of active status)
  - `GET /api/fact-checkers` - Returns:
    - Guest users: Active fact checkers only
    - Admin users: All fact checkers (active and inactive)
  - `GET /api/posts/{post_uid}/fact-checks` - Returns:
    - Guest users: Completed fact checks only
    - Admin users: All fact checks (including pending/failed)

#### 3. Admin-Only Endpoints (`/api/admin/*`)
- **Require authentication and admin role**
- Return 401/403 for unauthorized users
- Examples:
  - `POST /api/admin/ingest` - Trigger X.com ingestion
  - `POST /api/admin/posts/{post_uid}/classify` - Run classifiers
  - `POST /api/admin/posts/{post_uid}/fact-check/{slug}` - Run fact check
  - `DELETE /api/admin/posts/{post_uid}/fact-check/{slug}` - Delete fact check
  - `POST /api/admin/classifiers` - Create new classifier
  - All mutation operations (CREATE, UPDATE, DELETE)

### Frontend API Client Architecture

The frontend uses three patterns for API access:

#### 1. Plain `api` Object
```typescript
const api = axios.create({ baseURL: API_BASE_URL });
```
- For endpoints that **never** need authentication
- Used by: `usePublicNotes()`, `usePublicPosts()`, etc.

#### 2. `useApi()` Hook
```typescript
function useApi() {
  // Returns axios instance with conditional auth
  // Includes token if user is logged in, continues without if not
}
```
- For resource endpoints with **role-adaptive responses**
- Automatically includes auth token if available
- Silently continues without auth for guest users
- Used by: `useClassifiers()`, `useFactCheckers()`, `useFactChecks()`

#### 3. `useAuthenticatedApi()` Hook
```typescript
function useAuthenticatedApi() {
  // Returns axios instance that requires auth
  // Throws error if no token available
}
```
- For **admin-only** endpoints
- Requires authentication token
- Fails fast if user not authenticated
- Used by: `useClassifyPost()`, `useRunFactCheck()`, `useDeleteFactCheck()`

### Role-Based Access Control

#### Guest Users (Not Authenticated)
- Access to all `/api/public/*` endpoints
- Access to resource endpoints (`/api/*`) with limited data
- Cannot access `/api/admin/*` endpoints

#### Viewer Users (Authenticated, Non-Admin)
- Same as guest users currently
- Future: Could have additional privileges

#### Admin Users (Authenticated, role: "admin")
- Full access to all endpoints
- Get enriched data from resource endpoints
- Can perform all CRUD operations

### Example: Classifiers Endpoint

```python
# /api/classifiers - Single endpoint, role-based filtering
@router.get("/classifiers")
async def get_classifiers(
    current_user: Optional[User] = Depends(get_optional_user),
    session: AsyncSession = Depends(get_session)
):
    query = select(Classifier)
    
    if not current_user or current_user.role != "admin":
        # Guest/viewer: Only active classifiers
        query = query.where(Classifier.is_active == True)
    else:
        # Admin: All classifiers (can filter by is_active param)
        
    # Everyone gets the same response schema (ClassifierPublicResponse)
    # Only difference is which classifiers they can see
```

### Example: Fact Checks Endpoint

```python
# /api/posts/{post_uid}/fact-checks - Role-adaptive responses
@router.get("/posts/{post_uid}/fact-checks")
async def get_post_fact_checks(
    post_uid: str,
    current_user: Optional[User] = Depends(get_optional_user),
    session: AsyncSession = Depends(get_session)
):
    query = select(FactCheck).where(FactCheck.post_uid == post_uid)
    
    if not current_user or current_user.role != "admin":
        # Guest/viewer: Only completed fact checks
        query = query.where(FactCheck.status == "completed")
    # Admin: All fact checks including pending/failed
    
    # Same response schema for all users (FactCheckPublicResponse)
```

### Best Practices

1. **Use resource-based URLs**: `/api/posts`, not `/api/public/posts` and `/api/admin/posts`
2. **Let authentication determine capabilities**, not URLs
3. **Keep mutations in admin endpoints**: Only GET operations should be adaptive
4. **Use consistent response schemas**: Same fields for all users when possible
5. **Document role-specific behavior** in endpoint docstrings

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
├── clarity_v1/
│   ├── __init__.py
│   └── classifier.py
├── partisan_tilt_classifier_v1/
│   ├── __init__.py
│   └── classifier.py
├── media_type_v1/
│   ├── __init__.py
│   └── classifier.py
└── [other classifiers...]
```

Each classifier folder can contain additional files as needed (helpers, prompts, utils, etc.).
The `__init__.py` file should export the main classifier class for clean imports.

### Fact-Checker Code Structure

Fact-checkers are organized similarly under `/api/app/fact_checkers/`:

```
fact_checkers/
├── base.py                         # BaseFactChecker abstract class
├── registry.py                     # Maps slugs to fact-checker implementations
├── advocate_adversary_v1/          # Main fact-checker
│   ├── __init__.py
│   ├── fact_checker.py
│   └── graph.py                   # LangGraph workflow definition
├── shared/                         # Shared utilities
│   ├── enums.py                   # Verdict enums (True/False/Missing Context/etc)
│   └── schemas.py                 # Pydantic models for fact-check results
└── [other fact-checkers...]
```

### Note-Writer Code Structure

Note-writers generate 280-character Community Notes under `/api/app/note_writers/`:

```
note_writers/
├── base.py                         # BaseNoteWriter abstract class
├── registry.py                     # Maps slugs to note-writer implementations
└── x_note_writer_v1/
    ├── __init__.py
    ├── note_writer.py
    └── graph.py                   # LangGraph workflow for note generation
```

## Configuration

### Environment Variables

#### Backend (.env in /api)

```bash
# Environment
ENVIRONMENT=development
PRODUCTION=false

# Database
DATABASE_URL="postgresql+asyncpg://user:pass@host/db"

# X.com API
X_API_KEY="..."
X_API_KEY_SECRET="..."
X_ACCESS_TOKEN="..."
X_ACCESS_TOKEN_SECRET="..."

# Clerk Authentication
CLERK_JWKS_URL="https://your-instance.clerk.accounts.dev/.well-known/jwks.json"

# OpenAI (for fact-checking agents)
OPENAI_API_KEY="sk-..."

# LangSmith (optional - for LLM observability)
LANGSMITH_API_KEY="lsv2_sk_..."
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_PROJECT=open-note-network

# CORS Settings
ALLOWED_ORIGINS=["http://localhost:3000","https://your-frontend.vercel.app"]
ALLOWED_HOSTS=["localhost","your-api.fly.dev"]

# Scheduling Secrets (for GitHub Actions)
INGEST_SECRET="..."
RECONCILE_SECRET="..."
```

#### Frontend (.env.local in /web)

```bash
# API Backend URL
NEXT_PUBLIC_API_URL="http://localhost:8000/api"

# Clerk Authentication (same account as backend)
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY="pk_test_..."
CLERK_SECRET_KEY="sk_test_..."

# Analytics (optional)
NEXT_PUBLIC_MIXPANEL_TOKEN="..."
NEXT_PUBLIC_ANALYTICS_ENABLED=false
```

## Important Implementation Details

- **Authentication**: Full Clerk JWT implementation with role-based access control (admin/viewer)
- **Rate Limiting**: Built-in 1-second delays between X API requests (90 req/15min limit)
- **Error Handling**: Comprehensive logging with structlog
- **Database**: Auto-creates tables and inserts default data on startup via `init_db()`
- **Pagination**: Smart duplicate detection (80% threshold) prevents infinite loops
- **Post Processing**: Handles X.com's expanded user/media data structure
- **URL Encoding**: Properly handles pagination tokens with special characters
- **Link Verification**: Note writer validates all URLs before submission (no broken links)
- **UTM Param Cleaning**: Removes OpenAI UTM parameters from fact-check citations
- **JSONB Storage**: Flexible schema for classifications, fact-checks, and raw post data

## External Dependencies

- **PostgreSQL**: Via Neon cloud service with asyncpg driver (project: floral-mud-07640645)
- **Clerk**: Authentication service with JWT-based auth and role management
- **LangGraph**: Agent orchestration for classifiers, fact-checkers, and note writers
- **OpenAI GPT**: Powers LangGraph agents (GPT-4o, GPT-5 with reasoning)
- **requests-oauthlib**: OAuth1 authentication library for X.com API
- **LangSmith**: Optional LLM observability and tracing platform

## Service Status

- ✅ **Ingestion**: Fully implemented with X.com API and auto-classification
- ✅ **Classification**: LangGraph agents working with flexible classifier system (domain, clarity, partisan-tilt, media-type)
- ✅ **Fact-Checking**: LangGraph advocate-adversary pattern fully implemented
- ✅ **Note Writing**: 280-character note generation with link verification
- ✅ **Submission**: Full X.com Community Notes API integration with status tracking
- ✅ **Authentication**: Clerk JWT with role-based access control
- ✅ **Evaluation**: X.com note quality scoring endpoint integration

# Notes

- The Neon project ID for this project is floral-mud-07640645
- When running the project yourself, don't use the standard port numbers.
  Reserve those for the operator.
- The user has the front end server running at http://localhost:3000/