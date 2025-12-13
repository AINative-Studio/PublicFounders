"""
Pytest configuration and shared fixtures
Provides database, client, and authentication fixtures for testing
"""
import asyncio
import pytest
import uuid
from typing import AsyncGenerator, Generator
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.core.database import Base, get_db
from app.core.config import settings
from app.models.user import User
from app.models.founder_profile import FounderProfile, AutonomyMode
from app.main import app


# Test database URL (use in-memory SQLite or separate test database)
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/publicfounders_test"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_engine():
    """Create test database engine"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop tables after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create database session for testing"""
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
    """Create test client with database session override"""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
async def sample_user(db_session: AsyncSession) -> User:
    """Create a sample user for testing"""
    user = User(
        id=uuid.uuid4(),
        linkedin_id="linkedin_12345",
        name="John Doe",
        headline="Founder & CEO at TechStartup",
        profile_photo_url="https://example.com/photo.jpg",
        location="San Francisco, CA",
        email="john.doe@example.com",
        phone_number="+14155551234",
        phone_verified=False,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest.fixture
async def sample_user_with_profile(db_session: AsyncSession) -> tuple[User, FounderProfile]:
    """Create a sample user with founder profile"""
    user = User(
        id=uuid.uuid4(),
        linkedin_id="linkedin_67890",
        name="Jane Smith",
        headline="Serial Entrepreneur | AI Enthusiast",
        profile_photo_url="https://example.com/jane.jpg",
        location="New York, NY",
        email="jane.smith@example.com",
        phone_number="+12125555678",
        phone_verified=True,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    db_session.add(user)
    await db_session.flush()

    profile = FounderProfile(
        user_id=user.id,
        bio="Building the future of AI-powered networking for founders.",
        current_focus="Raising seed round for SaaS platform",
        autonomy_mode=AutonomyMode.SUGGEST,
        public_visibility=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(profile)

    return user, profile


@pytest.fixture
def linkedin_user_data() -> dict:
    """Sample LinkedIn OAuth user data"""
    return {
        "sub": "linkedin_abc123",
        "name": "Alex Johnson",
        "given_name": "Alex",
        "family_name": "Johnson",
        "picture": "https://media.licdn.com/dms/image/abc123/profile-displayphoto",
        "locale": "en-US",
        "email": "alex.johnson@example.com"
    }


@pytest.fixture
def valid_jwt_token() -> str:
    """Generate a valid JWT token for testing"""
    from app.core.security import create_access_token

    payload = {
        "sub": str(uuid.uuid4()),
        "linkedin_id": "linkedin_test123"
    }
    return create_access_token(payload)


@pytest.fixture
def mock_zerodb_response():
    """Mock ZeroDB API response"""
    return {
        "id": str(uuid.uuid4()),
        "status": "success",
        "vector_id": f"vec_{uuid.uuid4()}",
        "message": "Vector upserted successfully"
    }


@pytest.fixture
def mock_embedding_vector():
    """Mock 1536-dimensional embedding vector"""
    import numpy as np
    return np.random.rand(1536).tolist()
