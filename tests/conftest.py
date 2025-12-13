"""
Pytest configuration and shared fixtures.
"""
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from httpx import AsyncClient

from backend.app.main import app
from backend.app.core.database import Base, get_db
from backend.app.core.config import settings


# Test database URL (use in-memory SQLite for tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "linkedin_id": "test-linkedin-123",
        "name": "Test Founder",
        "headline": "CEO at TestCorp",
        "email": "test@example.com",
        "location": "San Francisco, CA"
    }


@pytest.fixture
def sample_founder_profile_data():
    """Sample founder profile data for testing."""
    return {
        "bio": "Experienced founder building in AI/ML",
        "current_focus": "Raising seed round for AI SaaS product",
        "autonomy_mode": "suggest",
        "public_visibility": True
    }


@pytest.fixture
def sample_goal_data():
    """Sample goal data for testing."""
    return {
        "type": "fundraising",
        "description": "Raise $2M seed round for AI platform",
        "priority": 8,
        "is_active": True
    }


@pytest.fixture
def sample_ask_data():
    """Sample ask data for testing."""
    return {
        "description": "Need intro to AI-focused VCs in Bay Area",
        "urgency": "high",
        "status": "open"
    }


@pytest.fixture
def sample_company_data():
    """Sample company data for testing."""
    return {
        "name": "TestCorp AI",
        "description": "AI-powered platform for founders",
        "stage": "seed",
        "industry": "AI/ML",
        "website": "https://testcorp.ai"
    }


@pytest.fixture
def sample_post_data():
    """Sample post data for testing."""
    return {
        "type": "progress",
        "content": "Just shipped our MVP! 100 users in first week.",
        "is_cross_posted": False
    }


@pytest.fixture
def sample_introduction_data():
    """Sample introduction data for testing."""
    return {
        "agent_initiated": True,
        "channel": "linkedin",
        "rationale": "Both founders working on AI infrastructure, complementary expertise",
        "status": "proposed"
    }
