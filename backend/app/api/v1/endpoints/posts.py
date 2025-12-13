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
import uuid as uuid_module
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from app.models.user import User
from app.models.post import PostType
from app.schemas.post import (
    PostCreate,
    PostUpdate,
    PostResponse,
    PostListResponse,
    PostDiscoveryRequest,
    PostDiscoveryResponse
)
from app.services.zerodb_client import zerodb_client
from app.services.embedding_service import embedding_service, EmbeddingServiceError
from app.services.cache_service import cache_service
from app.services.safety_service import safety_service
from app.services.rlhf_service import rlhf_service, RLHFServiceError
from app.services.observability_service import observability_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/posts", tags=["posts"])


# TODO: Replace with actual auth dependency from Sprint 1
async def get_current_user() -> User:
    """Mock auth dependency - replace with Sprint 1 implementation."""
    users = await zerodb_client.query_rows(
        table_name="users",
        limit=1
    )
    if not users:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    # Convert dict to User object for compatibility
    user_data = users[0]
    user = User()
    user.id = UUID(user_data["id"])
    user.name = user_data.get("name")
    user.email = user_data.get("email")
    return user


async def create_post_embedding_async(post_id: UUID, user_id: UUID, post_type: str, content: str):
    """
    Background task to create post embedding asynchronously.

    This function runs after the API response is sent, so embedding failures
    don't block the user experience.
    """
    try:
        # Update post embedding status to processing
        await zerodb_client.update_rows(
            table_name="posts",
            filter={"id": str(post_id)},
            update={"$set": {
                "embedding_status": "processing",
                "updated_at": datetime.utcnow().isoformat()
            }}
        )

        # Create embedding
        await embedding_service.create_post_embedding(
            post_id=post_id,
            user_id=user_id,
            post_type=post_type,
            content=content,
            additional_metadata={}
        )

        # Mark as completed
        await zerodb_client.update_rows(
            table_name="posts",
            filter={"id": str(post_id)},
            update={"$set": {
                "embedding_status": "completed",
                "embedding_created_at": datetime.utcnow().isoformat(),
                "embedding_error": None,
                "updated_at": datetime.utcnow().isoformat()
            }}
        )

        logger.info(f"Successfully created post embedding for {post_id}")

    except EmbeddingServiceError as e:
        logger.error(f"Failed to create post embedding for {post_id}: {e}")

        # Update post with error
        try:
            await zerodb_client.update_rows(
                table_name="posts",
                filter={"id": str(post_id)},
                update={"$set": {
                    "embedding_status": "failed",
                    "embedding_error": str(e),
                    "updated_at": datetime.utcnow().isoformat()
                }}
            )
        except Exception as update_error:
            logger.error(f"Failed to update post error status: {update_error}")

    except Exception as e:
        logger.error(f"Unexpected error creating post embedding: {e}")


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

    # Create post in ZeroDB
    post_id = uuid_module.uuid4()
    now = datetime.utcnow().isoformat()

    post_data_dict = {
        "id": str(post_id),
        "user_id": str(current_user.id),
        "type": post_data.type.value,
        "content": post_data.content,
        "is_cross_posted": post_data.is_cross_posted,
        "embedding_status": "pending",
        "embedding_created_at": None,
        "embedding_error": None,
        "created_at": now,
        "updated_at": now
    }

    await zerodb_client.insert_rows(
        table_name="posts",
        rows=[post_data_dict]
    )

    # Queue embedding creation as background task
    # This runs AFTER the response is sent, so it doesn't block the user
    background_tasks.add_task(
        create_post_embedding_async,
        post_id=post_id,
        user_id=current_user.id,
        post_type=post_data.type.value,
        content=post_data.content
    )

    # Invalidate discovery cache since new content affects all discovery results
    background_tasks.add_task(
        cache_service.invalidate_all_cache
    )

    logger.info(f"Created post {post_id}, embedding queued, cache invalidation scheduled")

    return PostResponse(**post_data_dict)


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
    current_user: User = Depends(get_current_user)
) -> PostListResponse:
    """
    List posts in chronological order (newest first).

    - Supports pagination
    - Filter by user or post type
    - Orders by created_at desc
    """
    # Build filter
    filter_dict = {}
    if user_id is not None:
        filter_dict["user_id"] = str(user_id)
    if post_type is not None:
        filter_dict["type"] = post_type.value

    # Get total count (query all matching to get count)
    all_matching = await zerodb_client.query_rows(
        table_name="posts",
        filter=filter_dict,
        limit=10000  # High limit to get all for counting
    )
    total = len(all_matching)

    # Get paginated results with sorting
    posts = await zerodb_client.query_rows(
        table_name="posts",
        filter=filter_dict,
        limit=page_size,
        offset=(page - 1) * page_size,
        sort={"created_at": -1}  # -1 for descending order
    )

    return PostListResponse(
        posts=[PostResponse(**post) for post in posts],
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
    goals = await zerodb_client.query_rows(
        table_name="goals",
        filter={
            "user_id": str(current_user.id),
            "is_active": True
        }
    )

    if not goals:
        # No active goals, return empty results
        return PostDiscoveryResponse(
            posts=[],
            similarity_scores=[],
            total=0
        )

    # Extract goal descriptions
    goal_descriptions = [goal["description"] for goal in goals]

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
            # Query posts by IDs - note: ZeroDB doesn't have native $in operator
            # so we need to query individually or use a workaround
            all_posts = []
            for post_id in post_ids:
                post_results = await zerodb_client.query_rows(
                    table_name="posts",
                    filter={"id": str(post_id)},
                    limit=1
                )
                if post_results:
                    all_posts.append(post_results[0])

            # Create a mapping for ordering
            post_map = {UUID(post["id"]): post for post in all_posts}

            # Reorder posts to match similarity order
            ordered_posts = [post_map[post_id] for post_id in post_ids if post_id in post_map]

            response_data = PostDiscoveryResponse(
                posts=[PostResponse(**post) for post in ordered_posts],
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
    current_user: User = Depends(get_current_user)
) -> None:
    """
    Track when user views/clicks a discovered post.

    - Updates RLHF with positive feedback for discovery algorithm
    - Helps improve future discovery recommendations
    - Returns 204 No Content on success
    """
    # Verify post exists
    post = await zerodb_client.get_by_id(
        table_name="posts",
        id=str(post_id)
    )

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post {post_id} not found"
        )

    # Get user's active goals for context
    goals = await zerodb_client.query_rows(
        table_name="goals",
        filter={
            "user_id": str(current_user.id),
            "is_active": True
        }
    )
    goal_descriptions = [goal["description"] for goal in goals]

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
    current_user: User = Depends(get_current_user)
) -> PostResponse:
    """
    Get a specific post by ID.

    - Any authenticated user can view posts (public feed)
    - Returns 404 if not found
    """
    post = await zerodb_client.get_by_id(
        table_name="posts",
        id=str(post_id)
    )

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post {post_id} not found"
        )

    return PostResponse(**post)


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
    posts = await zerodb_client.query_rows(
        table_name="posts",
        filter={
            "id": str(post_id),
            "user_id": str(current_user.id)
        },
        limit=1
    )

    if not posts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post {post_id} not found"
        )

    post = posts[0]

    # Track if embedding needs update
    needs_embedding_update = False

    # Prepare update data
    update_fields = post_update.model_dump(exclude_unset=True)

    # Convert enum to value if type is being updated
    if "type" in update_fields:
        update_fields["type"] = update_fields["type"].value
        needs_embedding_update = True

    if "content" in update_fields:
        needs_embedding_update = True

    # Add updated_at timestamp
    update_fields["updated_at"] = datetime.utcnow().isoformat()

    # Update in ZeroDB
    await zerodb_client.update_rows(
        table_name="posts",
        filter={"id": str(post_id)},
        update={"$set": update_fields}
    )

    # Get updated post
    updated_posts = await zerodb_client.query_rows(
        table_name="posts",
        filter={"id": str(post_id)},
        limit=1
    )
    updated_post = updated_posts[0]

    # Queue embedding update if needed (async)
    if needs_embedding_update:
        background_tasks.add_task(
            create_post_embedding_async,
            post_id=UUID(updated_post["id"]),
            user_id=UUID(updated_post["user_id"]),
            post_type=updated_post["type"],
            content=updated_post["content"]
        )
        logger.info(f"Updated post {post_id}, embedding update queued")

    return PostResponse(**updated_post)


@router.delete(
    "/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a post",
    description="Delete a post and its embedding"
)
async def delete_post(
    post_id: UUID,
    current_user: User = Depends(get_current_user)
) -> None:
    """
    Delete a post.

    - Verifies post belongs to authenticated user
    - Deletes from database
    - Attempts to delete embedding from ZeroDB
    - Returns 204 on success
    """
    # Fetch post to verify ownership
    posts = await zerodb_client.query_rows(
        table_name="posts",
        filter={
            "id": str(post_id),
            "user_id": str(current_user.id)
        },
        limit=1
    )

    if not posts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post {post_id} not found"
        )

    # Delete from ZeroDB
    await zerodb_client.delete_rows(
        table_name="posts",
        filter={"id": str(post_id)}
    )

    # Attempt to delete embedding (don't fail if this errors)
    try:
        vector_id = f"post_{post_id}"
        await embedding_service.delete_embedding(vector_id)
        logger.info(f"Deleted post embedding {vector_id}")
    except Exception as e:
        logger.error(f"Failed to delete post embedding: {e}")

    return None
