"""
Unit tests for Posts CRUD operations.
Following TDD principles - tests written BEFORE implementation.

Test Coverage:
- Post creation with different types
- Post embedding status tracking
- Cross-posting flag
- Async embedding workflow
- Embedding failure handling
- User relationship validation
- Chronological ordering
- Embedding content generation
"""
import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.post import Post, PostType
from app.models.user import User


class TestPostModel:
    """Test Post SQLAlchemy model."""

    @pytest.mark.asyncio
    async def test_create_post_valid(self, db_session: AsyncSession, test_user: User):
        """Test creating a post with valid data."""
        post = Post(
            user_id=test_user.id,
            type=PostType.MILESTONE,
            content="Just closed our first enterprise customer! $50k ARR.",
            is_cross_posted=True
        )
        db_session.add(post)
        await db_session.commit()
        await db_session.refresh(post)

        assert post.id is not None
        assert post.user_id == test_user.id
        assert post.type == PostType.MILESTONE
        assert post.content == "Just closed our first enterprise customer! $50k ARR."
        assert post.is_cross_posted is True
        assert post.created_at is not None
        assert post.embedding_status == "pending"  # Default
        assert post.embedding_created_at is None
        assert post.embedding_error is None

    @pytest.mark.asyncio
    async def test_post_default_values(self, db_session: AsyncSession, test_user: User):
        """Test post default values are set correctly."""
        post = Post(
            user_id=test_user.id,
            type=PostType.PROGRESS,
            content="Made progress on user authentication flow today."
        )
        db_session.add(post)
        await db_session.commit()
        await db_session.refresh(post)

        assert post.is_cross_posted is False  # Default
        assert post.embedding_status == "pending"  # Default
        assert post.embedding_created_at is None
        assert post.embedding_error is None

    @pytest.mark.asyncio
    async def test_post_types_enum(self, db_session: AsyncSession, test_user: User):
        """Test all post type enums work correctly."""
        post_types = [
            PostType.PROGRESS,
            PostType.LEARNING,
            PostType.MILESTONE,
            PostType.ASK
        ]

        for post_type in post_types:
            post = Post(
                user_id=test_user.id,
                type=post_type,
                content=f"Test post for {post_type.value} type"
            )
            db_session.add(post)

        await db_session.commit()

        # Verify all were created
        result = await db_session.execute(
            select(Post).where(Post.user_id == test_user.id)
        )
        posts = result.scalars().all()
        assert len(posts) == len(post_types)

    @pytest.mark.asyncio
    async def test_post_embedding_status_workflow(self, db_session: AsyncSession, test_user: User):
        """Test embedding status lifecycle from pending to completed."""
        post = Post(
            user_id=test_user.id,
            type=PostType.LEARNING,
            content="Learned about the importance of semantic embeddings today."
        )
        db_session.add(post)
        await db_session.commit()
        await db_session.refresh(post)

        # Initially pending
        assert post.embedding_status == "pending"
        assert post.embedding_created_at is None

        # Mark as completed
        post.mark_embedding_completed()
        await db_session.commit()
        await db_session.refresh(post)

        assert post.embedding_status == "completed"
        assert post.embedding_created_at is not None
        assert isinstance(post.embedding_created_at, datetime)
        assert post.embedding_error is None

    @pytest.mark.asyncio
    async def test_post_embedding_failure_handling(self, db_session: AsyncSession, test_user: User):
        """Test embedding failure is tracked properly."""
        post = Post(
            user_id=test_user.id,
            type=PostType.PROGRESS,
            content="Working on the new feature."
        )
        db_session.add(post)
        await db_session.commit()
        await db_session.refresh(post)

        # Mark as failed with error
        error_msg = "OpenAI API rate limit exceeded"
        post.mark_embedding_failed(error_msg)
        await db_session.commit()
        await db_session.refresh(post)

        assert post.embedding_status == "failed"
        assert post.embedding_error == error_msg
        assert post.embedding_created_at is None  # No completion timestamp

    @pytest.mark.asyncio
    async def test_post_user_relationship(self, db_session: AsyncSession, test_user: User):
        """Test post belongs to user relationship."""
        post = Post(
            user_id=test_user.id,
            type=PostType.ASK,
            content="Anyone have experience with Stripe Connect?"
        )
        db_session.add(post)
        await db_session.commit()
        await db_session.refresh(post)

        # Load user relationship
        await db_session.refresh(post, ["user"])
        assert post.user.id == test_user.id
        assert post.user.name == test_user.name

    @pytest.mark.asyncio
    async def test_post_embedding_content_generation(self, test_user: User):
        """Test embedding content includes post type prefix."""
        # Progress post
        progress_post = Post(
            user_id=test_user.id,
            type=PostType.PROGRESS,
            content="Shipped user dashboard v2 today"
        )
        assert "[PROGRESS]" in progress_post.embedding_content
        assert "Shipped user dashboard v2 today" in progress_post.embedding_content

        # Milestone post
        milestone_post = Post(
            user_id=test_user.id,
            type=PostType.MILESTONE,
            content="Reached 10k users!"
        )
        assert "[MILESTONE]" in milestone_post.embedding_content
        assert "Reached 10k users!" in milestone_post.embedding_content

        # Learning post
        learning_post = Post(
            user_id=test_user.id,
            type=PostType.LEARNING,
            content="TDD improves code quality significantly"
        )
        assert "[LEARNING]" in learning_post.embedding_content

        # Ask post
        ask_post = Post(
            user_id=test_user.id,
            type=PostType.ASK,
            content="Looking for feedback on our pricing model"
        )
        assert "[ASK]" in ask_post.embedding_content

    @pytest.mark.asyncio
    async def test_post_chronological_ordering(self, db_session: AsyncSession, test_user: User):
        """Test posts can be ordered chronologically."""
        # Create posts with slight time differences
        posts = []
        for i in range(3):
            post = Post(
                user_id=test_user.id,
                type=PostType.PROGRESS,
                content=f"Update {i}"
            )
            db_session.add(post)
            await db_session.commit()
            await db_session.refresh(post)
            posts.append(post)

            # Small delay to ensure different timestamps
            await asyncio.sleep(0.01)

        # Query posts in descending order (newest first)
        result = await db_session.execute(
            select(Post)
            .where(Post.user_id == test_user.id)
            .order_by(Post.created_at.desc())
        )
        ordered_posts = result.scalars().all()

        # Verify order (newest should be last in our creation list)
        assert ordered_posts[0].content == "Update 2"
        assert ordered_posts[-1].content == "Update 0"

    @pytest.mark.asyncio
    async def test_post_cascade_delete_with_user(self, db_session: AsyncSession):
        """Test posts are deleted when user is deleted (CASCADE)."""
        # Create new user
        user = User(
            linkedin_id=f"test_{uuid4()}",
            name="Test User",
            email="test@example.com"
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create posts for user
        posts = [
            Post(
                user_id=user.id,
                type=PostType.PROGRESS,
                content=f"Test post {i}"
            )
            for i in range(3)
        ]
        for post in posts:
            db_session.add(post)
        await db_session.commit()

        user_id = user.id

        # Delete user
        await db_session.delete(user)
        await db_session.commit()

        # Verify posts were cascaded
        result = await db_session.execute(
            select(Post).where(Post.user_id == user_id)
        )
        remaining_posts = result.scalars().all()
        assert len(remaining_posts) == 0

    @pytest.mark.asyncio
    async def test_multiple_posts_per_user(self, db_session: AsyncSession, test_user: User):
        """Test user can have multiple posts."""
        posts = [
            Post(
                user_id=test_user.id,
                type=PostType.PROGRESS,
                content="Implemented user authentication",
                is_cross_posted=True
            ),
            Post(
                user_id=test_user.id,
                type=PostType.LEARNING,
                content="Learned about event-driven architecture"
            ),
            Post(
                user_id=test_user.id,
                type=PostType.MILESTONE,
                content="First paying customer!"
            )
        ]

        for post in posts:
            db_session.add(post)
        await db_session.commit()

        # Verify all posts exist
        result = await db_session.execute(
            select(Post).where(Post.user_id == test_user.id)
        )
        user_posts = result.scalars().all()
        assert len(user_posts) >= 3

    @pytest.mark.asyncio
    async def test_post_update(self, db_session: AsyncSession, test_user: User):
        """Test updating post fields."""
        post = Post(
            user_id=test_user.id,
            type=PostType.PROGRESS,
            content="Working on feature X"
        )
        db_session.add(post)
        await db_session.commit()
        await db_session.refresh(post)

        original_created_at = post.created_at

        # Update fields
        post.content = "Completed feature X and started feature Y"
        post.is_cross_posted = True
        await db_session.commit()
        await db_session.refresh(post)

        assert post.content == "Completed feature X and started feature Y"
        assert post.is_cross_posted is True
        assert post.created_at == original_created_at
        assert post.updated_at > original_created_at

    @pytest.mark.asyncio
    async def test_post_repr(self, test_user: User):
        """Test post string representation."""
        post = Post(
            user_id=test_user.id,
            type=PostType.MILESTONE,
            content="Just raised our seed round! $2M from top tier VCs. Excited for this journey ahead!"
        )

        repr_str = repr(post)
        assert "Post" in repr_str
        assert "milestone" in repr_str.lower()
        assert "Just raised our seed round! $2M from top tier VCs" in repr_str  # First 50 chars

    @pytest.mark.asyncio
    async def test_post_cross_posting_flag(self, db_session: AsyncSession, test_user: User):
        """Test cross-posting flag works correctly."""
        # Post with cross-posting
        cross_posted = Post(
            user_id=test_user.id,
            type=PostType.MILESTONE,
            content="Major milestone achieved!",
            is_cross_posted=True
        )
        db_session.add(cross_posted)

        # Post without cross-posting
        not_cross_posted = Post(
            user_id=test_user.id,
            type=PostType.PROGRESS,
            content="Small internal win",
            is_cross_posted=False
        )
        db_session.add(not_cross_posted)

        await db_session.commit()
        await db_session.refresh(cross_posted)
        await db_session.refresh(not_cross_posted)

        assert cross_posted.is_cross_posted is True
        assert not_cross_posted.is_cross_posted is False


# Import asyncio for sleep
import asyncio
