# OpenNoteNetwork

**AI-powered fact-checking network that generates and submits Community Notes to X.com**

OpenNoteNetwork is an open-source system that automatically ingests posts eligible for Community Notes, classifies them by topic and veracity, generates comprehensive fact-checks using LLM-based agents, and submits concise 280-character Community Notes to X.com. This project was completed as part of the [AI for Human Reasoning Fellowship](https://snazzy-cajeta-24ac71.netlify.app/) at the Future of Life Institute.

**📊 Project Results (Sept-Oct 2025):**

- **11,065 posts** analyzed from X.com's Community Notes API
- **2,496 fact-checks** generated using LLM agents
- **132 Community Notes** submitted to X.com
- **14 notes** achieved "Community Rated Helpful" status
- **2.3M impressions** across all successful notes
- **1.9M views** on most successful note (Elon Musk's Cybertruck post)
- **$0.39** cost per click to companion website

🔗 **[Read the full writeup](docs/writeup/final_writeup.md)** - An in-depth analysis of building and running this system, including lessons learned, cost analysis, and recommendations for future work.

## ⚠️ Project Status

This project is **complete and no longer actively maintained**. The code is provided as-is for educational and research purposes. I'm not accepting pull requests, but the codebase is open-source (MIT License) for you to learn from, experiment with, and build upon.

The companion website [opennotenetwork.com](https://opennotenetwork.com) continues to ingest and classify posts from X.com's Community Notes API, but fact-checking is currently disabled due to cost.

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Getting Started](#getting-started)
- [Environment Configuration](#environment-configuration)
- [Project Structure](#project-structure)
- [Key Concepts](#key-concepts)
- [Development](#development)
- [Cost & Performance](#cost--performance)
- [Limitations & Future Work](#limitations--future-work)
- [License](#license)
- [Contact](#contact)

## Features

### Core Capabilities

- **Automated Post Ingestion**: Fetches posts eligible for Community Notes from X.com API
- **Multi-dimensional Classification**:
  - Domain classification (politics, health, climate, media attribution, etc.)
  - Clarity scoring (how fact-checkable is the claim?)
  - Political tilt detection
  - Media type analysis (text, images, video)
- **LLM-Based Fact-Checking**: Uses adversarial debate pattern (advocate vs. adversary agents) with GPT-5
- **Automated Note Generation**: Creates 280-character Community Notes optimized for X.com's requirements
- **Submission & Tracking**: Submits notes to X.com and tracks their status (helpful, not helpful, needs more ratings)
- **Admin Dashboard**: Next.js frontend for searching the dataset, reviewing fact-checks, editing notes, and managing submissions
- **Public API**: Read-only endpoints for accessing submitted notes and post classifications

## Architecture

OpenNoteNetwork uses a **monorepo architecture** with two main components:

- **Backend** (`/api`): FastAPI application with async SQLAlchemy ORM and PostgreSQL (Neon cloud)
- **Frontend** (`/web`): Next.js 15 application with TypeScript, Tailwind CSS, and shadcn/ui

### Tech Stack

**Backend:**

- FastAPI for REST API
- SQLAlchemy (async) with PostgreSQL
- LangGraph for fact-checking agents
- OpenAI GPT-5 for LLM capabilities
- Clerk for JWT authentication
- requests-oauthlib for X.com API integration
- Poetry for dependency management

**Frontend:**

- Next.js 15 with App Router and Turbopack
- TypeScript with strict mode
- Tailwind CSS + shadcn/ui components
- TanStack Query (React Query) for data fetching
- Clerk for authentication
- Axios for API calls

**Infrastructure:**

- PostgreSQL database (Neon cloud)
- GitHub Actions for scheduled ingestion (every 3 hours)
- Fly.io deployment (API)
- Vercel deployment (frontend)

## Getting Started

### Prerequisites

- **Python 3.11+** with Poetry installed
- **Node.js 18+** with npm
- **PostgreSQL database** (recommend [Neon](https://neon.tech) for cloud hosting)
- **X.com Developer Account** with Community Notes API access
- **OpenAI API Key** for GPT models
- **Clerk Account** for authentication (optional, can disable auth)

### Backend Setup

1. **Navigate to the API directory:**

   ```bash
   cd api
   ```

2. **Install dependencies:**

   ```bash
   poetry install
   ```

3. **Configure environment variables:**

   ```bash
   cp .env.example .env
   # Edit .env with your credentials (see Environment Configuration below)
   ```

4. **Start the development server:**
   ```bash
   poetry run python run.py
   ```

The API will be available at `http://localhost:8000` with interactive docs at `http://localhost:8000/api/docs`.

### Frontend Setup

1. **Navigate to the web directory:**

   ```bash
   cd web
   ```

2. **Install dependencies:**

   ```bash
   npm install
   ```

3. **Configure environment variables:**

   ```bash
   cp .env.example .env.local
   # Edit .env.local with your credentials
   ```

4. **Start the development server:**
   ```bash
   npm run dev
   ```

The frontend will be available at `http://localhost:3000`.

### Database Setup

The database schema is automatically initialized on first startup via SQLAlchemy's `create_all()` method. No manual migrations are needed for development.

If you're using Neon (recommended):

1. Create a free account at [neon.tech](https://neon.tech)
2. Create a new project
3. Copy the connection string to `DATABASE_URL` in your `.env`
4. The database will auto-initialize on first API startup

### Getting setup with the X.com Community Notes API

Follow the instructions at https://communitynotes.x.com/guide/en/api/overview

You'll need the access credentials, but you won't need to clone their example repo and setup Github actions.

### Setting Up Clerk Authentication

See [web/CLERK_SETUP.md](web/CLERK_SETUP.md) for detailed instructions on configuring Clerk authentication with role-based access control.

## Project Structure

```
opennotenetwork/
├── api/                          # FastAPI backend
│   ├── app/
│   │   ├── classifiers/          # Post classification modules
│   │   │   ├── domain_classifier_v1/
│   │   │   ├── clarity_v1/
│   │   │   ├── partisan_tilt_classifier_v1/
│   │   │   └── ...
│   │   ├── fact_checkers/        # Fact-checking agents
│   │   │   ├── advocate_adversary_v1/  # Main fact-checker
│   │   │   └── ...
│   │   ├── note_writers/         # Community Note generators
│   │   │   └── x_note_writer_v1/
│   │   ├── routers/              # FastAPI route handlers
│   │   │   ├── admin.py          # Admin-only endpoints
│   │   │   ├── public.py         # Public read-only endpoints
│   │   │   └── resources.py      # Role-adaptive endpoints
│   │   ├── services/             # Business logic
│   │   │   ├── ingestion.py      # X.com API integration
│   │   │   ├── classifier.py     # Classification orchestration
│   │   │   ├── fact_check.py     # Fact-checking orchestration
│   │   │   ├── submission.py     # Community Note submission
│   │   │   └── x_api_client.py   # X.com API client
│   │   ├── auth.py               # Clerk JWT authentication
│   │   ├── database.py           # Database utilities
│   │   ├── models.py             # SQLAlchemy models
│   │   └── schemas.py/           # Pydantic schemas
│   ├── main.py                   # FastAPI app entrypoint
│   ├── run.py                    # Development server
│   └── pyproject.toml            # Poetry dependencies
│
├── web/                          # Next.js frontend
│   ├── src/
│   │   ├── app/                  # Next.js App Router pages
│   │   │   ├── page.tsx          # Home page (public posts)
│   │   │   ├── posts/            # Post detail pages
│   │   │   ├── admin/            # Admin dashboard (auth required)
│   │   │   └── ...
│   │   ├── components/           # React components
│   │   │   ├── ui/               # shadcn/ui components
│   │   │   ├── posts/            # Post-related components
│   │   │   ├── fact-checks/      # Fact-check components
│   │   │   └── ...
│   │   ├── hooks/                # React Query hooks (useApi, etc.)
│   │   ├── lib/                  # Utilities and configs
│   │   └── types/                # TypeScript types
│   ├── public/                   # Static assets
│   └── package.json              # npm dependencies
│
├── docs/                         # Documentation
│   └── writeup/                  # Project writeup
│       └── final_writeup.md      # Comprehensive project analysis
│
├── .github/
│   └── workflows/
│       └── scheduled-ingestion.yml  # Auto-ingestion every 3 hours
│
├── CLAUDE.md                     # Development guide (for Claude Code)
└── README.md                     # This file
```

## Key Concepts

### Post UID System

Posts are identified using a standardized UID format: `platform--platform_post_id`

Example: `x--1234567890` (X.com post with ID 1234567890)

This allows the system to potentially support multiple platforms (X, Facebook, TikTok, YouTube) in the future.

### Classifier Architecture

All classifiers inherit from `BaseClassifier` and return structured output:

**Single Classification:**

```python
{
    "type": "single",
    "value": "category_name",
    "confidence": 0.85  # Optional
}
```

**Multi Classification:**

```python
{
    "type": "multi",
    "values": [
        {"value": "category1", "confidence": 0.9},
        {"value": "category2", "confidence": 0.75}
    ]
}
```

**Hierarchical Classification:**

```python
{
    "type": "hierarchical",
    "levels": [
        {"level": 1, "value": "main_category", "confidence": 0.95},
        {"level": 2, "value": "sub_category", "confidence": 0.8}
    ]
}
```

Classifiers are organized in subfolders under `/api/app/classifiers/` and registered in `registry.py`.

### Fact-Checking Agent Pattern

The main fact-checker uses an **adversarial debate pattern**:

1. **Context Gathering**: Research the post and gather background information
2. **Early Exit Check**: If claim is obviously true/false/satire, skip to summary
3. **Advocate Agent**: Finds evidence supporting the claim
4. **Adversary Agent**: Finds evidence contradicting the claim
5. **Summary**: Synthesizes findings into a comprehensive fact-check
6. **Verdict**: Assigns classification (False, Partly False, Missing Context, True, etc.)

This pattern was the first architecture tried and produced good results without optimization. Better architectures likely exist.

### API Endpoint Design

The API uses **role-adaptive endpoints** - the same URL returns different data based on authentication:

- **Public endpoints** (`/api/public/*`): Always public, same data for everyone
- **Resource endpoints** (`/api/*`): Return filtered data based on role (guests see active items only, admins see everything)
- **Admin endpoints** (`/api/admin/*`): Require authentication and admin role

Frontend uses three API patterns:

- `api` object: For public endpoints (no auth)
- `useApi()` hook: For role-adaptive endpoints (conditional auth)
- `useAuthenticatedApi()` hook: For admin endpoints (required auth)

## Development

### Running the Backend

```bash
cd api
poetry run python run.py          # Start dev server (localhost:8000)
poetry run ruff check              # Lint code
poetry run ruff format             # Format code
poetry run mypy .                  # Type checking
```

API documentation available at: `http://localhost:8000/api/docs`

### Running the Frontend

```bash
cd web
npm run dev                        # Start dev server (localhost:3000)
npm run build                      # Build for production
npm run lint                       # Run ESLint
```

### Database Management

The system uses automatic database initialization. On startup, `init_db()`:

- Creates all tables via SQLAlchemy's `create_all()`
- Inserts default data (platforms, classifiers, fact-checkers)
- No manual migrations needed during development

For production, consider implementing proper migrations with Alembic.

### Current Limitations

1. **No Video Processing**: ~35% of posts contain video, currently skipped
2. **Speed Bottlenecks**: Fact-checking takes several minutes; by the time notes are approved, most views have occurred
3. **Political Bias Challenge**: Bridging algorithm struggles with highly partisan claims, even when factually wrong
4. **Limited Evaluation**: No rigorous evaluation dataset; relying on vibes and X.com's rating system
5. **Manual Review**: Evaluation step is manual; should be automated for speed
6. **Unable to Verify**: System doesn't distinguish between "insufficient evidence" vs. "absence of evidence is the evidence"

### Potential Improvements

**Retrieval-Augmented Generation (RAG):**

- Index prior Community Notes (open-source dataset available)
- Retrieve semantically similar notes during fact-checking
- Reuse helpful notes with minor tweaks
- Reference existing Community Notes in new notes

**Reply Analysis:**

- Analyze post replies via X.com API
- Extract crowd-sourced corrections and counter-evidence
- Filter signal from noise using LLMs

**Video Processing:**

- Implement video frame extraction or multimodal models
- Handle video-based claims (currently 35% of posts)

**Reverse Image Search & AI Detection:**

- Detect manipulated or out-of-context images
- Use reverse image lookup (e.g., Bing Visual Search)
- Check for AI-generated content (e.g., Google SynthID watermarks)

**Proper Evaluation Dataset:**

- Ground truth labels for accuracy verification
- Diverse post types (political, health, climate, satire, opinion)
- Edge cases and adversarial examples
- Measure improvement across different architectures

**Community Notes System Improvements:**

- Retroactive notifications (show note to everyone who viewed the post)
- Reach penalties for repeated misinformation
- "Slow-tweet" option (voluntary fact-check delay for increased reach)

## License

MIT License - see LICENSE file for details.

This project is provided as-is for educational and research purposes. Feel free to learn from it, experiment with it, and build upon it. Attribution is appreciated but not required.

## Contact

This project was created by **Steve Isley** as part of the AI for Human Reasoning Fellowship at the Future of Life Institute (Sept-Oct 2025).

**Get in touch:**

- Email: [steve.c.isley@gmail.com](mailto:steve.c.isley@gmail.com)
- LinkedIn: [linkedin.com/in/stevecisley](https://www.linkedin.com/in/stevecisley/)

**About the Fellowship:**

- Program: [AI for Human Reasoning Fellowship](https://snazzy-cajeta-24ac71.netlify.app/)
- Organizer: [Future of Life Institute](https://www.flf.org/)

I'm happy to discuss:

- Architecture decisions and lessons learned
- Adapting this system for other platforms or use cases
- Building fact-checking-as-a-service products
- Research directions in AI-powered fact-checking

## Acknowledgments

- **Future of Life Institute** for organizing the AI for Human Reasoning Fellowship
- **X.com Community Notes team** for API access and mentorship during the fellowship

## Disclosure of AI Use

I used Claude Code to help with this project. I'm not a professional software development engineer, but I do code a lot. I'm not saying I don't stand behind the code, but I'm also not saying I carefully scrutinized every line of code...

The biggest mess is probably with the ingestion pipeline - I really should have invested the time to implement a real queueing library
