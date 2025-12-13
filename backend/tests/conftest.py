"""
Pytest configuration and shared fixtures for testing.
Provides database session, test users, and other common test utilities.
"""
import pytest
import asyncio
from typing import AsyncGenerator
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from app.core.database import Base
from app.models.user import User
from app.models.goal import Goal
from app.models.ask import Ask
from app.models.post import Post

# Test database URL (use in-memory SQLite for fast tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
        future=True
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create database session for tests."""
    async_session = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )

    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user for testing."""
    user = User(
        linkedin_id=f"test_{uuid4()}",
        name="Test Founder",
        email="test@publicfounders.com",
        headline="CEO at TestCo",
        location="San Francisco, CA"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_user_2(db_session: AsyncSession) -> User:
    """Create a second test user for relationship testing."""
    user = User(
        linkedin_id=f"test_{uuid4()}",
        name="Second Founder",
        email="test2@publicfounders.com",
        headline="CTO at TestCo",
        location="New York, NY"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_goal(db_session: AsyncSession, test_user: User) -> Goal:
    """Create a test goal."""
    from app.models.goal import GoalType

    goal = Goal(
        user_id=test_user.id,
        type=GoalType.FUNDRAISING,
        description="Raise $2M seed round by Q2 2025",
        priority=10,
        is_active=True
    )
    db_session.add(goal)
    await db_session.commit()
    await db_session.refresh(goal)
    return goal


@pytest.fixture
async def test_ask(db_session: AsyncSession, test_user: User, test_goal: Goal) -> Ask:
    """Create a test ask."""
    from app.models.ask import AskUrgency, AskStatus

    ask = Ask(
        user_id=test_user.id,
        goal_id=test_goal.id,
        description="Need warm intros to tier 1 VCs",
        urgency=AskUrgency.HIGH,
        status=AskStatus.OPEN
    )
    db_session.add(ask)
    await db_session.commit()
    await db_session.refresh(ask)
    return ask


@pytest.fixture
async def test_post(db_session: AsyncSession, test_user: User) -> Post:
    """Create a test post."""
    from app.models.post import PostType

    post = Post(
        user_id=test_user.id,
        type=PostType.MILESTONE,
        content="Just closed our first enterprise customer! $50k ARR.",
        is_cross_posted=True
    )
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)
    return post


@pytest.fixture
def mock_embedding_vector():
    """Mock 1536-dimension embedding vector for testing."""
    return [0.1] * 1536


@pytest.fixture
def mock_zerodb_response():
    """Mock ZeroDB API response."""
    return {
        "vector_id": "test_vector_123",
        "status": "success"
    }


@pytest.fixture
def mock_openai_response(mock_embedding_vector):
    """Mock OpenAI API response."""
    return {
        "data": [{
            "embedding": mock_embedding_vector,
            "index": 0
        }],
        "model": "text-embedding-3-small",
        "usage": {
            "prompt_tokens": 10,
            "total_tokens": 10
        }
    }
