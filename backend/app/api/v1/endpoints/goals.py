"""
Goals API Endpoints
Implements CRUD operations for founder goals with semantic embedding support.

Endpoints:
- POST   /api/v1/goals - Create goal
- GET    /api/v1/goals - List my goals
- GET    /api/v1/goals/search - Search goals semantically
- GET    /api/v1/goals/{goal_id} - Get goal
- PUT    /api/v1/goals/{goal_id} - Update goal
- DELETE /api/v1/goals/{goal_id} - Delete goal
"""
import logging
import time
from typing import List, Optional
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.models.user import User
from app.models.goal import Goal, GoalType
from app.schemas.goal import GoalCreate, GoalUpdate, GoalResponse, GoalListResponse
from app.services.embedding_service import embedding_service, EmbeddingServiceError
from app.services.rlhf_service import rlhf_service, RLHFServiceError
from app.services.observability_service import observability_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/goals", tags=["goals"])


# TODO: Replace with actual auth dependency from Sprint 1
async def get_current_user(db: AsyncSession = Depends(get_db)) -> User:
    """Mock auth dependency - replace with Sprint 1 implementation."""
    # For now, return first user in database
    result = await db.execute(select(User).limit(1))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return user


@router.post(
    "",
    response_model=GoalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new goal",
    description="Create a new goal and generate semantic embedding synchronously"
)
async def create_goal(
    goal_data: GoalCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> GoalResponse:
    """
    Create a new goal for the authenticated user.

    - Validates goal data
    - Persists to database
    - Creates semantic embedding (SYNC - critical for matching)
    - Returns created goal
    """
    # Create goal in database
    goal = Goal(
        user_id=current_user.id,
        type=goal_data.type,
        description=goal_data.description,
        priority=goal_data.priority,
        is_active=goal_data.is_active
    )

    db.add(goal)
    await db.commit()
    await db.refresh(goal)

    # Create embedding synchronously (critical for matching)
    try:
        await embedding_service.create_goal_embedding(
            goal_id=goal.id,
            user_id=current_user.id,
            goal_type=goal.type.value,
            description=goal.description,
            priority=goal.priority,
            additional_metadata={
                "is_active": goal.is_active
            }
        )
        logger.info(f"Created goal embedding for goal {goal.id}")
    except EmbeddingServiceError as e:
        logger.error(f"Failed to create goal embedding: {e}")
        # Don't rollback - goal creation should succeed even if embedding fails
        # Embedding can be retried later via background job

    return GoalResponse.model_validate(goal)


@router.get(
    "",
    response_model=GoalListResponse,
    summary="List my goals",
    description="Retrieve paginated list of goals for authenticated user"
)
async def list_goals(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    goal_type: Optional[GoalType] = Query(None, description="Filter by goal type"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> GoalListResponse:
    """
    List goals for the authenticated user with pagination and filtering.

    - Supports pagination
    - Filter by active status
    - Filter by goal type
    - Orders by priority (desc) then created_at (desc)
    """
    # Build query
    query = select(Goal).where(Goal.user_id == current_user.id)

    # Apply filters
    if is_active is not None:
        query = query.where(Goal.is_active == is_active)

    if goal_type is not None:
        query = query.where(Goal.type == goal_type)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply ordering and pagination
    query = query.order_by(
        Goal.priority.desc(),
        Goal.created_at.desc()
    ).offset((page - 1) * page_size).limit(page_size)

    # Execute query
    result = await db.execute(query)
    goals = result.scalars().all()

    return GoalListResponse(
        goals=[GoalResponse.model_validate(goal) for goal in goals],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total
    )


@router.get(
    "/{goal_id}",
    response_model=GoalResponse,
    summary="Get a specific goal",
    description="Retrieve a goal by ID (must belong to authenticated user)"
)
async def get_goal(
    goal_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> GoalResponse:
    """
    Get a specific goal by ID.

    - Verifies goal belongs to authenticated user
    - Returns 404 if not found or doesn't belong to user
    """
    result = await db.execute(
        select(Goal).where(
            Goal.id == goal_id,
            Goal.user_id == current_user.id
        )
    )
    goal = result.scalar_one_or_none()

    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Goal {goal_id} not found"
        )

    return GoalResponse.model_validate(goal)


@router.put(
    "/{goal_id}",
    response_model=GoalResponse,
    summary="Update a goal",
    description="Update goal fields and regenerate embedding if description/type changed"
)
async def update_goal(
    goal_id: UUID,
    goal_update: GoalUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> GoalResponse:
    """
    Update an existing goal.

    - Verifies goal belongs to authenticated user
    - Updates only provided fields
    - Regenerates embedding if description or type changed
    - Returns updated goal
    """
    # Fetch goal
    result = await db.execute(
        select(Goal).where(
            Goal.id == goal_id,
            Goal.user_id == current_user.id
        )
    )
    goal = result.scalar_one_or_none()

    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Goal {goal_id} not found"
        )

    # Track if embedding needs update
    needs_embedding_update = False

    # Update fields
    update_data = goal_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field in ["type", "description"]:
            needs_embedding_update = True
        setattr(goal, field, value)

    await db.commit()
    await db.refresh(goal)

    # Update embedding if needed
    if needs_embedding_update:
        try:
            await embedding_service.create_goal_embedding(
                goal_id=goal.id,
                user_id=current_user.id,
                goal_type=goal.type.value,
                description=goal.description,
                priority=goal.priority,
                additional_metadata={
                    "is_active": goal.is_active
                }
            )
            logger.info(f"Updated goal embedding for goal {goal.id}")
        except EmbeddingServiceError as e:
            logger.error(f"Failed to update goal embedding: {e}")

    return GoalResponse.model_validate(goal)


@router.delete(
    "/{goal_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a goal",
    description="Delete a goal and its embedding"
)
async def delete_goal(
    goal_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> None:
    """
    Delete a goal.

    - Verifies goal belongs to authenticated user
    - Deletes from database (cascades to asks)
    - Attempts to delete embedding from ZeroDB
    - Returns 204 on success
    """
    # Fetch goal
    result = await db.execute(
        select(Goal).where(
            Goal.id == goal_id,
            Goal.user_id == current_user.id
        )
    )
    goal = result.scalar_one_or_none()

    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Goal {goal_id} not found"
        )

    # Delete from database
    await db.delete(goal)
    await db.commit()

    # Attempt to delete embedding (don't fail if this errors)
    try:
        vector_id = f"goal_{goal_id}"
        await embedding_service.delete_embedding(vector_id)
        logger.info(f"Deleted goal embedding {vector_id}")
    except Exception as e:
        logger.error(f"Failed to delete goal embedding: {e}")

    return None


@router.get(
    "/search",
    response_model=GoalListResponse,
    summary="Search for matching goals",
    description="Semantic search for goals that match your description"
)
async def search_goals(
    query: str = Query(..., description="Search query for finding similar goals"),
    goal_type: Optional[GoalType] = Query(None, description="Filter by goal type"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    min_similarity: float = Query(0.7, ge=0.0, le=1.0, description="Minimum similarity threshold"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> GoalListResponse:
    """
    Search for goals semantically similar to the query.

    - Performs semantic search using embeddings
    - Filters by goal type if specified
    - Returns results with similarity scores
    - Tracks interaction for RLHF learning
    """
    try:
        # Build metadata filters
        metadata_filters = {}
        if goal_type:
            metadata_filters["goal_type"] = goal_type.value

        # Perform semantic search
        start_time = time.time()
        results = await embedding_service.search_similar(
            query_text=query,
            entity_type="goal",
            metadata_filters=metadata_filters if metadata_filters else None,
            limit=limit,
            min_similarity=min_similarity
        )
        search_duration_ms = (time.time() - start_time) * 1000

        # Track embedding search cost
        await observability_service.track_embedding_cost(
            operation="search",
            tokens=len(query.split()) * 5,  # Rough estimate
            entity_type="goal"
        )

        # Extract goal IDs and scores
        goal_ids = []
        similarity_scores = []

        for result in results:
            metadata = result.get("metadata", {})
            source_id = metadata.get("source_id")
            if source_id:
                try:
                    goal_ids.append(UUID(source_id))
                    similarity_scores.append(result.get("similarity", 0.0))
                except ValueError:
                    logger.warning(f"Invalid UUID in source_id: {source_id}")
                    continue

        # Fetch goals from database
        goals_list = []
        if goal_ids:
            goals_result = await db.execute(
                select(Goal).where(Goal.id.in_(goal_ids))
            )
            goals = goals_result.scalars().all()

            # Create a mapping for ordering by similarity
            goal_map = {goal.id: goal for goal in goals}
            goals_list = [goal_map[goal_id] for goal_id in goal_ids if goal_id in goal_map]

        # Track RLHF interaction for learning
        try:
            await rlhf_service.track_goal_match(
                query_goal_id=uuid4(),  # Synthetic ID for search query
                query_goal_description=query,
                matched_goal_ids=goal_ids,
                similarity_scores=similarity_scores,
                context={
                    "user_id": str(current_user.id),
                    "goal_type": goal_type.value if goal_type else None,
                    "search_duration_ms": search_duration_ms,
                    "min_similarity": min_similarity
                }
            )
        except RLHFServiceError as e:
            # Don't fail the request if RLHF tracking fails
            logger.warning(f"Failed to track RLHF interaction: {e}")

        # Track API performance
        await observability_service.track_api_call(
            endpoint="/goals/search",
            method="GET",
            duration_ms=search_duration_ms,
            status_code=200,
            user_id=str(current_user.id)
        )

        return GoalListResponse(
            goals=[GoalResponse.model_validate(goal) for goal in goals_list],
            total=len(goals_list),
            page=1,
            page_size=len(goals_list),
            has_more=False
        )

    except EmbeddingServiceError as e:
        logger.error(f"Semantic search failed: {e}")

        # Track error
        await observability_service.track_error(
            error_type="embedding_search_error",
            error_message=str(e),
            severity="high",
            context={"query": query, "user_id": str(current_user.id)}
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Semantic search temporarily unavailable"
        )
