# Contributing to PublicFounders

Thank you for your interest in contributing to PublicFounders! This guide will help you get started with development using our ZeroDB-powered architecture.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Development Setup](#development-setup)
3. [ZeroDB Development Workflow](#zerodb-development-workflow)
4. [Code Standards](#code-standards)
5. [Testing Guidelines](#testing-guidelines)
6. [Submitting Changes](#submitting-changes)
7. [Common Tasks](#common-tasks)

---

## Getting Started

### Prerequisites

- Python 3.9 or higher
- Git
- ZeroDB account (sign up at https://zerodb.ai)
- OpenAI API key (for embeddings)
- Code editor (VS Code recommended)

### First Time Setup

1. **Fork the repository** on GitHub

2. **Clone your fork**:
```bash
git clone https://github.com/YOUR_USERNAME/PublicFounders.git
cd PublicFounders
```

3. **Add upstream remote**:
```bash
git remote add upstream https://github.com/AINative-Studio/PublicFounders.git
```

4. **Create virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

5. **Install dependencies**:
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

6. **Set up environment variables**:
```bash
# Copy example and edit
cp .env.example .env

# Add your credentials
ZERODB_API_KEY=your_dev_api_key
ZERODB_PROJECT_ID=your_dev_project_id
OPENAI_API_KEY=your_openai_key
JWT_SECRET_KEY=dev-secret-key-change-in-production
```

7. **Install pre-commit hooks**:
```bash
pre-commit install
```

8. **Verify setup**:
```bash
cd backend
python -c "from app.services.zerodb_client import zerodb_client; print('ZeroDB client loaded successfully')"
```

---

## Development Setup

### Development Environment

**No PostgreSQL needed!** PublicFounders uses ZeroDB for all data operations.

### Running the Development Server

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Access the application:
- **API Docs**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc
- **Health Check**: http://localhost:8000/health

### Project Structure

```
PublicFounders/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       └── endpoints/    # API route handlers
│   │   ├── core/                 # Configuration
│   │   ├── models/               # Pydantic models (validation)
│   │   ├── schemas/              # Request/response schemas
│   │   ├── services/             # Business logic
│   │   │   ├── zerodb_client.py  # Database client
│   │   │   ├── auth_service.py
│   │   │   ├── profile_service.py
│   │   │   └── embedding_service.py
│   │   └── main.py               # FastAPI app
│   └── tests/                    # Test suite
├── .env                          # Environment variables (not in git)
├── requirements.txt              # Production dependencies
└── requirements-dev.txt          # Development dependencies
```

---

## ZeroDB Development Workflow

### No Migrations!

Unlike traditional databases, ZeroDB uses schema-less NoSQL tables. You don't need to:
- Create migrations
- Run `alembic upgrade`
- Manage database schema changes

Simply update your code and the data structure adapts automatically!

### Working with Data

#### Creating Records

```python
from app.services.zerodb_client import zerodb_client
from uuid import uuid4
from datetime import datetime

# Insert a record
async def create_user(email: str, name: str):
    user_data = {
        "id": str(uuid4()),
        "email": email,
        "name": name,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }

    result = await zerodb_client.insert_rows("users", [user_data])
    return result["inserted_ids"][0]
```

#### Querying Records

```python
# Find by ID
user = await zerodb_client.get_by_id("users", user_id)

# Find by field
users = await zerodb_client.get_by_field("users", "email", "founder@example.com")

# Complex queries (MongoDB-style)
active_founders = await zerodb_client.query_rows(
    "founder_profiles",
    filter={"is_active": True, "autonomy_mode": "auto"},
    limit=10,
    sort={"created_at": -1}  # -1 for descending
)
```

#### Updating Records

```python
# Update by filter
await zerodb_client.update_rows(
    "users",
    filter={"id": user_id},
    update={"$set": {"name": "New Name", "updated_at": datetime.utcnow().isoformat()}}
)
```

#### Deleting Records

```python
# Delete by filter
await zerodb_client.delete_rows(
    "posts",
    filter={"user_id": user_id, "is_draft": True}
)
```

### Adding Vector Embeddings

```python
from app.services.embedding_service import EmbeddingService

# Generate and store embedding
embedding_service = EmbeddingService()

# For goals
vector_id = await embedding_service.create_goal_embedding(
    goal_id=goal_id,
    content=f"{goal_type}: {goal_description}",
    metadata={"priority": 8, "user_id": user_id}
)

# Update goal with embedding reference
await zerodb_client.update_rows(
    "goals",
    filter={"id": goal_id},
    update={"$set": {"embedding_id": vector_id}}
)
```

### Semantic Search

```python
# Search by similarity
similar_goals = await embedding_service.search_similar_goals(
    query_text="Looking for seed funding",
    limit=10,
    threshold=0.7  # Minimum similarity score
)
```

---

## Code Standards

### Python Style Guide

We follow **PEP 8** with these tools:

#### Ruff (Linting & Formatting)

```bash
# Check code
ruff check backend/app tests

# Auto-fix issues
ruff check --fix backend/app tests

# Format code
ruff format backend/app tests
```

#### Type Checking (MyPy)

```bash
mypy backend/app --ignore-missing-imports
```

#### Security Scanning

```bash
bandit -r backend/app
```

### Code Conventions

#### 1. Use Type Hints

```python
# Good
async def get_user(user_id: str) -> Optional[Dict[str, Any]]:
    return await zerodb_client.get_by_id("users", user_id)

# Bad
async def get_user(user_id):
    return await zerodb_client.get_by_id("users", user_id)
```

#### 2. Use Pydantic for Validation

```python
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    name: str
    phone: Optional[str] = None

# FastAPI automatically validates
@router.post("/users")
async def create_user(user: UserCreate):
    # user is already validated
    ...
```

#### 3. Handle Errors Properly

```python
from fastapi import HTTPException, status

async def get_user(user_id: str):
    user = await zerodb_client.get_by_id("users", user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )

    return user
```

#### 4. Use Async/Await Consistently

```python
# Good - async all the way
async def get_profile(user_id: str):
    user = await zerodb_client.get_by_id("users", user_id)
    profiles = await zerodb_client.query_rows(
        "founder_profiles",
        filter={"user_id": user_id}
    )
    return profiles[0] if profiles else None

# Bad - blocking calls
def get_profile(user_id: str):
    # Don't use sync calls in async app
    ...
```

#### 5. Log Important Operations

```python
import logging

logger = logging.getLogger(__name__)

async def create_goal(user_id: str, goal_data: dict):
    logger.info(f"Creating goal for user {user_id}")

    try:
        result = await zerodb_client.insert_rows("goals", [goal_data])
        logger.info(f"Goal created successfully: {result['inserted_ids'][0]}")
        return result
    except Exception as e:
        logger.error(f"Failed to create goal: {e}", exc_info=True)
        raise
```

---

## Testing Guidelines

### Test Structure

```
tests/
├── conftest.py           # Shared fixtures
├── unit/                 # Unit tests (60% of tests)
│   ├── test_models.py
│   └── test_services.py
├── integration/          # Integration tests (30%)
│   ├── test_auth.py
│   └── test_profile.py
└── e2e/                  # End-to-end tests (10%)
    └── test_workflows.py
```

### Writing Tests

#### Unit Test Example

```python
import pytest
from app.services.auth_service import AuthService

@pytest.mark.unit
async def test_create_user_from_linkedin():
    """Test user creation from LinkedIn data."""
    auth_service = AuthService()

    linkedin_data = {
        "id": "linkedin123",
        "email": "founder@example.com",
        "name": "Jane Founder"
    }

    user = await auth_service.create_user_from_linkedin(linkedin_data)

    assert user["email"] == "founder@example.com"
    assert user["linkedin_id"] == "linkedin123"
    assert "id" in user
```

#### Integration Test Example

```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.integration
async def test_create_goal_endpoint():
    """Test goal creation via API endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create auth token
        token = create_test_token(user_id="test-user")

        # Create goal
        response = await client.post(
            "/api/v1/goals",
            json={
                "type": "fundraising",
                "description": "Raise $2M seed round",
                "priority": 8
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "fundraising"
        assert "id" in data
```

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=app --cov-report=html --cov-report=term-missing

# Specific test types
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m e2e          # E2E tests only

# Specific file
pytest tests/unit/test_auth.py

# Specific test
pytest tests/unit/test_auth.py::test_create_user
```

### Coverage Requirements

- **Overall**: 80% minimum
- **Services**: 85% minimum
- **API Endpoints**: 80% minimum
- **Models**: 90% minimum

```bash
# Check coverage
pytest --cov=app --cov-fail-under=80
```

### Mocking ZeroDB

For unit tests, mock the ZeroDB client:

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.unit
async def test_get_user_service():
    """Test user service with mocked ZeroDB."""

    mock_user = {
        "id": "test-id",
        "email": "test@example.com",
        "name": "Test User"
    }

    with patch('app.services.auth_service.zerodb_client') as mock_client:
        mock_client.get_by_id = AsyncMock(return_value=mock_user)

        auth_service = AuthService()
        user = await auth_service.get_user_by_id("test-id")

        assert user["email"] == "test@example.com"
        mock_client.get_by_id.assert_called_once_with("users", "test-id")
```

---

## Submitting Changes

### Branch Naming

```bash
# Features
git checkout -b feat/add-semantic-search

# Bug fixes
git checkout -b fix/auth-token-expiry

# Documentation
git checkout -b docs/update-readme

# Refactoring
git checkout -b refactor/simplify-embedding-service
```

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```bash
# Format: <type>(<scope>): <description>

# Examples:
git commit -m "feat(goals): add semantic goal matching"
git commit -m "fix(auth): handle expired LinkedIn tokens"
git commit -m "docs(readme): update ZeroDB setup instructions"
git commit -m "test(profile): add profile service unit tests"
git commit -m "refactor(api): simplify error handling"
```

### Pull Request Process

1. **Update from upstream**:
```bash
git fetch upstream
git rebase upstream/develop
```

2. **Run all checks**:
```bash
# Lint
ruff check backend/app tests

# Type check
mypy backend/app

# Tests
pytest --cov=app --cov-fail-under=80

# Security
bandit -r backend/app
```

3. **Push to your fork**:
```bash
git push origin feat/your-feature
```

4. **Create Pull Request**:
- Go to GitHub
- Click "New Pull Request"
- Select `develop` as base branch
- Fill out PR template
- Request review

### PR Checklist

- [ ] Code follows style guidelines (Ruff passes)
- [ ] Type hints added (MyPy passes)
- [ ] Tests added/updated (coverage >= 80%)
- [ ] Documentation updated
- [ ] Commits follow conventional format
- [ ] No secrets in code
- [ ] Pre-commit hooks pass

---

## Common Tasks

### Adding a New API Endpoint

**1. Create endpoint file** (if needed):
```python
# backend/app/api/v1/endpoints/new_feature.py
from fastapi import APIRouter, Depends
from app.core.security import get_current_user

router = APIRouter()

@router.post("/")
async def create_feature(
    data: FeatureCreate,
    current_user: dict = Depends(get_current_user)
):
    # Implementation
    ...
```

**2. Register router**:
```python
# backend/app/api/v1/api.py
from app.api.v1.endpoints import new_feature

api_router.include_router(
    new_feature.router,
    prefix="/new-feature",
    tags=["new-feature"]
)
```

**3. Add tests**:
```python
# tests/integration/test_new_feature.py
@pytest.mark.integration
async def test_create_feature():
    # Test implementation
    ...
```

### Adding a New Service

**1. Create service file**:
```python
# backend/app/services/new_service.py
from app.services.zerodb_client import zerodb_client
from typing import Optional, Dict, Any

class NewService:
    """Service for handling new feature logic."""

    async def create_item(self, data: dict) -> str:
        """Create a new item."""
        result = await zerodb_client.insert_rows("table_name", [data])
        return result["inserted_ids"][0]

    async def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get item by ID."""
        return await zerodb_client.get_by_id("table_name", item_id)
```

**2. Add tests**:
```python
# tests/unit/test_new_service.py
@pytest.mark.unit
async def test_create_item():
    # Test implementation
    ...
```

### Adding Semantic Search

**1. Generate embeddings**:
```python
from app.services.embedding_service import EmbeddingService

embedding_service = EmbeddingService()

# Create embedding
vector_id = await embedding_service.create_embedding(
    entity_type="custom",
    entity_id=item_id,
    content=item_text,
    metadata={"field": "value"}
)
```

**2. Search by similarity**:
```python
# Search similar items
results = await embedding_service.search_similar(
    entity_type="custom",
    query_text="search query",
    limit=10,
    threshold=0.7
)
```

### Debugging Tips

**1. Enable debug logging**:
```python
# backend/app/main.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

**2. Use FastAPI's interactive docs**:
- Go to http://localhost:8000/api/docs
- Try out endpoints directly
- See request/response schemas

**3. Check ZeroDB operations**:
```python
# Add debug logging to zerodb_client.py
logger.debug(f"Query: {filter}, Result: {result}")
```

**4. Use Python debugger**:
```python
import pdb; pdb.set_trace()  # Breakpoint
```

---

## Getting Help

### Resources

- **Documentation**: See README.md, ARCHITECTURE.md, DEPLOYMENT.md
- **API Docs**: http://localhost:8000/api/docs (when running locally)
- **ZeroDB Docs**: https://docs.zerodb.ai
- **FastAPI Docs**: https://fastapi.tiangolo.com

### Communication

- **GitHub Issues**: For bugs and feature requests
- **GitHub Discussions**: For questions and ideas
- **Email**: dev@ainative.studio

### Common Issues

**Q: ZeroDB client not connecting?**
A: Check your `.env` file has valid `ZERODB_API_KEY` and `ZERODB_PROJECT_ID`

**Q: Tests failing with "table not found"?**
A: Make sure you're using the correct ZeroDB project ID for testing

**Q: Pre-commit hooks failing?**
A: Run `ruff format backend/app tests` to auto-format code

**Q: MyPy errors?**
A: Add type hints or use `# type: ignore` for external libraries

---

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Assume good intentions
- Follow the project's technical standards

---

Thank you for contributing to PublicFounders! Every contribution helps build a better platform for founders to connect and grow.

**Happy coding!**
