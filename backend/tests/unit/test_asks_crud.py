"""
Unit tests for Asks CRUD operations.
Following TDD principles - tests written BEFORE implementation.

Test Coverage:
- Ask creation with and without goal linkage
- Ask urgency levels
- Ask status lifecycle
- Ask fulfillment tracking
- User relationship validation
- Goal relationship validation (nullable)
- Embedding content generation
- Status transition methods
"""
import pytest
from uuid import uuid4
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.ask import Ask, AskUrgency, AskStatus
from app.models.goal import Goal, GoalType
from app.models.user import User


class TestAskModel:
    """Test Ask SQLAlchemy model."""

    @pytest.mark.asyncio
    async def test_create_ask_without_goal(self, db_session: AsyncSession, test_user: User):
        """Test creating an ask without linking to a goal."""
        ask = Ask(
            user_id=test_user.id,
            description="Looking for introductions to seed investors",
            urgency=AskUrgency.HIGH
        )
        db_session.add(ask)
        await db_session.commit()
        await db_session.refresh(ask)

        assert ask.id is not None
        assert ask.user_id == test_user.id
        assert ask.goal_id is None
        assert ask.description == "Looking for introductions to seed investors"
        assert ask.urgency == AskUrgency.HIGH
        assert ask.status == AskStatus.OPEN  # Default status
        assert ask.created_at is not None
        assert ask.fulfilled_at is None

    @pytest.mark.asyncio
    async def test_create_ask_with_goal(self, db_session: AsyncSession, test_user: User):
        """Test creating an ask linked to a goal."""
        # Create goal first
        goal = Goal(
            user_id=test_user.id,
            type=GoalType.FUNDRAISING,
            description="Raise $2M seed round"
        )
        db_session.add(goal)
        await db_session.commit()
        await db_session.refresh(goal)

        # Create ask linked to goal
        ask = Ask(
            user_id=test_user.id,
            goal_id=goal.id,
            description="Need warm intros to tier 1 VCs",
            urgency=AskUrgency.HIGH
        )
        db_session.add(ask)
        await db_session.commit()
        await db_session.refresh(ask)

        assert ask.goal_id == goal.id
        # Load relationship
        await db_session.refresh(ask, ["goal"])
        assert ask.goal.description == "Raise $2M seed round"

    @pytest.mark.asyncio
    async def test_ask_default_values(self, db_session: AsyncSession, test_user: User):
        """Test ask default values are set correctly."""
        ask = Ask(
            user_id=test_user.id,
            description="Need help with product-market fit"
        )
        db_session.add(ask)
        await db_session.commit()
        await db_session.refresh(ask)

        assert ask.urgency == AskUrgency.MEDIUM  # Default urgency
        assert ask.status == AskStatus.OPEN  # Default status
        assert ask.fulfilled_at is None

    @pytest.mark.asyncio
    async def test_ask_urgency_levels(self, db_session: AsyncSession, test_user: User):
        """Test all urgency level enums work correctly."""
        urgency_levels = [AskUrgency.LOW, AskUrgency.MEDIUM, AskUrgency.HIGH]

        for urgency in urgency_levels:
            ask = Ask(
                user_id=test_user.id,
                description=f"Test ask with {urgency.value} urgency",
                urgency=urgency
            )
            db_session.add(ask)

        await db_session.commit()

        # Verify all were created
        result = await db_session.execute(
            select(Ask).where(Ask.user_id == test_user.id)
        )
        asks = result.scalars().all()
        assert len(asks) == len(urgency_levels)

    @pytest.mark.asyncio
    async def test_ask_status_transitions(self, db_session: AsyncSession, test_user: User):
        """Test ask status lifecycle transitions."""
        ask = Ask(
            user_id=test_user.id,
            description="Need customer discovery interviews",
            urgency=AskUrgency.MEDIUM
        )
        db_session.add(ask)
        await db_session.commit()
        await db_session.refresh(ask)

        # Initially open
        assert ask.status == AskStatus.OPEN
        assert ask.fulfilled_at is None

        # Mark as fulfilled
        ask.mark_fulfilled()
        await db_session.commit()
        await db_session.refresh(ask)

        assert ask.status == AskStatus.FULFILLED
        assert ask.fulfilled_at is not None
        assert isinstance(ask.fulfilled_at, datetime)

    @pytest.mark.asyncio
    async def test_ask_mark_closed_without_fulfillment(self, db_session: AsyncSession, test_user: User):
        """Test marking ask as closed without fulfillment."""
        ask = Ask(
            user_id=test_user.id,
            description="Looking for design feedback",
            urgency=AskUrgency.LOW
        )
        db_session.add(ask)
        await db_session.commit()
        await db_session.refresh(ask)

        # Mark as closed (not fulfilled)
        ask.mark_closed()
        await db_session.commit()
        await db_session.refresh(ask)

        assert ask.status == AskStatus.CLOSED
        assert ask.fulfilled_at is None  # No fulfillment timestamp

    @pytest.mark.asyncio
    async def test_ask_user_relationship(self, db_session: AsyncSession, test_user: User):
        """Test ask belongs to user relationship."""
        ask = Ask(
            user_id=test_user.id,
            description="Need beta testers for SaaS product"
        )
        db_session.add(ask)
        await db_session.commit()
        await db_session.refresh(ask)

        # Load user relationship
        await db_session.refresh(ask, ["user"])
        assert ask.user.id == test_user.id
        assert ask.user.name == test_user.name

    @pytest.mark.asyncio
    async def test_ask_embedding_content_with_urgency(self, test_user: User):
        """Test embedding content generation includes urgency for high/low."""
        # High urgency ask
        high_urgency_ask = Ask(
            user_id=test_user.id,
            description="Need legal counsel ASAP",
            urgency=AskUrgency.HIGH
        )
        assert "[HIGH]" in high_urgency_ask.embedding_content
        assert "Need legal counsel ASAP" in high_urgency_ask.embedding_content

        # Low urgency ask
        low_urgency_ask = Ask(
            user_id=test_user.id,
            description="Looking for mentorship opportunities",
            urgency=AskUrgency.LOW
        )
        assert "[LOW]" in low_urgency_ask.embedding_content

        # Medium urgency (no prefix)
        medium_urgency_ask = Ask(
            user_id=test_user.id,
            description="Seeking product feedback",
            urgency=AskUrgency.MEDIUM
        )
        assert "[MEDIUM]" not in medium_urgency_ask.embedding_content
        assert "Seeking product feedback" in medium_urgency_ask.embedding_content

    @pytest.mark.asyncio
    async def test_ask_goal_relationship_nullable(self, db_session: AsyncSession, test_user: User):
        """Test goal relationship is nullable (optional)."""
        # Create ask without goal
        ask = Ask(
            user_id=test_user.id,
            description="General advice needed"
        )
        db_session.add(ask)
        await db_session.commit()
        await db_session.refresh(ask)

        assert ask.goal_id is None
        await db_session.refresh(ask, ["goal"])
        assert ask.goal is None

    @pytest.mark.asyncio
    async def test_ask_goal_set_null_on_delete(self, db_session: AsyncSession, test_user: User):
        """Test goal_id is set to NULL when goal is deleted (SET NULL)."""
        # Create goal and ask
        goal = Goal(
            user_id=test_user.id,
            type=GoalType.HIRING,
            description="Build engineering team"
        )
        db_session.add(goal)
        await db_session.commit()
        await db_session.refresh(goal)

        ask = Ask(
            user_id=test_user.id,
            goal_id=goal.id,
            description="Need referrals for senior engineers"
        )
        db_session.add(ask)
        await db_session.commit()
        ask_id = ask.id

        # Delete goal
        await db_session.delete(goal)
        await db_session.commit()

        # Verify ask still exists but goal_id is NULL
        result = await db_session.execute(
            select(Ask).where(Ask.id == ask_id)
        )
        updated_ask = result.scalar_one()
        assert updated_ask.id == ask_id
        assert updated_ask.goal_id is None

    @pytest.mark.asyncio
    async def test_ask_cascade_delete_with_user(self, db_session: AsyncSession):
        """Test asks are deleted when user is deleted (CASCADE)."""
        # Create new user
        user = User(
            linkedin_id=f"test_{uuid4()}",
            name="Test User",
            email="test@example.com"
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create asks for user
        asks = [
            Ask(
                user_id=user.id,
                description=f"Test ask {i}"
            )
            for i in range(3)
        ]
        for ask in asks:
            db_session.add(ask)
        await db_session.commit()

        user_id = user.id

        # Delete user
        await db_session.delete(user)
        await db_session.commit()

        # Verify asks were cascaded
        result = await db_session.execute(
            select(Ask).where(Ask.user_id == user_id)
        )
        remaining_asks = result.scalars().all()
        assert len(remaining_asks) == 0

    @pytest.mark.asyncio
    async def test_multiple_asks_per_user(self, db_session: AsyncSession, test_user: User):
        """Test user can have multiple asks."""
        asks = [
            Ask(
                user_id=test_user.id,
                description="Need pitch deck review",
                urgency=AskUrgency.HIGH
            ),
            Ask(
                user_id=test_user.id,
                description="Looking for co-founder",
                urgency=AskUrgency.MEDIUM
            ),
            Ask(
                user_id=test_user.id,
                description="Seeking marketing advice",
                urgency=AskUrgency.LOW
            )
        ]

        for ask in asks:
            db_session.add(ask)
        await db_session.commit()

        # Verify all asks exist
        result = await db_session.execute(
            select(Ask).where(Ask.user_id == test_user.id)
        )
        user_asks = result.scalars().all()
        assert len(user_asks) >= 3

    @pytest.mark.asyncio
    async def test_ask_update(self, db_session: AsyncSession, test_user: User):
        """Test updating ask fields."""
        ask = Ask(
            user_id=test_user.id,
            description="Need UX designer",
            urgency=AskUrgency.LOW
        )
        db_session.add(ask)
        await db_session.commit()
        await db_session.refresh(ask)

        original_created_at = ask.created_at

        # Update fields
        ask.description = "Need senior UX designer with B2B experience"
        ask.urgency = AskUrgency.HIGH
        await db_session.commit()
        await db_session.refresh(ask)

        assert ask.description == "Need senior UX designer with B2B experience"
        assert ask.urgency == AskUrgency.HIGH
        assert ask.created_at == original_created_at
        assert ask.updated_at > original_created_at

    @pytest.mark.asyncio
    async def test_ask_repr(self, test_user: User):
        """Test ask string representation."""
        ask = Ask(
            user_id=test_user.id,
            description="Looking for strategic advisors with marketplace experience and proven track record",
            urgency=AskUrgency.HIGH,
            status=AskStatus.OPEN
        )

        repr_str = repr(ask)
        assert "Ask" in repr_str
        assert "high" in repr_str.lower()
        assert "open" in repr_str.lower()
        assert "Looking for strategic advisors with marketplace" in repr_str  # First 50 chars
