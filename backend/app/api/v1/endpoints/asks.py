"""
Asks API Endpoints
Implements CRUD operations for founder asks with semantic embedding support.

Endpoints:
- POST   /api/v1/asks - Create ask
- GET    /api/v1/asks - List asks (mine or all)
- GET    /api/v1/asks/search - Search asks semantically
- GET    /api/v1/asks/{ask_id} - Get ask
- PUT    /api/v1/asks/{ask_id} - Update ask
- PATCH  /api/v1/asks/{ask_id}/status - Update status
- DELETE /api/v1/asks/{ask_id} - Delete ask
"""
import logging
import time
from typing import Optional, List
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from app.core.database import get_db
from app.models.user import User
from app.models.ask import Ask, AskUrgency, AskStatus
from app.models.goal import Goal
from app.schemas.ask import (
    AskCreate,
    AskUpdate,
    AskStatusUpdate,
    AskResponse,
    AskListResponse
)
from app.services.embedding_service import embedding_service, EmbeddingServiceError
from app.services.safety_service import safety_service
from app.services.rlhf_service import rlhf_service, RLHFServiceError
from app.services.observability_service import observability_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/asks", tags=["asks"])


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


@router.post(
    "",
    response_model=AskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new ask",
    description="Create a new ask and generate semantic embedding synchronously"
)
async def create_ask(
    ask_data: AskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> AskResponse:
    """
    Create a new ask for the authenticated user.

    - Validates ask data
    - Scans for PII and scam content
    - Verifies goal ownership if goal_id provided
    - Persists to database
    - Creates semantic embedding (SYNC - critical for agent matching)
    - Returns created ask
    """
    # Scan ask description for safety issues
    try:
        safety_check = await safety_service.scan_text(
            text=ask_data.description,
            checks=["pii", "scam_detection"]
        )

        # Block high-confidence scams immediately
        if safety_check.is_scam and safety_check.scam_confidence > 0.7:
            logger.warning(
                f"Ask creation blocked for user {current_user.id}: "
                f"scam confidence {safety_check.scam_confidence}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ask contains suspicious content. Please revise and resubmit."
            )

        # Warn about PII (log but don't block)
        if safety_check.contains_pii:
            logger.warning(
                f"Ask for user {current_user.id} contains PII: {safety_check.pii_types}"
            )
            # In production, you could return a warning in the response

    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        # Log safety errors but don't block ask creation
        logger.error(f"Safety check failed for ask creation: {e}")

    # Validate goal ownership if goal_id provided
    if ask_data.goal_id:
        goal_result = await db.execute(
            select(Goal).where(
                Goal.id == ask_data.goal_id,
                Goal.user_id == current_user.id
            )
        )
        goal = goal_result.scalar_one_or_none()
        if not goal:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Goal {ask_data.goal_id} not found or does not belong to you"
            )

    # Create ask in database
    ask = Ask(
        user_id=current_user.id,
        goal_id=ask_data.goal_id,
        description=ask_data.description,
        urgency=ask_data.urgency
    )

    db.add(ask)
    await db.commit()
    await db.refresh(ask)

    # Create embedding synchronously (critical for agent matching)
    try:
        await embedding_service.create_ask_embedding(
            ask_id=ask.id,
            user_id=current_user.id,
            description=ask.description,
            urgency=ask.urgency.value,
            goal_id=ask.goal_id,
            additional_metadata={
                "status": ask.status.value
            }
        )
        logger.info(f"Created ask embedding for ask {ask.id}")
    except EmbeddingServiceError as e:
        logger.error(f"Failed to create ask embedding: {e}")
        # Don't rollback - ask creation should succeed even if embedding fails

    return AskResponse.model_validate(ask)


@router.get(
    "",
    response_model=AskListResponse,
    summary="List asks",
    description="Retrieve paginated list of asks (can filter by mine, status, urgency)"
)
async def list_asks(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    mine_only: bool = Query(True, description="Show only my asks"),
    status_filter: Optional[AskStatus] = Query(None, description="Filter by status"),
    urgency_filter: Optional[AskUrgency] = Query(None, description="Filter by urgency"),
    goal_id: Optional[UUID] = Query(None, description="Filter by goal"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> AskListResponse:
    """
    List asks with pagination and filtering.

    - Can view own asks or all asks
    - Filter by status, urgency, or linked goal
    - Orders by urgency (high first) then created_at (desc)
    """
    # Build query
    if mine_only:
        query = select(Ask).where(Ask.user_id == current_user.id)
    else:
        query = select(Ask)

    # Apply filters
    if status_filter is not None:
        query = query.where(Ask.status == status_filter)

    if urgency_filter is not None:
        query = query.where(Ask.urgency == urgency_filter)

    if goal_id is not None:
        query = query.where(Ask.goal_id == goal_id)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply ordering and pagination
    # Order by urgency: high > medium > low, then by created_at desc
    query = query.order_by(
        Ask.urgency.desc(),
        Ask.created_at.desc()
    ).offset((page - 1) * page_size).limit(page_size)

    # Execute query
    result = await db.execute(query)
    asks = result.scalars().all()

    return AskListResponse(
        asks=[AskResponse.model_validate(ask) for ask in asks],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total
    )


@router.get(
    "/{ask_id}",
    response_model=AskResponse,
    summary="Get a specific ask",
    description="Retrieve an ask by ID"
)
async def get_ask(
    ask_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> AskResponse:
    """
    Get a specific ask by ID.

    - Any authenticated user can view asks (public for matching)
    - Returns 404 if not found
    """
    result = await db.execute(
        select(Ask).where(Ask.id == ask_id)
    )
    ask = result.scalar_one_or_none()

    if not ask:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ask {ask_id} not found"
        )

    return AskResponse.model_validate(ask)


@router.put(
    "/{ask_id}",
    response_model=AskResponse,
    summary="Update an ask",
    description="Update ask fields and regenerate embedding if description changed"
)
async def update_ask(
    ask_id: UUID,
    ask_update: AskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> AskResponse:
    """
    Update an existing ask.

    - Verifies ask belongs to authenticated user
    - Scans for PII and scam content if description updated
    - Updates only provided fields
    - Regenerates embedding if description or urgency changed
    - Returns updated ask
    """
    # Scan description for safety issues if being updated
    update_data = ask_update.model_dump(exclude_unset=True)
    if "description" in update_data:
        try:
            safety_check = await safety_service.scan_text(
                text=update_data["description"],
                checks=["pii", "scam_detection"]
            )

            # Block high-confidence scams
            if safety_check.is_scam and safety_check.scam_confidence > 0.7:
                logger.warning(
                    f"Ask update blocked for user {current_user.id}: "
                    f"scam confidence {safety_check.scam_confidence}"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Ask contains suspicious content. Please revise and resubmit."
                )

            # Warn about PII
            if safety_check.contains_pii:
                logger.warning(
                    f"Ask update for user {current_user.id} contains PII: {safety_check.pii_types}"
                )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Safety check failed for ask update: {e}")

    # Fetch ask
    result = await db.execute(
        select(Ask).where(
            Ask.id == ask_id,
            Ask.user_id == current_user.id
        )
    )
    ask = result.scalar_one_or_none()

    if not ask:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ask {ask_id} not found"
        )

    # Validate goal ownership if updating goal_id
    update_data = ask_update.model_dump(exclude_unset=True)
    if "goal_id" in update_data and update_data["goal_id"] is not None:
        goal_result = await db.execute(
            select(Goal).where(
                Goal.id == update_data["goal_id"],
                Goal.user_id == current_user.id
            )
        )
        goal = goal_result.scalar_one_or_none()
        if not goal:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Goal {update_data['goal_id']} not found or does not belong to you"
            )

    # Track if embedding needs update
    needs_embedding_update = False

    # Update fields
    for field, value in update_data.items():
        if field in ["description", "urgency"]:
            needs_embedding_update = True
        setattr(ask, field, value)

    await db.commit()
    await db.refresh(ask)

    # Update embedding if needed
    if needs_embedding_update:
        try:
            await embedding_service.create_ask_embedding(
                ask_id=ask.id,
                user_id=current_user.id,
                description=ask.description,
                urgency=ask.urgency.value,
                goal_id=ask.goal_id,
                additional_metadata={
                    "status": ask.status.value
                }
            )
            logger.info(f"Updated ask embedding for ask {ask.id}")
        except EmbeddingServiceError as e:
            logger.error(f"Failed to update ask embedding: {e}")

    return AskResponse.model_validate(ask)


@router.patch(
    "/{ask_id}/status",
    response_model=AskResponse,
    summary="Update ask status",
    description="Update ask status to open, fulfilled, or closed"
)
async def update_ask_status(
    ask_id: UUID,
    status_update: AskStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> AskResponse:
    """
    Update ask status.

    - Verifies ask belongs to authenticated user
    - Updates status and sets fulfilled_at timestamp if applicable
    - Returns updated ask
    """
    # Fetch ask
    result = await db.execute(
        select(Ask).where(
            Ask.id == ask_id,
            Ask.user_id == current_user.id
        )
    )
    ask = result.scalar_one_or_none()

    if not ask:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ask {ask_id} not found"
        )

    # Update status using model methods
    if status_update.status == AskStatus.FULFILLED:
        ask.mark_fulfilled()
    elif status_update.status == AskStatus.CLOSED:
        ask.mark_closed()
    else:
        ask.status = status_update.status

    await db.commit()
    await db.refresh(ask)

    return AskResponse.model_validate(ask)


@router.delete(
    "/{ask_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an ask",
    description="Delete an ask and its embedding"
)
async def delete_ask(
    ask_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> None:
    """
    Delete an ask.

    - Verifies ask belongs to authenticated user
    - Deletes from database
    - Attempts to delete embedding from ZeroDB
    - Returns 204 on success
    """
    # Fetch ask
    result = await db.execute(
        select(Ask).where(
            Ask.id == ask_id,
            Ask.user_id == current_user.id
        )
    )
    ask = result.scalar_one_or_none()

    if not ask:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ask {ask_id} not found"
        )

    # Delete from database
    await db.delete(ask)
    await db.commit()

    # Attempt to delete embedding (don't fail if this errors)
    try:
        vector_id = f"ask_{ask_id}"
        await embedding_service.delete_embedding(vector_id)
        logger.info(f"Deleted ask embedding {vector_id}")
    except Exception as e:
        logger.error(f"Failed to delete ask embedding: {e}")

    return None


@router.get(
    "/search",
    response_model=AskListResponse,
    summary="Search for matching asks",
    description="Semantic search for asks that match your query"
)
async def search_asks(
    query: str = Query(..., description="Search query for finding similar asks"),
    urgency_filter: Optional[AskUrgency] = Query(None, description="Filter by urgency"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    min_similarity: float = Query(0.7, ge=0.0, le=1.0, description="Minimum similarity threshold"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> AskListResponse:
    """
    Search for asks semantically similar to the query.

    - Performs semantic search using embeddings
    - Filters by urgency if specified
    - Returns results with similarity scores
    - Tracks interaction for RLHF learning
    """
    try:
        # Build metadata filters
        metadata_filters = {}
        if urgency_filter:
            metadata_filters["urgency"] = urgency_filter.value

        # Perform semantic search
        start_time = time.time()
        results = await embedding_service.search_similar(
            query_text=query,
            entity_type="ask",
            metadata_filters=metadata_filters if metadata_filters else None,
            limit=limit,
            min_similarity=min_similarity
        )
        search_duration_ms = (time.time() - start_time) * 1000

        # Track embedding search cost
        await observability_service.track_embedding_cost(
            operation="search",
            tokens=len(query.split()) * 5,  # Rough estimate
            entity_type="ask"
        )

        # Extract ask IDs and scores
        ask_ids = []
        similarity_scores = []

        for result in results:
            metadata = result.get("metadata", {})
            source_id = metadata.get("source_id")
            if source_id:
                try:
                    ask_ids.append(UUID(source_id))
                    similarity_scores.append(result.get("similarity", 0.0))
                except ValueError:
                    logger.warning(f"Invalid UUID in source_id: {source_id}")
                    continue

        # Fetch asks from database
        asks_list = []
        if ask_ids:
            asks_result = await db.execute(
                select(Ask).where(Ask.id.in_(ask_ids))
            )
            asks = asks_result.scalars().all()

            # Create a mapping for ordering by similarity
            ask_map = {ask.id: ask for ask in asks}
            asks_list = [ask_map[ask_id] for ask_id in ask_ids if ask_id in ask_map]

        # Track RLHF interaction for learning
        try:
            await rlhf_service.track_ask_match(
                query_ask_id=uuid4(),  # Synthetic ID for search query
                query_ask_description=query,
                matched_ask_ids=ask_ids,
                similarity_scores=similarity_scores,
                context={
                    "user_id": str(current_user.id),
                    "urgency": urgency_filter.value if urgency_filter else None,
                    "search_duration_ms": search_duration_ms,
                    "min_similarity": min_similarity
                }
            )
        except RLHFServiceError as e:
            # Don't fail the request if RLHF tracking fails
            logger.warning(f"Failed to track RLHF interaction: {e}")

        # Track API performance
        await observability_service.track_api_call(
            endpoint="/asks/search",
            method="GET",
            duration_ms=search_duration_ms,
            status_code=200,
            user_id=str(current_user.id)
        )

        return AskListResponse(
            asks=[AskResponse.model_validate(ask) for ask in asks_list],
            total=len(asks_list),
            page=1,
            page_size=len(asks_list),
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
