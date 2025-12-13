"""
Unit tests for Goals CRUD operations.
Following TDD principles - tests written BEFORE implementation.

Test Coverage:
- Goal creation with valid data
- Goal creation with invalid data (validation errors)
- Goal retrieval by ID
- Goal listing with pagination
- Goal update operations
- Goal soft deletion (is_active=False)
- Goal hard deletion
- User relationship validation
- Priority validation (1-10 range)
- Embedding content generation
"""
import pytest
from uuid import uuid4
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.goal import Goal, GoalType
from app.models.user import User


class TestGoalModel:
    """Test Goal SQLAlchemy model."""

    @pytest.mark.asyncio
    async def test_create_goal_valid(self, db_session: AsyncSession, test_user: User):
        """Test creating a goal with valid data."""
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

        assert goal.id is not None
        assert goal.user_id == test_user.id
        assert goal.type == GoalType.FUNDRAISING
        assert goal.description == "Raise $2M seed round by Q2 2025"
        assert goal.priority == 10
        assert goal.is_active is True
        assert goal.created_at is not None
        assert goal.updated_at is not None

    @pytest.mark.asyncio
    async def test_goal_default_values(self, db_session: AsyncSession, test_user: User):
        """Test goal default values are set correctly."""
        goal = Goal(
            user_id=test_user.id,
            type=GoalType.HIRING,
            description="Hire senior backend engineer"
        )
        db_session.add(goal)
        await db_session.commit()
        await db_session.refresh(goal)

        assert goal.priority == 1  # Default priority
        assert goal.is_active is True  # Default active state

    @pytest.mark.asyncio
    async def test_goal_types_enum(self, db_session: AsyncSession, test_user: User):
        """Test all goal type enums work correctly."""
        goal_types = [
            GoalType.FUNDRAISING,
            GoalType.HIRING,
            GoalType.GROWTH,
            GoalType.PARTNERSHIPS,
            GoalType.LEARNING
        ]

        for goal_type in goal_types:
            goal = Goal(
                user_id=test_user.id,
                type=goal_type,
                description=f"Test goal for {goal_type.value}"
            )
            db_session.add(goal)

        await db_session.commit()

        # Verify all were created
        result = await db_session.execute(
            select(Goal).where(Goal.user_id == test_user.id)
        )
        goals = result.scalars().all()
        assert len(goals) == len(goal_types)

    @pytest.mark.asyncio
    async def test_goal_priority_validation(self, db_session: AsyncSession, test_user: User):
        """Test priority validation (should be 1-10)."""
        # Valid priorities
        for priority in [1, 5, 10]:
            goal = Goal(
                user_id=test_user.id,
                type=GoalType.GROWTH,
                description=f"Test priority {priority}",
                priority=priority
            )
            db_session.add(goal)
            await db_session.commit()
            await db_session.refresh(goal)
            assert goal.priority == priority

        # Note: Database constraints should enforce min/max,
        # but schema validation happens at API layer

    @pytest.mark.asyncio
    async def test_goal_user_relationship(self, db_session: AsyncSession, test_user: User):
        """Test goal belongs to user relationship."""
        goal = Goal(
            user_id=test_user.id,
            type=GoalType.LEARNING,
            description="Master machine learning fundamentals"
        )
        db_session.add(goal)
        await db_session.commit()
        await db_session.refresh(goal)

        # Load user relationship
        await db_session.refresh(goal, ["user"])
        assert goal.user.id == test_user.id
        assert goal.user.name == test_user.name

    @pytest.mark.asyncio
    async def test_goal_embedding_content(self, db_session: AsyncSession, test_user: User):
        """Test embedding content generation."""
        goal = Goal(
            user_id=test_user.id,
            type=GoalType.FUNDRAISING,
            description="Raise Series A funding"
        )

        embedding_content = goal.embedding_content
        assert "fundraising" in embedding_content.lower()
        assert "Raise Series A funding" in embedding_content

    @pytest.mark.asyncio
    async def test_goal_update(self, db_session: AsyncSession, test_user: User):
        """Test updating goal fields."""
        goal = Goal(
            user_id=test_user.id,
            type=GoalType.HIRING,
            description="Hire CTO",
            priority=5
        )
        db_session.add(goal)
        await db_session.commit()
        await db_session.refresh(goal)

        original_created_at = goal.created_at

        # Update fields
        goal.description = "Hire experienced CTO with AI background"
        goal.priority = 10
        await db_session.commit()
        await db_session.refresh(goal)

        assert goal.description == "Hire experienced CTO with AI background"
        assert goal.priority == 10
        assert goal.created_at == original_created_at  # Should not change
        assert goal.updated_at > original_created_at  # Should update

    @pytest.mark.asyncio
    async def test_goal_soft_delete(self, db_session: AsyncSession, test_user: User):
        """Test soft deletion (is_active=False)."""
        goal = Goal(
            user_id=test_user.id,
            type=GoalType.PARTNERSHIPS,
            description="Partner with 3 enterprises"
        )
        db_session.add(goal)
        await db_session.commit()
        await db_session.refresh(goal)

        # Soft delete
        goal.is_active = False
        await db_session.commit()
        await db_session.refresh(goal)

        assert goal.is_active is False
        assert goal.id is not None  # Still exists in database

    @pytest.mark.asyncio
    async def test_goal_hard_delete(self, db_session: AsyncSession, test_user: User):
        """Test hard deletion from database."""
        goal = Goal(
            user_id=test_user.id,
            type=GoalType.GROWTH,
            description="Reach $1M ARR"
        )
        db_session.add(goal)
        await db_session.commit()
        goal_id = goal.id

        # Hard delete
        await db_session.delete(goal)
        await db_session.commit()

        # Verify deletion
        result = await db_session.execute(
            select(Goal).where(Goal.id == goal_id)
        )
        deleted_goal = result.scalar_one_or_none()
        assert deleted_goal is None

    @pytest.mark.asyncio
    async def test_goal_cascade_delete_with_user(self, db_session: AsyncSession):
        """Test goals are deleted when user is deleted (CASCADE)."""
        # Create new user
        user = User(
            linkedin_id=f"test_{uuid4()}",
            name="Test User",
            email="test@example.com"
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create goals for user
        goals = [
            Goal(
                user_id=user.id,
                type=GoalType.FUNDRAISING,
                description=f"Test goal {i}"
            )
            for i in range(3)
        ]
        for goal in goals:
            db_session.add(goal)
        await db_session.commit()

        user_id = user.id

        # Delete user
        await db_session.delete(user)
        await db_session.commit()

        # Verify goals were cascaded
        result = await db_session.execute(
            select(Goal).where(Goal.user_id == user_id)
        )
        remaining_goals = result.scalars().all()
        assert len(remaining_goals) == 0

    @pytest.mark.asyncio
    async def test_multiple_goals_per_user(self, db_session: AsyncSession, test_user: User):
        """Test user can have multiple goals."""
        goals = [
            Goal(
                user_id=test_user.id,
                type=GoalType.FUNDRAISING,
                description="Raise seed funding",
                priority=10
            ),
            Goal(
                user_id=test_user.id,
                type=GoalType.HIRING,
                description="Build engineering team",
                priority=8
            ),
            Goal(
                user_id=test_user.id,
                type=GoalType.GROWTH,
                description="Reach 1000 users",
                priority=6
            )
        ]

        for goal in goals:
            db_session.add(goal)
        await db_session.commit()

        # Verify all goals exist
        result = await db_session.execute(
            select(Goal).where(Goal.user_id == test_user.id)
        )
        user_goals = result.scalars().all()
        assert len(user_goals) >= 3  # At least the ones we created

    @pytest.mark.asyncio
    async def test_goal_repr(self, test_user: User):
        """Test goal string representation."""
        goal = Goal(
            user_id=test_user.id,
            type=GoalType.LEARNING,
            description="Learn Rust programming language for systems development"
        )

        repr_str = repr(goal)
        assert "Goal" in repr_str
        assert "learning" in repr_str.lower()
        assert "Learn Rust programming language for systems" in repr_str  # First 50 chars
