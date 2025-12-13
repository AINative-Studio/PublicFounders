# PublicFounders

**A semantic AI founder network powered by LinkedIn data, AI-native agents, and ZeroDB's vector intelligence.**

PublicFounders is a build-in-public platform that uses AI agents to intelligently connect founders, facilitate introductions, and accelerate growth through semantic matching.

## Architecture Overview

### Tech Stack

- **Backend Framework**: Python 3.9+ with FastAPI
- **Database**: PostgreSQL 15+ (relational data)
- **Vector Store**: ZeroDB (semantic embeddings)
- **Authentication**: LinkedIn OAuth 2.0
- **Testing**: pytest with 80% minimum coverage
- **Code Quality**: Ruff, Black, MyPy, pre-commit hooks
- **CI/CD**: GitHub Actions

### Design Philosophy

PublicFounders implements a **dual-layer data model**:

1. **Relational Layer** (PostgreSQL): Source of truth for deterministic, auditable data
2. **Vector Layer** (ZeroDB): Intelligence layer for semantic matching and AI agent decision-making

## Quick Start

### Prerequisites

- Python 3.9 or higher
- PostgreSQL 15 or higher
- Git

### Installation

1. **Clone the repository**:
```bash
git clone https://github.com/AINative-Studio/PublicFounders.git
cd PublicFounders
```

2. **Create and activate virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development
```

4. **Set up environment variables**:
```bash
cp .env.example .env
# Edit .env with your actual credentials
```

5. **Set up PostgreSQL database**:
```bash
createdb publicfounders
```

6. **Run database migrations**:
```bash
cd backend
alembic upgrade head
```

7. **Install pre-commit hooks** (recommended for development):
```bash
pre-commit install
```

### Running the Application

**Development server**:
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Access the API**:
- API Documentation: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc
- Health Check: http://localhost:8000/health

## Testing

### Run All Tests

```bash
cd backend
pytest
```

### Run with Coverage Report

```bash
pytest --cov=app --cov-report=html --cov-report=term-missing
```

Coverage reports are generated in `htmlcov/index.html`.

### Run Specific Test Types

```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# E2E tests only
pytest -m e2e
```

### Coverage Requirements

This project enforces **80% minimum test coverage**. PRs that drop coverage below this threshold will fail CI checks.

## Development Workflow

### Code Quality Tools

**Linting and Formatting**:
```bash
# Run Ruff linter
ruff check backend/app tests

# Auto-fix issues
ruff check --fix backend/app tests

# Format code with Ruff
ruff format backend/app tests
```

**Type Checking**:
```bash
mypy backend/app --ignore-missing-imports
```

**Security Scanning**:
```bash
bandit -r backend/app
```

### Pre-commit Hooks

Pre-commit hooks automatically run on every commit:
- Trailing whitespace removal
- End-of-file fixer
- YAML/JSON validation
- Ruff linting and formatting
- MyPy type checking
- Pytest with coverage check

**Bypass hooks** (not recommended):
```bash
git commit --no-verify
```

### Database Migrations

**Create a new migration**:
```bash
cd backend
alembic revision --autogenerate -m "Description of changes"
```

**Apply migrations**:
```bash
alembic upgrade head
```

**Rollback migrations**:
```bash
alembic downgrade -1  # Rollback one migration
alembic downgrade base  # Rollback all migrations
```

## Project Structure

```
PublicFounders/
├── backend/
│   ├── alembic/                 # Database migrations
│   │   └── versions/            # Migration files
│   ├── app/
│   │   ├── api/                 # API endpoints
│   │   │   └── v1/
│   │   │       └── endpoints/   # Route handlers
│   │   ├── core/                # Core configuration
│   │   │   ├── config.py        # Settings management
│   │   │   └── database.py      # Database setup
│   │   ├── models/              # SQLAlchemy models
│   │   ├── schemas/             # Pydantic schemas
│   │   ├── services/            # Business logic
│   │   │   ├── embedding_service.py
│   │   │   └── zerodb_service.py
│   │   └── main.py              # FastAPI app entry point
│   ├── alembic.ini              # Alembic configuration
│   └── pytest.ini               # Pytest configuration
├── tests/
│   ├── conftest.py              # Shared test fixtures
│   ├── unit/                    # Unit tests
│   ├── integration/             # Integration tests
│   └── e2e/                     # End-to-end tests
├── .env                         # Environment variables (not in git)
├── .env.example                 # Example environment file
├── .pre-commit-config.yaml      # Pre-commit hooks config
├── pyproject.toml               # Python project configuration
├── requirements.txt             # Production dependencies
├── requirements-dev.txt         # Development dependencies
└── README.md                    # This file
```

## Data Model

### Relational Tables (PostgreSQL)

- **users**: Core user authentication and profile
- **founder_profiles**: Founder-specific data and preferences
- **companies**: Company information
- **company_roles**: User-company relationships
- **goals**: Founder goals and intentions
- **asks**: Specific help requests
- **posts**: Build-in-public content
- **introductions**: AI-facilitated connections
- **interaction_outcomes**: Introduction results for RLHF

### Vector Collections (ZeroDB)

- **founder_embeddings**: Semantic founder profiles
- **goal_embeddings**: Intent-aware goal vectors
- **ask_embeddings**: Help request embeddings
- **post_embeddings**: Content discovery vectors
- **introduction_embeddings**: Connection rationale
- **interaction_embeddings**: Outcome patterns
- **agent_memory_embeddings**: AI learning memory

## Sprint Plan

This project follows an agile sprint methodology:

- **Sprint 0** (Foundation Setup): Database, API, testing framework ✅
- **Sprint 1**: Authentication, LinkedIn OAuth, profile management
- **Sprint 2**: Goals, asks, and posts
- **Sprint 3**: Semantic intelligence and embeddings
- **Sprint 4**: Virtual advisor and intro suggestions
- **Sprint 5**: Introduction execution and outcomes
- **Sprint 6**: Feed and discovery
- **Sprint 7**: Permissions, audit, and safety
- **Sprint 8**: KPI tracking and reporting

See [sprintplan.md](sprintplan.md) for detailed sprint breakdown.

## API Documentation

### Health Check

**GET** `/health`

Returns API health status and version information.

```json
{
  "status": "healthy",
  "service": "PublicFounders API",
  "version": "1.0.0",
  "environment": "development"
}
```

### API Endpoints (Sprint 1+)

- `/api/v1/auth/*` - Authentication endpoints
- `/api/v1/profile/*` - Profile management
- `/api/v1/goals/*` - Goal CRUD operations
- `/api/v1/asks/*` - Ask management
- `/api/v1/posts/*` - Content posting
- `/api/v1/introductions/*` - Introduction workflows

Full API documentation available at `/api/docs` when running the server.

## Environment Variables

See `.env.example` for all required environment variables. Key variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `ZERODB_API_KEY` | ZeroDB API key | Yes |
| `ZERODB_PROJECT_ID` | ZeroDB project identifier | Yes |
| `OPENAI_API_KEY` | OpenAI API key for embeddings | Yes |
| `LINKEDIN_CLIENT_ID` | LinkedIn OAuth client ID | Sprint 1+ |
| `LINKEDIN_CLIENT_SECRET` | LinkedIn OAuth secret | Sprint 1+ |
| `JWT_SECRET_KEY` | JWT signing key (change in prod!) | Yes |

## CI/CD Pipeline

GitHub Actions automatically run on all PRs and pushes to `main`/`develop`:

1. **Lint Check**: Ruff linting and formatting
2. **Type Check**: MyPy static analysis
3. **Tests**: Full test suite with 80% coverage requirement
4. **Security Scan**: Bandit security analysis
5. **Build Check**: Verify application builds

## Contributing

1. Create a feature branch from `develop`
2. Make your changes following code standards
3. Ensure all tests pass and coverage >= 80%
4. Submit a pull request to `develop`

## License

Copyright (c) 2025 AINative Studio. All rights reserved.

See [LICENSE](LICENSE) for details.

## Support

For issues and questions:
- GitHub Issues: https://github.com/AINative-Studio/PublicFounders/issues
- Documentation: See `docs/` directory
- Email: support@ainative.studio

---

**Built with**:  heart: **by the AINative team**
