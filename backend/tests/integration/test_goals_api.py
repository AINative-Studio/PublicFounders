"""
Integration tests for Goals API endpoints.
Tests full request/response cycle including database and embedding service.
"""
import pytest
from uuid import uuid4
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient
from app.main import app
from app.models.user import User
from app.models.goal import Goal, GoalType
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
class TestGoalsAPI:
    """Integration tests for /api/v1/goals endpoints."""

    async def test_create_goal_success(self, client: AsyncClient, test_user: User, mock_embedding_service):
        """Test successful goal creation."""
        with patch("app.api.v1.endpoints.goals.embedding_service", mock_embedding_service):
            response = await client.post(
                "/api/v1/goals",
                json={
                    "type": "fundraising",
                    "description": "Raise $2M seed round by Q2 2025",
                    "priority": 10,
                    "is_active": True
                }
            )

        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "fundraising"
        assert data["description"] == "Raise $2M seed round by Q2 2025"
        assert data["priority"] == 10
        assert data["is_active"] is True
        assert "id" in data
        assert "user_id" in data

    async def test_create_goal_embedding_failure_does_not_block(
        self,
        client: AsyncClient,
        test_user: User
    ):
        """Test goal creation succeeds even if embedding fails."""
        with patch("app.api.v1.endpoints.goals.embedding_service") as mock_service:
            mock_service.create_goal_embedding.side_effect = Exception("Embedding service down")

            response = await client.post(
                "/api/v1/goals",
                json={
                    "type": "hiring",
                    "description": "Hire senior backend engineer",
                    "priority": 8
                }
            )

        # Goal should still be created
        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "hiring"

    async def test_list_goals_with_pagination(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test listing goals with pagination."""
        # Create multiple goals
        for i in range(5):
            goal = Goal(
                user_id=test_user.id,
                type=GoalType.GROWTH,
                description=f"Test goal {i}",
                priority=i
            )
            db_session.add(goal)
        await db_session.commit()

        # Get first page
        response = await client.get("/api/v1/goals?page=1&page_size=3")
        assert response.status_code == 200

        data = response.json()
        assert len(data["goals"]) <= 3
        assert data["page"] == 1
        assert data["page_size"] == 3
        assert data["total"] >= 5

    async def test_list_goals_filter_by_active(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test filtering goals by active status."""
        # Create active and inactive goals
        active_goal = Goal(
            user_id=test_user.id,
            type=GoalType.FUNDRAISING,
            description="Active goal",
            is_active=True
        )
        inactive_goal = Goal(
            user_id=test_user.id,
            type=GoalType.HIRING,
            description="Inactive goal",
            is_active=False
        )
        db_session.add_all([active_goal, inactive_goal])
        await db_session.commit()

        # Filter by active
        response = await client.get("/api/v1/goals?is_active=true")
        assert response.status_code == 200

        data = response.json()
        for goal in data["goals"]:
            assert goal["is_active"] is True

    async def test_get_goal_by_id(
        self,
        client: AsyncClient,
        test_goal: Goal
    ):
        """Test retrieving a specific goal."""
        response = await client.get(f"/api/v1/goals/{test_goal.id}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == str(test_goal.id)
        assert data["description"] == test_goal.description

    async def test_get_nonexistent_goal_returns_404(self, client: AsyncClient):
        """Test 404 for nonexistent goal."""
        fake_id = uuid4()
        response = await client.get(f"/api/v1/goals/{fake_id}")
        assert response.status_code == 404

    async def test_update_goal(
        self,
        client: AsyncClient,
        test_goal: Goal,
        mock_embedding_service
    ):
        """Test updating a goal."""
        with patch("app.api.v1.endpoints.goals.embedding_service", mock_embedding_service):
            response = await client.put(
                f"/api/v1/goals/{test_goal.id}",
                json={
                    "description": "Updated description",
                    "priority": 5
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated description"
        assert data["priority"] == 5

    async def test_update_goal_regenerates_embedding_if_needed(
        self,
        client: AsyncClient,
        test_goal: Goal
    ):
        """Test embedding regeneration when description changes."""
        with patch("app.api.v1.endpoints.goals.embedding_service") as mock_service:
            mock_service.create_goal_embedding = AsyncMock(return_value="new_vector_id")

            await client.put(
                f"/api/v1/goals/{test_goal.id}",
                json={"description": "Completely new description"}
            )

            # Embedding should be regenerated
            mock_service.create_goal_embedding.assert_called_once()

    async def test_delete_goal(
        self,
        client: AsyncClient,
        test_goal: Goal,
        mock_embedding_service
    ):
        """Test deleting a goal."""
        with patch("app.api.v1.endpoints.goals.embedding_service", mock_embedding_service):
            response = await client.delete(f"/api/v1/goals/{test_goal.id}")

        assert response.status_code == 204

        # Verify goal is deleted
        get_response = await client.get(f"/api/v1/goals/{test_goal.id}")
        assert get_response.status_code == 404

    async def test_validation_min_description_length(self, client: AsyncClient):
        """Test validation for minimum description length."""
        response = await client.post(
            "/api/v1/goals",
            json={
                "type": "fundraising",
                "description": "Short",  # Too short
                "priority": 5
            }
        )
        assert response.status_code == 422  # Validation error

    async def test_validation_priority_range(self, client: AsyncClient):
        """Test validation for priority range."""
        # Priority too high
        response = await client.post(
            "/api/v1/goals",
            json={
                "type": "fundraising",
                "description": "Valid description here",
                "priority": 11  # Max is 10
            }
        )
        assert response.status_code == 422

        # Priority too low
        response = await client.post(
            "/api/v1/goals",
            json={
                "type": "fundraising",
                "description": "Valid description here",
                "priority": 0  # Min is 1
            }
        )
        assert response.status_code == 422


# Fixtures for integration tests
@pytest.fixture
async def client(db_session):
    """Create async HTTP client for testing."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_embedding_service():
    """Mock embedding service for testing."""
    mock = AsyncMock()
    mock.create_goal_embedding.return_value = "test_vector_id"
    mock.delete_embedding.return_value = True
    return mock
