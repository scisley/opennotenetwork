# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered climate fact-checking system that generates and submits Community Notes to X.com. The system uses a monorepo architecture with FastAPI backend (`/api`) and Next.js frontend (`/web`).

**Core Workflow:**
1. **Ingestion** - Fetch posts eligible for Community Notes from X.com API
2. **Classification** - Tag posts using LangGraph agents with flexible classification system
3. **Generation** - Create both full fact-checks and 280-char concise notes via LangGraph
4. **Review** - Admin approval workflow with editing capabilities
5. **Submission** - Send approved notes to X.com Community Notes API
6. **Reconciliation** - Track outcomes and update database status

## Frontend Architecture (`/web`)

### Tech Stack
- **Next.js 15** with App Router and Turbopack
- **TypeScript** with strict mode
- **Tailwind CSS** for styling
- **shadcn/ui** components
- **React Query (TanStack Query)** for data fetching and caching
- **React Hook Form + Zod** for forms and validation
- **Axios** for API calls

### Development Commands

```bash
cd web
npm install              # Install dependencies
npm run dev             # Start dev server with Turbopack (localhost:3000)
npm run build           # Build production application
npm run start           # Start production server
npm run lint            # Run ESLint
```

### Key Frontend Patterns

#### Post UID System
Posts use URL-safe UIDs in format `platform--platform_post_id` (e.g., `x--1234567890`). URLs automatically encode these for routing: `/notes/x--1234567890`.

#### Data Fetching Hooks (`/web/src/hooks/use-api.ts`)
- `usePublicNotes()` - Fetch submitted/accepted notes
- `usePublicPosts()` - Fetch posts with pagination and search
- `usePostById()` - Fetch single post details
- `useClassifiers()` - Fetch available classifiers
- `useClassifyPost()` - Trigger classification for a post

#### Custom Hooks
- `useLocalStorage()` - Persist state to localStorage with TypeScript generics

#### Component Architecture
- **Classification Display**: Minimal chips with modal for details (`ClassificationChips`)
- **Admin Controls**: Classification runner with localStorage persistence (`ClassificationAdmin`)
- **Tweet Embedding**: X.com tweet display with reply/quote chains (`TwitterEmbed`)
- **Layout**: Responsive side-by-side for single tweets, stacked for chains

### Environment Variables

```bash
# Frontend (.env.local)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Backend Architecture (`/api`)

### Tech Stack
- **FastAPI** with async SQLAlchemy ORM
- **PostgreSQL** via Neon cloud (floral-mud-07640645)
- **Poetry** for dependency management
- **Pydantic** for data validation

### Development Commands

```bash
cd api
poetry install                    # Install dependencies
poetry run python run.py         # Start dev server (localhost:8000)
poetry run ruff check            # Lint code
poetry run ruff format           # Format code
poetry run mypy .                # Type checking
```

### Database Schema

#### Core Tables
- `posts` - Ingested posts with deduplication
- `classifiers` - Flexible classifier definitions
- `classifications` - JSONB storage for classification results
- `submissions` - Note submission tracking

#### Classification System
- **Classifiers**: Define classification logic with output schemas
- **Classifications**: Store results as JSONB with type-specific structures:
  - `single`: Single choice with confidence
  - `multi`: Multiple values with individual confidences
  - `hierarchical`: Multi-level categorization

### API Endpoints

#### Public Routes (`/api/public/`)
- `GET /posts` - List posts with search
- `GET /posts/{post_uid}` - Get post details with classifications
- `GET /notes` - List submitted/accepted notes

#### Admin Routes (`/api/admin/`)
- `POST /ingest` - Trigger X.com ingestion
- `GET /classifiers` - List available classifiers
- `POST /posts/{post_uid}/classify` - Run classifiers on post
- Headers: `x-ingest-secret` or `x-reconcile-secret`

### X.com Integration
- Uses `requests-oauthlib` library with OAuth1 authentication
- Shared API client in backend ([x_api_client.py](../api/app/services/x_api_client.py))
- Rate limits: 90 requests per 15 minutes
- Smart duplicate detection (80% threshold)
- Handles reply chains and quoted tweets

## Database Operations

Development mode - use Neon tool for schema changes:
```sql
-- Example: Add column with trigger
ALTER TABLE classifications ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE;
CREATE TRIGGER update_classifications_updated_at 
  BEFORE UPDATE ON classifications 
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

## Current Service Status

- ✅ **Ingestion**: Fully implemented with X.com API
- ✅ **Classification**: LangGraph agent integration with flexible system
- 🟡 **Note Generation**: Stubbed (returns mock fact-check content)
- 🟡 **Submission**: Stubbed (returns mock submission IDs)
- 🟡 **Authentication**: Stubbed (bypassed for development)

## Important Implementation Notes

- **Classification Storage**: JSONB for flexible schema evolution
- **LocalStorage Persistence**: Admin selections persist across sessions
- **Responsive Layouts**: Side-by-side for single tweets, stacked for chains
- **Query Parameter Arrays**: Use `Query` annotation for repeated params in FastAPI
- **Database Timestamps**: Use triggers for automatic `updated_at` updates
- **Neon Project ID**: floral-mud-07640645