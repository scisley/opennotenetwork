# OpenNoteNetwork

Open-source AI-powered fact-checking network that generates and submits Community Notes to X.com for combating misinformation across various topics.

## Architecture

- **Backend**: FastAPI with async SQLAlchemy and PostgreSQL (Neon)
- **Frontend**: Next.js (coming soon)
- **AI**: LangGraph agents for classification and fact-checking

## Quick Start

### Backend Setup

```bash
cd api
poetry install
cp .env.example .env  # Configure your environment variables
poetry run python run.py
```

API docs available at `http://localhost:8000/api/docs`

### Key Features

- **Automated Ingestion**: Fetches posts eligible for Community Notes from X.com
- **Smart Classification**: LangGraph agents classify posts by topic (climate, politics, health, etc.) and detect misinformation
- **Fact-Check Generation**: Creates both full and concise (280-char) fact-checks
- **Review Workflow**: Admin approval system with editing capabilities
- **Auto-Classification**: New posts are automatically classified during ingestion

### Environment Variables

Required in `api/.env`:
- `DATABASE_URL`: PostgreSQL connection string
- `X_API_KEY`, `X_API_KEY_SECRET`: X.com API credentials
- `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET`: X.com OAuth tokens
- `INGEST_SECRET`: Secret for automated ingestion triggers
- `LANGGRAPH_API_KEY`: LangGraph API key

### Development

```bash
# Run linting
cd api && poetry run ruff check

# Format code
cd api && poetry run ruff format

# Type checking
cd api && poetry run mypy .
```

## License

MIT