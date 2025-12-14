"""
Pytest configuration and shared fixtures
Provides ZeroDB mocks, client, and authentication fixtures for testing
"""
import asyncio
import pytest
import uuid
from typing import AsyncGenerator, Generator
from datetime import datetime, timedelta
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch

from app.main import app
from app.core.enums import AutonomyMode


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_zerodb():
    """
    Mock ZeroDB client for testing
    Provides common database operations as async mocks
    """
    with patch('app.services.zerodb_client.zerodb_client') as mock:
        # Configure mock methods
        mock.insert_rows = AsyncMock(return_value={"success": True, "inserted": 1})
        mock.query_rows = AsyncMock(return_value=[])
        mock.update_rows = AsyncMock(return_value={"success": True, "updated": 1})
        mock.delete_rows = AsyncMock(return_value={"success": True, "deleted": 1})
        mock.get_by_id = AsyncMock(return_value=None)
        mock.get_by_field = AsyncMock(return_value=None)
        yield mock


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create test client"""
    async with AsyncClient(app=app, base_url="http://test") as test_client:
        yield test_client


@pytest.fixture
def sample_user_dict() -> dict:
    """Create a sample user dictionary for testing"""
    user_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    return {
        "id": user_id,
        "linkedin_id": "linkedin_12345",
        "name": "John Doe",
        "headline": "Founder & CEO at TechStartup",
        "profile_picture_url": "https://example.com/photo.jpg",
        "location": "San Francisco, CA",
        "email": "john.doe@example.com",
        "phone_number": "+14155551234",
        "phone_verified": False,
        "phone_verification_code": None,
        "phone_verification_expires_at": None,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
        "last_login_at": None
    }


@pytest.fixture
def sample_user_with_profile_dict() -> tuple[dict, dict]:
    """Create a sample user with founder profile as dictionaries"""
    user_id = str(uuid.uuid4())
    profile_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    user = {
        "id": user_id,
        "linkedin_id": "linkedin_67890",
        "name": "Jane Smith",
        "headline": "Serial Entrepreneur | AI Enthusiast",
        "profile_picture_url": "https://example.com/jane.jpg",
        "location": "New York, NY",
        "email": "jane.smith@example.com",
        "phone_number": "+12125555678",
        "phone_verified": True,
        "phone_verification_code": None,
        "phone_verification_expires_at": None,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
        "last_login_at": None
    }

    profile = {
        "id": profile_id,
        "user_id": user_id,
        "bio": "Building the future of AI-powered networking for founders.",
        "current_focus": "Raising seed round for SaaS platform",
        "autonomy_mode": AutonomyMode.SUGGEST.value,
        "public_visibility": True,
        "embedding_id": None,
        "created_at": now,
        "updated_at": now
    }

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


@pytest.fixture
def sample_user_with_profile_and_agent_dict() -> tuple[dict, dict, dict]:
    """Create a sample user with founder profile and advisor agent as dictionaries"""
    from app.models.advisor_agent import AgentStatus

    user_id = str(uuid.uuid4())
    agent_id = str(uuid.uuid4())
    profile_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    user = {
        "id": user_id,
        "linkedin_id": "linkedin_agent_test",
        "name": "Agent Test User",
        "headline": "Founder Testing Agent",
        "email": "agent.test@example.com",
        "is_active": True,
        "created_at": now,
        "updated_at": now
    }

    profile = {
        "id": profile_id,
        "user_id": user_id,
        "bio": "Testing advisor agent functionality",
        "current_focus": "Building AI-powered features",
        "autonomy_mode": AutonomyMode.SUGGEST.value,
        "public_visibility": True,
        "created_at": now,
        "updated_at": now
    }

    agent = {
        "id": agent_id,
        "user_id": user_id,
        "status": AgentStatus.ACTIVE.value,
        "name": "Test Advisor",
        "memory_namespace": f"agent_{user_id}",
        "total_memories": 0,
        "total_suggestions": 0,
        "total_actions": 0,
        "is_enabled": True,
        "created_at": now,
        "updated_at": now,
        "last_memory_at": None,
        "last_active_at": None,
        "last_summary_at": None
    }

    return user, profile, agent


@pytest.fixture
def mock_zerodb_client():
    """
    Mock ZeroDB client for advisor agent and autonomy controls testing
    Patches multiple services that use zerodb_client
    """
    with patch('app.services.advisor_agent_service.zerodb_client') as mock_advisor, \
         patch('app.services.autonomy_controls_service.zerodb_client') as mock_autonomy:
        # Configure mock methods for both patches
        for mock in [mock_advisor, mock_autonomy]:
            mock.insert_rows = AsyncMock(return_value={"success": True, "inserted": 1})
            mock.query_rows = AsyncMock(return_value=[])
            mock.update_rows = AsyncMock(return_value={"success": True, "updated": 1})
            mock.delete_rows = AsyncMock(return_value={"success": True, "deleted": 1})
            mock.get_by_id = AsyncMock(return_value=None)
            mock.get_by_field = AsyncMock(return_value=None)

        # Return the autonomy mock as primary (tests can configure either)
        yield mock_autonomy


@pytest.fixture
def mock_zerodb_vector_service():
    """
    Mock ZeroDB vector service for advisor agent testing
    """
    with patch('app.services.advisor_agent_service.zerodb_service') as mock:
        mock.upsert_vector = AsyncMock(return_value="vec_test_123")
        mock.search_vectors = AsyncMock(return_value=[])
        mock.prepare_metadata = lambda **kwargs: kwargs
        yield mock


@pytest.fixture
def mock_embedding_service():
    """
    Mock embedding service for advisor agent testing
    """
    with patch('app.services.advisor_agent_service.embedding_service') as mock:
        mock.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
        yield mock
