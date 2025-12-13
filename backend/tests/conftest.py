"""
Pytest configuration and shared fixtures for testing.
Provides ZeroDB test utilities, test users, and other common test utilities.
"""
import pytest
import asyncio
from typing import Dict, Any
from uuid import uuid4
from datetime import datetime
from app.services.zerodb_client import zerodb_client


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function", autouse=True)
async def setup_test_tables():
    """
    Create ZeroDB tables for testing.
    Runs automatically before each test function.
    """
    # Create all required tables
    tables_to_create = ["users", "founder_profiles", "goals", "asks", "posts", "companies", "company_roles", "introductions"]

    # Note: In a real test environment, you would create these tables
    # For now, we assume they exist from the migration
    yield

    # Cleanup: Delete all test data after each test
    # Note: We don't delete tables, just data with test markers
    try:
        # Clean up test users (those with test_ prefix in linkedin_id)
        await zerodb_client.delete_rows(
            table_name="users",
            filter={"linkedin_id": {"$regex": "^test_"}}
        )
    except Exception:
        pass  # Ignore cleanup errors


@pytest.fixture
async def test_user() -> Dict[str, Any]:
    """Create a test user for testing."""
    user_id = str(uuid4())
    now = datetime.utcnow().isoformat()

    user_data = {
        "id": user_id,
        "linkedin_id": f"test_{uuid4()}",
        "name": "Test Founder",
        "email": "test@publicfounders.com",
        "headline": "CEO at TestCo",
        "location": "San Francisco, CA",
        "phone_number": None,
        "phone_verified": False,
        "profile_picture_url": None,
        "created_at": now,
        "updated_at": now
    }

    await zerodb_client.insert_rows(table_name="users", rows=[user_data])
    return user_data


@pytest.fixture
async def test_user_2() -> Dict[str, Any]:
    """Create a second test user for relationship testing."""
    user_id = str(uuid4())
    now = datetime.utcnow().isoformat()

    user_data = {
        "id": user_id,
        "linkedin_id": f"test_{uuid4()}",
        "name": "Second Founder",
        "email": "test2@publicfounders.com",
        "headline": "CTO at TestCo",
        "location": "New York, NY",
        "phone_number": None,
        "phone_verified": False,
        "profile_picture_url": None,
        "created_at": now,
        "updated_at": now
    }

    await zerodb_client.insert_rows(table_name="users", rows=[user_data])
    return user_data


@pytest.fixture
async def test_goal(test_user: Dict[str, Any]) -> Dict[str, Any]:
    """Create a test goal."""
    from app.models.goal import GoalType

    goal_id = str(uuid4())
    now = datetime.utcnow().isoformat()

    goal_data = {
        "id": goal_id,
        "user_id": test_user["id"],
        "type": GoalType.FUNDRAISING.value,
        "description": "Raise $2M seed round by Q2 2025",
        "priority": 10,
        "is_active": True,
        "embedding_id": None,
        "created_at": now,
        "updated_at": now
    }

    await zerodb_client.insert_rows(table_name="goals", rows=[goal_data])
    return goal_data


@pytest.fixture
async def test_ask(test_user: Dict[str, Any], test_goal: Dict[str, Any]) -> Dict[str, Any]:
    """Create a test ask."""
    from app.models.ask import AskUrgency, AskStatus

    ask_id = str(uuid4())
    now = datetime.utcnow().isoformat()

    ask_data = {
        "id": ask_id,
        "user_id": test_user["id"],
        "goal_id": test_goal["id"],
        "description": "Need warm intros to tier 1 VCs",
        "urgency": AskUrgency.HIGH.value,
        "status": AskStatus.OPEN.value,
        "fulfilled_at": None,
        "embedding_id": None,
        "created_at": now,
        "updated_at": now
    }

    await zerodb_client.insert_rows(table_name="asks", rows=[ask_data])
    return ask_data


@pytest.fixture
async def test_post(test_user: Dict[str, Any]) -> Dict[str, Any]:
    """Create a test post."""
    from app.models.post import PostType

    post_id = str(uuid4())
    now = datetime.utcnow().isoformat()

    post_data = {
        "id": post_id,
        "user_id": test_user["id"],
        "type": PostType.MILESTONE.value,
        "content": "Just closed our first enterprise customer! $50k ARR.",
        "is_cross_posted": True,
        "embedding_status": "pending",
        "embedding_created_at": None,
        "embedding_error": None,
        "embedding_id": None,
        "created_at": now,
        "updated_at": now
    }

    await zerodb_client.insert_rows(table_name="posts", rows=[post_data])
    return post_data


@pytest.fixture
def mock_embedding_vector():
    """Mock 384-dimension embedding vector for testing (updated from 1536)."""
    return [0.1] * 384


@pytest.fixture
def mock_zerodb_response():
    """Mock ZeroDB API response."""
    return {
        "vector_id": "test_vector_123",
        "status": "success"
    }


@pytest.fixture
def mock_ainative_response(mock_embedding_vector):
    """Mock AINative API response (replaced OpenAI)."""
    return {
        "embeddings": [mock_embedding_vector],
        "model": "BAAI/bge-small-en-v1.5",
        "dimensions": 384
    }
