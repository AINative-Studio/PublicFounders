"""
Posts API Endpoints
Implements CRUD operations for build-in-public posts with async embedding and semantic discovery.

Endpoints:
- POST   /api/v1/posts - Create post
- GET    /api/v1/posts - List posts (chronological feed)
- GET    /api/v1/posts/discover - Semantic discovery feed
- POST   /api/v1/posts/{post_id}/view - Track post view
- GET    /api/v1/posts/{post_id} - Get post
- PUT    /api/v1/posts/{post_id} - Update post
- DELETE /api/v1/posts/{post_id} - Delete post
"""
import asyncio
import logging
import time
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.models.user import User
from app.models.post import Post, PostType
from app.models.goal import Goal
from app.schemas.post import (
    PostCreate,
    PostUpdate,
    PostResponse,
    PostListResponse,
    PostDiscoveryRequest,
    PostDiscoveryResponse
)
from app.services.embedding_service import embedding_service, EmbeddingServiceError
from app.services.cache_service import cache_service
from app.services.safety_service import safety_service
from app.services.rlhf_service import rlhf_service, RLHFServiceError
from app.services.observability_service import observability_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/posts", tags=["posts"])


# TODO: Replace with actual auth dependency from Sprint 1
async def get_current_user(db: AsyncSession = Depends(get_db)) -> User:
    """Mock auth dependency - replace with Sprint 1 implementation."""
    result = await db.execute(select(User).limit(1))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return user


async def create_post_embedding_async(post_id: UUID, user_id: UUID, post_type: str, content: str, db_url: str):
    """
    Background task to create post embedding asynchronously.

    This function runs after the API response is sent, so embedding failures
    don't block the user experience.
    """
    # Import here to avoid circular dependencies
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

    try:
        # Create new DB session for background task
        engine = create_async_engine(db_url)
        async_session = async_sessionmaker(engine, expire_on_commit=False)

        async with async_session() as session:
            # Update post embedding status to processing
            result = await session.execute(
                select(Post).where(Post.id == post_id)
            )
            post = result.scalar_one_or_none()

            if not post:
                logger.error(f"Post {post_id} not found for embedding")
                return

            post.embedding_status = "processing"
            await session.commit()

            # Create embedding
            await embedding_service.create_post_embedding(
                post_id=post_id,
                user_id=user_id,
                post_type=post_type,
                content=content,
                additional_metadata={}
            )

            # Mark as completed
            post.mark_embedding_completed()
            await session.commit()

            logger.info(f"Successfully created post embedding for {post_id}")

    except EmbeddingServiceError as e:
        logger.error(f"Failed to create post embedding for {post_id}: {e}")

        # Update post with error
        try:
            async with async_session() as session:
                result = await session.execute(
                    select(Post).where(Post.id == post_id)
                )
                post = result.scalar_one_or_none()
                if post:
                    post.mark_embedding_failed(str(e))
                    await session.commit()
        except Exception as update_error:
            logger.error(f"Failed to update post error status: {update_error}")

    except Exception as e:
        logger.error(f"Unexpected error creating post embedding: {e}")

    finally:
        await engine.dispose()


@router.post(
    "",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new post",
    description="Create a new post with async embedding (doesn't block response)"
)
async def create_post(
    post_data: PostCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> PostResponse:
    """
    Create a new build-in-public post.

    - Validates post data
    - Scans for inappropriate content and PII
    - Persists to database immediately
    - Queues embedding creation as background task (ASYNC - don't block UX)
    - Returns created post with embedding_status='pending'
    """
    # Scan post content for safety issues
    try:
        safety_check = await safety_service.scan_text(
            text=post_data.content,
            checks=["content_moderation", "pii"]
        )

        # Block inappropriate content
        if not safety_check.is_safe:
            logger.warning(
                f"Post creation blocked for user {current_user.id}: "
                f"flags {safety_check.content_flags}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Post contains inappropriate content: {', '.join(safety_check.content_flags)}"
            )

        # Warn about PII (log but don't block)
        if safety_check.contains_pii:
            logger.warning(
                f"Post for user {current_user.id} contains PII: {safety_check.pii_types}"
            )

    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        # Log safety errors but don't block post creation
        logger.error(f"Safety check failed for post creation: {e}")

    # Create post in database
    post = Post(
        user_id=current_user.id,
        type=post_data.type,
        content=post_data.content,
        is_cross_posted=post_data.is_cross_posted
    )

    db.add(post)
    await db.commit()
    await db.refresh(post)

    # Queue embedding creation as background task
    # This runs AFTER the response is sent, so it doesn't block the user
    from app.core.config import settings
    background_tasks.add_task(
        create_post_embedding_async,
        post_id=post.id,
        user_id=current_user.id,
        post_type=post.type.value,
        content=post.content,
        db_url=settings.DATABASE_URL
    )

    # Invalidate discovery cache since new content affects all discovery results
    background_tasks.add_task(
        cache_service.invalidate_all_cache
    )

    logger.info(f"Created post {post.id}, embedding queued, cache invalidation scheduled")

    return PostResponse.model_validate(post)


@router.get(
    "",
    response_model=PostListResponse,
    summary="List posts (chronological feed)",
    description="Retrieve paginated chronological feed of posts"
)
async def list_posts(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    user_id: Optional[UUID] = Query(None, description="Filter by user"),
    post_type: Optional[PostType] = Query(None, description="Filter by type"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> PostListResponse:
    """
    List posts in chronological order (newest first).

    - Supports pagination
    - Filter by user or post type
    - Orders by created_at desc
    """
    # Build query
    query = select(Post)

    # Apply filters
    if user_id is not None:
        query = query.where(Post.user_id == user_id)

    if post_type is not None:
        query = query.where(Post.type == post_type)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply ordering and pagination
    query = query.order_by(
        Post.created_at.desc()
    ).offset((page - 1) * page_size).limit(page_size)

    # Execute query
    result = await db.execute(query)
    posts = result.scalars().all()

    return PostListResponse(
        posts=[PostResponse.model_validate(post) for post in posts],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total
    )


@router.get(
    "/discover",
    response_model=PostDiscoveryResponse,
    summary="Discover relevant posts (semantic)",
    description="Discover posts relevant to your goals using semantic search with caching"
)
async def discover_posts(
    discovery_params: PostDiscoveryRequest = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> PostDiscoveryResponse:
    """
    Discover posts semantically relevant to user's goals.

    - Combines user's active goals as query
    - Checks cache first for performance (< 200ms for cache hits)
    - Semantic search with recency weighting if cache miss
    - Caches results with 5-minute TTL
    - Returns ranked posts with similarity scores
    """
    # Get user's active goals
    result = await db.execute(
        select(Goal).where(
            Goal.user_id == current_user.id,
            Goal.is_active == True
        )
    )
    goals = result.scalars().all()

    if not goals:
        # No active goals, return empty results
        return PostDiscoveryResponse(
            posts=[],
            similarity_scores=[],
            total=0
        )

    # Extract goal descriptions
    goal_descriptions = [goal.description for goal in goals]

    # CACHE LOOKUP: Check if we have cached results
    cached_results = await cache_service.get_cached_discovery(
        user_id=current_user.id,
        goal_descriptions=goal_descriptions
    )

    if cached_results:
        logger.info(f"Cache HIT for user {current_user.id} discovery")
        # Return cached results directly
        return PostDiscoveryResponse(**cached_results)

    logger.info(f"Cache MISS for user {current_user.id} discovery - performing semantic search")

    try:
        # Track discovery start time for observability
        start_time = time.time()

        # Perform semantic discovery
        scored_results = await embedding_service.discover_relevant_posts(
            user_goals=goal_descriptions,
            limit=discovery_params.limit,
            recency_weight=discovery_params.recency_weight
        )

        discovery_duration_ms = (time.time() - start_time) * 1000

        # Extract post IDs from results
        post_ids = []
        similarity_scores = []

        for result_data, combined_score in scored_results:
            # Extract source_id from metadata
            metadata = result_data.get("metadata", {})
            source_id = metadata.get("source_id")
            if source_id:
                try:
                    post_ids.append(UUID(source_id))
                    similarity_scores.append(combined_score)
                except ValueError:
                    logger.warning(f"Invalid UUID in source_id: {source_id}")
                    continue

        # Fetch posts from database
        if post_ids:
            posts_result = await db.execute(
                select(Post).where(Post.id.in_(post_ids))
            )
            posts = posts_result.scalars().all()

            # Create a mapping for ordering
            post_map = {post.id: post for post in posts}

            # Reorder posts to match similarity order
            ordered_posts = [post_map[post_id] for post_id in post_ids if post_id in post_map]

            response_data = PostDiscoveryResponse(
                posts=[PostResponse.model_validate(post) for post in ordered_posts],
                similarity_scores=similarity_scores[:len(ordered_posts)],
                total=len(ordered_posts)
            )
        else:
            response_data = PostDiscoveryResponse(
                posts=[],
                similarity_scores=[],
                total=0
            )

        # CACHE STORAGE: Store results for future requests
        await cache_service.cache_discovery_results(
            user_id=current_user.id,
            goal_descriptions=goal_descriptions,
            results=response_data.model_dump(),
            ttl_seconds=300  # 5 minutes
        )

        # Track RLHF interaction for discovery learning (no clicks yet)
        try:
            await rlhf_service.track_discovery_interaction(
                user_id=current_user.id,
                user_goals=goal_descriptions,
                shown_posts=post_ids,
                clicked_post_id=None  # Will be tracked separately on click
            )
        except RLHFServiceError as e:
            logger.warning(f"Failed to track RLHF discovery interaction: {e}")

        # Track API performance
        await observability_service.track_api_call(
            endpoint="/posts/discover",
            method="GET",
            duration_ms=discovery_duration_ms,
            status_code=200,
            user_id=str(current_user.id)
        )

        return response_data

    except EmbeddingServiceError as e:
        logger.error(f"Semantic discovery failed: {e}")

        # Track error
        await observability_service.track_error(
            error_type="discovery_error",
            error_message=str(e),
            severity="high",
            context={"user_id": str(current_user.id), "goal_count": len(goal_descriptions)}
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Semantic search temporarily unavailable"
        )


@router.post(
    "/{post_id}/view",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Track post view",
    description="Track when user views/clicks a discovered post for RLHF learning"
)
async def track_post_view(
    post_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> None:
    """
    Track when user views/clicks a discovered post.

    - Updates RLHF with positive feedback for discovery algorithm
    - Helps improve future discovery recommendations
    - Returns 204 No Content on success
    """
    # Verify post exists
    result = await db.execute(
        select(Post).where(Post.id == post_id)
    )
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post {post_id} not found"
        )

    # Get user's active goals for context
    goals_result = await db.execute(
        select(Goal).where(
            Goal.user_id == current_user.id,
            Goal.is_active == True
        )
    )
    goals = goals_result.scalars().all()
    goal_descriptions = [goal.description for goal in goals]

    # Track discovery interaction with click feedback
    try:
        await rlhf_service.track_discovery_interaction(
            user_id=current_user.id,
            user_goals=goal_descriptions,
            shown_posts=[post_id],
            clicked_post_id=post_id
        )
        logger.info(f"Tracked post view: user={current_user.id}, post={post_id}")
    except RLHFServiceError as e:
        # Don't fail the request if RLHF tracking fails
        logger.warning(f"Failed to track post view: {e}")

    return None


@router.get(
    "/{post_id}",
    response_model=PostResponse,
    summary="Get a specific post",
    description="Retrieve a post by ID"
)
async def get_post(
    post_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> PostResponse:
    """
    Get a specific post by ID.

    - Any authenticated user can view posts (public feed)
    - Returns 404 if not found
    """
    result = await db.execute(
        select(Post).where(Post.id == post_id)
    )
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post {post_id} not found"
        )

    return PostResponse.model_validate(post)


@router.put(
    "/{post_id}",
    response_model=PostResponse,
    summary="Update a post",
    description="Update post fields and queue embedding regeneration if content changed"
)
async def update_post(
    post_id: UUID,
    post_update: PostUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> PostResponse:
    """
    Update an existing post.

    - Verifies post belongs to authenticated user
    - Scans for inappropriate content and PII if content updated
    - Updates only provided fields
    - Queues embedding regeneration if content or type changed (async)
    - Returns updated post
    """
    # Scan content for safety issues if being updated
    update_data = post_update.model_dump(exclude_unset=True)
    if "content" in update_data:
        try:
            safety_check = await safety_service.scan_text(
                text=update_data["content"],
                checks=["content_moderation", "pii"]
            )

            # Block inappropriate content
            if not safety_check.is_safe:
                logger.warning(
                    f"Post update blocked for user {current_user.id}: "
                    f"flags {safety_check.content_flags}"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Post contains inappropriate content: {', '.join(safety_check.content_flags)}"
                )

            # Warn about PII
            if safety_check.contains_pii:
                logger.warning(
                    f"Post update for user {current_user.id} contains PII: {safety_check.pii_types}"
                )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Safety check failed for post update: {e}")

    # Fetch post
    result = await db.execute(
        select(Post).where(
            Post.id == post_id,
            Post.user_id == current_user.id
        )
    )
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post {post_id} not found"
        )

    # Track if embedding needs update
    needs_embedding_update = False

    # Update fields
    update_data = post_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field in ["content", "type"]:
            needs_embedding_update = True
        setattr(post, field, value)

    await db.commit()
    await db.refresh(post)

    # Queue embedding update if needed (async)
    if needs_embedding_update:
        from app.core.config import settings
        background_tasks.add_task(
            create_post_embedding_async,
            post_id=post.id,
            user_id=current_user.id,
            post_type=post.type.value,
            content=post.content,
            db_url=settings.DATABASE_URL
        )
        logger.info(f"Updated post {post.id}, embedding update queued")

    return PostResponse.model_validate(post)


@router.delete(
    "/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a post",
    description="Delete a post and its embedding"
)
async def delete_post(
    post_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> None:
    """
    Delete a post.

    - Verifies post belongs to authenticated user
    - Deletes from database
    - Attempts to delete embedding from ZeroDB
    - Returns 204 on success
    """
    # Fetch post
    result = await db.execute(
        select(Post).where(
            Post.id == post_id,
            Post.user_id == current_user.id
        )
    )
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post {post_id} not found"
        )

    # Delete from database
    await db.delete(post)
    await db.commit()

    # Attempt to delete embedding (don't fail if this errors)
    try:
        vector_id = f"post_{post_id}"
        await embedding_service.delete_embedding(vector_id)
        logger.info(f"Deleted post embedding {vector_id}")
    except Exception as e:
        logger.error(f"Failed to delete post embedding: {e}")

    return None
