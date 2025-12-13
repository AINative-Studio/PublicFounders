"""
Unit tests for database models.
"""
import pytest
from datetime import datetime, date
from uuid import uuid4

from backend.app.models import (
    User, FounderProfile, AutonomyMode,
    Company, CompanyStage, CompanyRole,
    Goal, GoalType, Ask, AskUrgency, AskStatus,
    Post, PostType, Introduction, IntroductionChannel,
    IntroductionStatus, InteractionOutcome, OutcomeType
)


@pytest.mark.unit
class TestUserModel:
    """Test User model."""

    async def test_user_creation(self, db_session, sample_user_data):
        """Test creating a user."""
        user = User(
            id=uuid4(),
            **sample_user_data,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        assert user.id is not None
        assert user.name == sample_user_data["name"]
        assert user.email == sample_user_data["email"]
        assert user.linkedin_id == sample_user_data["linkedin_id"]

    async def test_user_to_dict(self, sample_user_data):
        """Test user to_dict method."""
        user = User(
            id=uuid4(),
            **sample_user_data,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        user_dict = user.to_dict()

        assert "id" in user_dict
        assert user_dict["name"] == sample_user_data["name"]
        assert user_dict["email"] == sample_user_data["email"]
        assert "phone_verified" in user_dict


@pytest.mark.unit
class TestFounderProfileModel:
    """Test FounderProfile model."""

    async def test_founder_profile_creation(self, db_session, sample_user_data, sample_founder_profile_data):
        """Test creating a founder profile."""
        user = User(
            id=uuid4(),
            **sample_user_data,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        profile = FounderProfile(
            user_id=user.id,
            **sample_founder_profile_data,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(profile)

        assert profile.user_id == user.id
        assert profile.bio == sample_founder_profile_data["bio"]
        assert profile.autonomy_mode == AutonomyMode.SUGGEST


@pytest.mark.unit
class TestCompanyModel:
    """Test Company model."""

    async def test_company_creation(self, db_session, sample_company_data):
        """Test creating a company."""
        company = Company(
            id=uuid4(),
            **sample_company_data,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        db_session.add(company)
        await db_session.commit()
        await db_session.refresh(company)

        assert company.id is not None
        assert company.name == sample_company_data["name"]
        assert company.stage == CompanyStage.SEED

    async def test_company_embedding_content(self, sample_company_data):
        """Test company embedding content generation."""
        company = Company(
            id=uuid4(),
            **sample_company_data,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        content = company.embedding_content

        assert company.name in content
        assert "Stage:" in content
        assert "Industry:" in content


@pytest.mark.unit
class TestGoalModel:
    """Test Goal model."""

    async def test_goal_creation(self, db_session, sample_user_data, sample_goal_data):
        """Test creating a goal."""
        user = User(
            id=uuid4(),
            **sample_user_data,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db_session.add(user)
        await db_session.commit()

        goal = Goal(
            id=uuid4(),
            user_id=user.id,
            **sample_goal_data,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        db_session.add(goal)
        await db_session.commit()
        await db_session.refresh(goal)

        assert goal.id is not None
        assert goal.type == GoalType.FUNDRAISING
        assert goal.priority == sample_goal_data["priority"]

    async def test_goal_embedding_content(self, sample_user_data, sample_goal_data):
        """Test goal embedding content generation."""
        goal = Goal(
            id=uuid4(),
            user_id=uuid4(),
            **sample_goal_data,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        content = goal.embedding_content

        assert "fundraising" in content.lower()
        assert sample_goal_data["description"] in content


@pytest.mark.unit
class TestAskModel:
    """Test Ask model."""

    async def test_ask_creation(self, db_session, sample_user_data, sample_ask_data):
        """Test creating an ask."""
        user = User(
            id=uuid4(),
            **sample_user_data,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db_session.add(user)
        await db_session.commit()

        ask = Ask(
            id=uuid4(),
            user_id=user.id,
            **sample_ask_data,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        db_session.add(ask)
        await db_session.commit()
        await db_session.refresh(ask)

        assert ask.id is not None
        assert ask.urgency == AskUrgency.HIGH
        assert ask.status == AskStatus.OPEN

    async def test_ask_mark_fulfilled(self, sample_user_data, sample_ask_data):
        """Test marking ask as fulfilled."""
        ask = Ask(
            id=uuid4(),
            user_id=uuid4(),
            **sample_ask_data,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        ask.mark_fulfilled()

        assert ask.status == AskStatus.FULFILLED
        assert ask.fulfilled_at is not None


@pytest.mark.unit
class TestPostModel:
    """Test Post model."""

    async def test_post_creation(self, db_session, sample_user_data, sample_post_data):
        """Test creating a post."""
        user = User(
            id=uuid4(),
            **sample_user_data,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db_session.add(user)
        await db_session.commit()

        post = Post(
            id=uuid4(),
            user_id=user.id,
            **sample_post_data,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        db_session.add(post)
        await db_session.commit()
        await db_session.refresh(post)

        assert post.id is not None
        assert post.type == PostType.PROGRESS
        assert post.embedding_status == "pending"

    async def test_post_mark_embedding_completed(self, sample_user_data, sample_post_data):
        """Test marking embedding as completed."""
        post = Post(
            id=uuid4(),
            user_id=uuid4(),
            **sample_post_data,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        post.mark_embedding_completed()

        assert post.embedding_status == "completed"
        assert post.embedding_created_at is not None
        assert post.embedding_error is None


@pytest.mark.unit
class TestIntroductionModel:
    """Test Introduction model."""

    async def test_introduction_creation(self, db_session, sample_user_data, sample_introduction_data):
        """Test creating an introduction."""
        user1 = User(
            id=uuid4(),
            **sample_user_data,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db_session.add(user1)

        user2_data = sample_user_data.copy()
        user2_data["linkedin_id"] = "test-linkedin-456"
        user2_data["email"] = "test2@example.com"
        user2 = User(
            id=uuid4(),
            **user2_data,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db_session.add(user2)
        await db_session.commit()

        intro = Introduction(
            id=uuid4(),
            requester_id=user1.id,
            target_id=user2.id,
            **sample_introduction_data,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        db_session.add(intro)
        await db_session.commit()
        await db_session.refresh(intro)

        assert intro.id is not None
        assert intro.channel == IntroductionChannel.LINKEDIN
        assert intro.status == IntroductionStatus.PROPOSED

    async def test_introduction_mark_sent(self, sample_introduction_data):
        """Test marking introduction as sent."""
        intro = Introduction(
            id=uuid4(),
            requester_id=uuid4(),
            target_id=uuid4(),
            **sample_introduction_data,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        intro.mark_sent()

        assert intro.status == IntroductionStatus.SENT
        assert intro.sent_at is not None


@pytest.mark.unit
class TestInteractionOutcomeModel:
    """Test InteractionOutcome model."""

    async def test_outcome_is_successful(self):
        """Test is_successful property."""
        outcome = InteractionOutcome(
            id=uuid4(),
            introduction_id=uuid4(),
            outcome_type=OutcomeType.MEETING,
            recorded_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        assert outcome.is_successful is True

        outcome.outcome_type = OutcomeType.NONE
        assert outcome.is_successful is False
