# PublicFounders

**A semantic AI founder network powered by LinkedIn data, AI-native agents, and ZeroDB's vector intelligence.**

PublicFounders is a build-in-public platform that uses AI agents to intelligently connect founders, facilitate introductions, and accelerate growth through semantic matching.

## Architecture Overview

### Tech Stack

- **Backend Framework**: Python 3.9+ with FastAPI
- **Database**: ZeroDB (unified NoSQL + vector storage)
- **Authentication**: LinkedIn OAuth 2.0
- **Embeddings**: OpenAI text-embedding-3-small (1536 dimensions)
- **Testing**: pytest with 80% minimum coverage
- **Code Quality**: Ruff, Black, MyPy, pre-commit hooks
- **CI/CD**: GitHub Actions

### Design Philosophy

PublicFounders implements a **unified semantic architecture**:

**Single Platform** (ZeroDB): All data in one place - relational NoSQL tables + vector embeddings for semantic intelligence, eliminating the complexity of managing multiple databases while maintaining full auditability and AI capabilities.

## Quick Start

### Prerequisites

- Python 3.9 or higher
- ZeroDB account (sign up at https://zerodb.ai)
- OpenAI API key
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

4. **Set up ZeroDB project**:
   - Create a project at https://zerodb.ai
   - Get your API key and project ID
   - Tables are already created (8 NoSQL tables)

5. **Set up environment variables**:
```bash
# Create .env file in project root
cat > .env << EOF
# ZeroDB Configuration
ZERODB_API_KEY=your_zerodb_api_key_here
ZERODB_PROJECT_ID=your_zerodb_project_id_here

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# JWT Configuration
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=10080

# LinkedIn OAuth (optional for development)
LINKEDIN_CLIENT_ID=your_linkedin_client_id
LINKEDIN_CLIENT_SECRET=your_linkedin_client_secret
LINKEDIN_REDIRECT_URI=http://localhost:8000/api/v1/auth/linkedin/callback

# Application Settings
ENVIRONMENT=development
API_V1_PREFIX=/api/v1
PROJECT_NAME=PublicFounders
EOF
```

6. **Install pre-commit hooks** (recommended for development):
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

**No database migrations needed!** ZeroDB tables are managed directly via the API.

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

### ZeroDB Development

**No migrations needed!** ZeroDB uses schema-less NoSQL tables that adapt automatically.

**Working with data**:
```python
from app.services.zerodb_client import zerodb_client

# Insert data
await zerodb_client.insert_rows("users", [{
    "id": str(uuid4()),
    "email": "founder@example.com",
    "name": "Jane Founder"
}])

# Query data
users = await zerodb_client.query_rows(
    "users",
    filter={"email": "founder@example.com"},
    limit=10
)

# Update data
await zerodb_client.update_rows(
    "users",
    filter={"id": user_id},
    update={"$set": {"name": "New Name"}}
)
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

### ZeroDB NoSQL Tables (8 tables)

- **users**: User authentication and profile data
- **founder_profiles**: Founder-specific preferences and bio
- **companies**: Company information
- **company_roles**: User-company relationships
- **goals**: Founder goals and objectives
- **asks**: Help requests from founders
- **posts**: Build-in-public content
- **introductions**: AI-facilitated connections

### ZeroDB Vector Store

All tables automatically support vector embeddings for semantic search:
- **Founder embeddings**: Composite of bio + experience + goals
- **Goal embeddings**: Intent vectors for matching
- **Ask embeddings**: Help requests with urgency weighting
- **Post embeddings**: Content for discovery

**Key Benefit**: NoSQL data + vector embeddings in a single platform - no synchronization issues!

## Sprint Plan

This project follows an agile sprint methodology:

- **Sprint 0** (Foundation Setup): Database, API, testing framework ✅
- **Sprint 1**: Authentication, LinkedIn OAuth, profile management ✅
- **Sprint 2**: Goals, asks, and posts ✅
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

Required environment variables for PublicFounders:

| Variable | Description | Required |
|----------|-------------|----------|
| `ZERODB_API_KEY` | ZeroDB API key for database access | Yes |
| `ZERODB_PROJECT_ID` | ZeroDB project identifier | Yes |
| `OPENAI_API_KEY` | OpenAI API key for embeddings | Yes |
| `JWT_SECRET_KEY` | JWT signing key (change in prod!) | Yes |
| `JWT_ALGORITHM` | JWT algorithm (HS256) | Yes |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiry (7 days = 10080) | Yes |
| `LINKEDIN_CLIENT_ID` | LinkedIn OAuth client ID | Optional |
| `LINKEDIN_CLIENT_SECRET` | LinkedIn OAuth secret | Optional |
| `LINKEDIN_REDIRECT_URI` | OAuth callback URL | Optional |
| `ENVIRONMENT` | Environment (development/production) | Yes |

**Note**: No PostgreSQL or Redis required - everything runs on ZeroDB!

## Why ZeroDB? Key Benefits

### Simplified Architecture
- **One Platform**: NoSQL tables + vector embeddings in a single database
- **No Syncing**: Relational data and semantic vectors always in sync
- **Fewer Dependencies**: No PostgreSQL, no Redis, no connection pooling complexity

### Developer Experience
- **No Migrations**: Schema-less NoSQL adapts automatically
- **Simple API**: MongoDB-style queries, not SQL or ORM
- **Fast Development**: No database setup, just API credentials
- **Easy Testing**: Direct HTTP API calls, no database containers

### Performance & Cost
- **Lower Latency**: Direct REST API, no ORM overhead
- **Built-in Caching**: ZeroDB handles caching internally
- **Cost Effective**: Single subscription vs. multiple database services
- **Auto Scaling**: Distributed architecture handles growth

### AI-Native Features
- **Semantic Search**: Vector embeddings built-in, no separate store
- **RLHF Support**: Event streams for reinforcement learning
- **Agent Memory**: Long-term learning capabilities
- **Quantum Ready**: Future-proof for advanced AI workloads

## Troubleshooting

### Common Issues

**Issue**: `ZERODB_API_KEY not found`
- **Solution**: Make sure `.env` file exists in project root with valid API key

**Issue**: `httpx.HTTPStatusError: 401 Unauthorized`
- **Solution**: Check that your ZeroDB API key is valid and not expired

**Issue**: `Table not found` error
- **Solution**: Verify your `ZERODB_PROJECT_ID` is correct and tables are created

**Issue**: OpenAI embeddings failing
- **Solution**: Check `OPENAI_API_KEY` is valid and has available credits

**Need help?** Open an issue on GitHub or contact support@ainative.studio

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

**Built with :heart: by the AINative team**
