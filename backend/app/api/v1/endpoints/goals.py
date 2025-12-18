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
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.security import decode_access_token
from app.services.zerodb_client import zerodb_client
from app.models.goal import GoalType
from app.schemas.goal import GoalCreate, GoalUpdate, GoalResponse, GoalListResponse
from app.services.embedding_service import embedding_service, EmbeddingServiceError
from app.services.rlhf_service import rlhf_service, RLHFServiceError
from app.services.observability_service import observability_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/goals", tags=["goals"])
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Extract user from JWT token and fetch from ZeroDB."""
    token = credentials.credentials
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    user = await zerodb_client.get_by_id(table_name="users", id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
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
    current_user: dict = Depends(get_current_user)
) -> GoalResponse:
    """
    Create a new goal for the authenticated user.

    - Validates goal data
    - Persists to database
    - Creates semantic embedding (SYNC - critical for matching)
    - Returns created goal
    """
    # Generate goal ID
    goal_id = str(uuid4())
    now = datetime.utcnow().isoformat()

    # Prepare goal data
    goal_dict = {
        "id": goal_id,
        "user_id": current_user["id"],
        "type": goal_data.type.value,
        "description": goal_data.description,
        "priority": goal_data.priority,
        "is_active": goal_data.is_active,
        "embedding_id": None,
        "created_at": now,
        "updated_at": now
    }

    # Insert goal into ZeroDB
    await zerodb_client.insert_rows(
        table_name="goals",
        rows=[goal_dict]
    )

    # Create embedding synchronously (critical for matching)
    embedding_id = None
    try:
        embedding_id = await embedding_service.create_goal_embedding(
            goal_id=UUID(goal_id),
            user_id=UUID(current_user["id"]),
            goal_type=goal_data.type.value,
            description=goal_data.description,
            priority=goal_data.priority,
            additional_metadata={
                "is_active": goal_data.is_active
            }
        )
        logger.info(f"Created goal embedding for goal {goal_id}")

        # Update goal with embedding_id
        await zerodb_client.update_rows(
            table_name="goals",
            filter={"id": goal_id},
            update={"$set": {
                "embedding_id": embedding_id,
                "updated_at": datetime.utcnow().isoformat()
            }}
        )
        goal_dict["embedding_id"] = embedding_id
    except EmbeddingServiceError as e:
        logger.error(f"Failed to create goal embedding: {e}")
        # Don't fail - goal creation should succeed even if embedding fails
        # Embedding can be retried later via background job

    return GoalResponse(**goal_dict)


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
    current_user: dict = Depends(get_current_user)
) -> GoalListResponse:
    """
    List goals for the authenticated user with pagination and filtering.

    - Supports pagination
    - Filter by active status
    - Filter by goal type
    - Orders by priority (desc) then created_at (desc)
    """
    # Build filter
    filter_dict = {"user_id": current_user["id"]}

    # Apply filters
    if is_active is not None:
        filter_dict["is_active"] = is_active

    if goal_type is not None:
        filter_dict["type"] = goal_type.value

    # Get all matching goals for total count
    # Note: ZeroDB doesn't support count operation, so we query all and count
    all_goals = await zerodb_client.query_rows(
        table_name="goals",
        filter=filter_dict,
        limit=1000  # Reasonable upper limit
    )
    total = len(all_goals)

    # Sort by priority (desc) then created_at (desc)
    all_goals.sort(
        key=lambda g: (
            -g.get("priority", 0),
            g.get("created_at", "")
        ),
        reverse=True
    )

    # Apply pagination
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    goals = all_goals[start_idx:end_idx]

    return GoalListResponse(
        goals=[GoalResponse(**goal) for goal in goals],
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
    current_user: dict = Depends(get_current_user)
) -> GoalResponse:
    """
    Get a specific goal by ID.

    - Verifies goal belongs to authenticated user
    - Returns 404 if not found or doesn't belong to user
    """
    # Query goal from ZeroDB
    goals = await zerodb_client.query_rows(
        table_name="goals",
        filter={
            "id": str(goal_id),
            "user_id": current_user["id"]
        },
        limit=1
    )

    if not goals:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Goal {goal_id} not found"
        )

    return GoalResponse(**goals[0])


@router.put(
    "/{goal_id}",
    response_model=GoalResponse,
    summary="Update a goal",
    description="Update goal fields and regenerate embedding if description/type changed"
)
async def update_goal(
    goal_id: UUID,
    goal_update: GoalUpdate,
    current_user: dict = Depends(get_current_user)
) -> GoalResponse:
    """
    Update an existing goal.

    - Verifies goal belongs to authenticated user
    - Updates only provided fields
    - Regenerates embedding if description or type changed
    - Returns updated goal
    """
    # Fetch goal
    goals = await zerodb_client.query_rows(
        table_name="goals",
        filter={
            "id": str(goal_id),
            "user_id": current_user["id"]
        },
        limit=1
    )

    if not goals:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Goal {goal_id} not found"
        )

    goal = goals[0]

    # Track if embedding needs update
    needs_embedding_update = False

    # Prepare update fields
    update_data = goal_update.model_dump(exclude_unset=True)
    update_dict = {}

    for field, value in update_data.items():
        if field in ["type", "description"]:
            needs_embedding_update = True
        # Convert enum to value if needed
        if hasattr(value, 'value'):
            update_dict[field] = value.value
        else:
            update_dict[field] = value

    # Add updated_at timestamp
    update_dict["updated_at"] = datetime.utcnow().isoformat()

    # Update goal in ZeroDB
    await zerodb_client.update_rows(
        table_name="goals",
        filter={"id": str(goal_id)},
        update={"$set": update_dict}
    )

    # Merge updates into goal dict
    goal.update(update_dict)

    # Update embedding if needed
    if needs_embedding_update:
        try:
            embedding_id = await embedding_service.create_goal_embedding(
                goal_id=goal_id,
                user_id=UUID(current_user["id"]),
                goal_type=goal.get("type"),
                description=goal.get("description"),
                priority=goal.get("priority", 0),
                additional_metadata={
                    "is_active": goal.get("is_active", True)
                }
            )
            logger.info(f"Updated goal embedding for goal {goal_id}")

            # Update embedding_id in ZeroDB
            await zerodb_client.update_rows(
                table_name="goals",
                filter={"id": str(goal_id)},
                update={"$set": {
                    "embedding_id": embedding_id,
                    "updated_at": datetime.utcnow().isoformat()
                }}
            )
            goal["embedding_id"] = embedding_id
        except EmbeddingServiceError as e:
            logger.error(f"Failed to update goal embedding: {e}")

    return GoalResponse(**goal)


@router.delete(
    "/{goal_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a goal",
    description="Delete a goal and its embedding"
)
async def delete_goal(
    goal_id: UUID,
    current_user: dict = Depends(get_current_user)
) -> None:
    """
    Delete a goal.

    - Verifies goal belongs to authenticated user
    - Deletes from database (cascades to asks)
    - Attempts to delete embedding from ZeroDB
    - Returns 204 on success
    """
    # Fetch goal
    goals = await zerodb_client.query_rows(
        table_name="goals",
        filter={
            "id": str(goal_id),
            "user_id": current_user["id"]
        },
        limit=1
    )

    if not goals:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Goal {goal_id} not found"
        )

    # Delete from ZeroDB
    await zerodb_client.delete_rows(
        table_name="goals",
        filter={"id": str(goal_id)}
    )

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
    current_user: dict = Depends(get_current_user)
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
                    goal_ids.append(source_id)
                    similarity_scores.append(result.get("similarity", 0.0))
                except ValueError:
                    logger.warning(f"Invalid UUID in source_id: {source_id}")
                    continue

        # Fetch goals from ZeroDB
        goals_list = []
        if goal_ids:
            # Query goals in batches (ZeroDB limitation)
            for goal_id in goal_ids:
                goal = await zerodb_client.get_by_id(
                    table_name="goals",
                    id=goal_id
                )
                if goal:
                    goals_list.append(goal)

        # Track RLHF interaction for learning
        try:
            await rlhf_service.track_goal_match(
                query_goal_id=uuid4(),  # Synthetic ID for search query
                query_goal_description=query,
                matched_goal_ids=[UUID(gid) for gid in goal_ids],
                similarity_scores=similarity_scores,
                context={
                    "user_id": current_user["id"],
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
            user_id=current_user["id"]
        )

        return GoalListResponse(
            goals=[GoalResponse(**goal) for goal in goals_list],
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
            context={"query": query, "user_id": current_user["id"]}
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Semantic search temporarily unavailable"
        )
