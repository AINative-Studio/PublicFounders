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
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.models.ask import AskUrgency, AskStatus
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
from app.services.zerodb_client import zerodb_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/asks", tags=["asks"])


# TODO: Replace with actual auth dependency from Sprint 1
async def get_current_user() -> Dict[str, Any]:
    """
    Mock auth dependency - replace with Sprint 1 implementation.
    Returns a dictionary representing a user from ZeroDB.
    """
    users = await zerodb_client.query_rows(
        table_name="users",
        limit=1
    )
    if not users:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return users[0]


@router.post(
    "",
    response_model=AskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new ask",
    description="Create a new ask and generate semantic embedding synchronously"
)
async def create_ask(
    ask_data: AskCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
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
    user_id = current_user["id"]

    # Scan ask description for safety issues
    try:
        safety_check = await safety_service.scan_text(
            text=ask_data.description,
            checks=["pii", "scam_detection"]
        )

        # Block high-confidence scams immediately
        if safety_check.is_scam and safety_check.scam_confidence > 0.7:
            logger.warning(
                f"Ask creation blocked for user {user_id}: "
                f"scam confidence {safety_check.scam_confidence}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ask contains suspicious content. Please revise and resubmit."
            )

        # Warn about PII (log but don't block)
        if safety_check.contains_pii:
            logger.warning(
                f"Ask for user {user_id} contains PII: {safety_check.pii_types}"
            )
            # In production, you could return a warning in the response

    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        # Log safety errors but don't block ask creation
        logger.error(f"Safety check failed for ask creation: {e}")

    # Validate goal ownership if goal_id provided
    if ask_data.goal_id:
        goal = await zerodb_client.get_by_id(
            table_name="goals",
            id=str(ask_data.goal_id)
        )
        if not goal or goal["user_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Goal {ask_data.goal_id} not found or does not belong to you"
            )

    # Create ask ID
    ask_id = str(uuid4())
    now = datetime.utcnow().isoformat()

    # Prepare ask data
    ask_data_dict = {
        "id": ask_id,
        "user_id": user_id,
        "description": ask_data.description,
        "urgency": ask_data.urgency.value,
        "status": AskStatus.OPEN.value,
        "goal_id": str(ask_data.goal_id) if ask_data.goal_id else None,
        "fulfilled_at": None,
        "embedding_id": None,
        "created_at": now,
        "updated_at": now
    }

    # Insert ask into ZeroDB
    await zerodb_client.insert_rows(
        table_name="asks",
        rows=[ask_data_dict]
    )

    # Create embedding synchronously (critical for agent matching)
    try:
        await embedding_service.create_ask_embedding(
            ask_id=UUID(ask_id),
            user_id=UUID(user_id),
            description=ask_data.description,
            urgency=ask_data.urgency.value,
            goal_id=UUID(ask_data.goal_id) if ask_data.goal_id else None,
            additional_metadata={
                "status": AskStatus.OPEN.value
            }
        )
        logger.info(f"Created ask embedding for ask {ask_id}")
    except EmbeddingServiceError as e:
        logger.error(f"Failed to create ask embedding: {e}")
        # Don't rollback - ask creation should succeed even if embedding fails

    # Fetch created ask for response
    created_ask = await zerodb_client.get_by_id(
        table_name="asks",
        id=ask_id
    )

    return AskResponse(**created_ask)


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
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> AskListResponse:
    """
    List asks with pagination and filtering.

    - Can view own asks or all asks
    - Filter by status, urgency, or linked goal
    - Orders by urgency (high first) then created_at (desc)
    """
    user_id = current_user["id"]

    # Build filter
    filter_dict = {}
    if mine_only:
        filter_dict["user_id"] = user_id

    if status_filter is not None:
        filter_dict["status"] = status_filter.value

    if urgency_filter is not None:
        filter_dict["urgency"] = urgency_filter.value

    if goal_id is not None:
        filter_dict["goal_id"] = str(goal_id)

    # First, get total count with same filter (without pagination)
    all_asks = await zerodb_client.query_rows(
        table_name="asks",
        filter=filter_dict,
        limit=10000  # Large limit to get count
    )
    total = len(all_asks)

    # Apply sorting: urgency (high > medium > low), then created_at (desc)
    urgency_order = {"high": 3, "medium": 2, "low": 1}
    sorted_asks = sorted(
        all_asks,
        key=lambda x: (
            urgency_order.get(x.get("urgency", "medium"), 2),
            x.get("created_at", "")
        ),
        reverse=True
    )

    # Apply pagination
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_asks = sorted_asks[start_idx:end_idx]

    return AskListResponse(
        asks=[AskResponse(**ask) for ask in paginated_asks],
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
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> AskResponse:
    """
    Get a specific ask by ID.

    - Any authenticated user can view asks (public for matching)
    - Returns 404 if not found
    """
    ask = await zerodb_client.get_by_id(
        table_name="asks",
        id=str(ask_id)
    )

    if not ask:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ask {ask_id} not found"
        )

    return AskResponse(**ask)


@router.put(
    "/{ask_id}",
    response_model=AskResponse,
    summary="Update an ask",
    description="Update ask fields and regenerate embedding if description changed"
)
async def update_ask(
    ask_id: UUID,
    ask_update: AskUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> AskResponse:
    """
    Update an existing ask.

    - Verifies ask belongs to authenticated user
    - Scans for PII and scam content if description updated
    - Updates only provided fields
    - Regenerates embedding if description or urgency changed
    - Returns updated ask
    """
    user_id = current_user["id"]

    # Get update data
    update_data = ask_update.model_dump(exclude_unset=True)

    # Scan description for safety issues if being updated
    if "description" in update_data:
        try:
            safety_check = await safety_service.scan_text(
                text=update_data["description"],
                checks=["pii", "scam_detection"]
            )

            # Block high-confidence scams
            if safety_check.is_scam and safety_check.scam_confidence > 0.7:
                logger.warning(
                    f"Ask update blocked for user {user_id}: "
                    f"scam confidence {safety_check.scam_confidence}"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Ask contains suspicious content. Please revise and resubmit."
                )

            # Warn about PII
            if safety_check.contains_pii:
                logger.warning(
                    f"Ask update for user {user_id} contains PII: {safety_check.pii_types}"
                )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Safety check failed for ask update: {e}")

    # Fetch ask
    ask = await zerodb_client.get_by_id(
        table_name="asks",
        id=str(ask_id)
    )

    if not ask or ask["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ask {ask_id} not found"
        )

    # Validate goal ownership if updating goal_id
    if "goal_id" in update_data and update_data["goal_id"] is not None:
        goal = await zerodb_client.get_by_id(
            table_name="goals",
            id=str(update_data["goal_id"])
        )
        if not goal or goal["user_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Goal {update_data['goal_id']} not found or does not belong to you"
            )

    # Track if embedding needs update
    needs_embedding_update = False

    # Prepare update dict for ZeroDB
    zerodb_update = {}
    for field, value in update_data.items():
        if field in ["description", "urgency"]:
            needs_embedding_update = True

        # Convert enum values to strings
        if hasattr(value, "value"):
            zerodb_update[field] = value.value
        elif isinstance(value, UUID):
            zerodb_update[field] = str(value)
        else:
            zerodb_update[field] = value

    # Add updated_at timestamp
    zerodb_update["updated_at"] = datetime.utcnow().isoformat()

    # Update ask in ZeroDB
    await zerodb_client.update_rows(
        table_name="asks",
        filter={"id": str(ask_id)},
        update={"$set": zerodb_update}
    )

    # Fetch updated ask
    updated_ask = await zerodb_client.get_by_id(
        table_name="asks",
        id=str(ask_id)
    )

    # Update embedding if needed
    if needs_embedding_update:
        try:
            await embedding_service.create_ask_embedding(
                ask_id=UUID(str(ask_id)),
                user_id=UUID(user_id),
                description=updated_ask["description"],
                urgency=updated_ask["urgency"],
                goal_id=UUID(updated_ask["goal_id"]) if updated_ask.get("goal_id") else None,
                additional_metadata={
                    "status": updated_ask["status"]
                }
            )
            logger.info(f"Updated ask embedding for ask {ask_id}")
        except EmbeddingServiceError as e:
            logger.error(f"Failed to update ask embedding: {e}")

    return AskResponse(**updated_ask)


@router.patch(
    "/{ask_id}/status",
    response_model=AskResponse,
    summary="Update ask status",
    description="Update ask status to open, fulfilled, or closed"
)
async def update_ask_status(
    ask_id: UUID,
    status_update: AskStatusUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> AskResponse:
    """
    Update ask status.

    - Verifies ask belongs to authenticated user
    - Updates status and sets fulfilled_at timestamp if applicable
    - Returns updated ask
    """
    user_id = current_user["id"]

    # Fetch ask
    ask = await zerodb_client.get_by_id(
        table_name="asks",
        id=str(ask_id)
    )

    if not ask or ask["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ask {ask_id} not found"
        )

    # Prepare status update
    update_dict = {
        "status": status_update.status.value,
        "updated_at": datetime.utcnow().isoformat()
    }

    # Set fulfilled_at if status is FULFILLED
    if status_update.status == AskStatus.FULFILLED:
        update_dict["fulfilled_at"] = datetime.utcnow().isoformat()
    elif status_update.status == AskStatus.CLOSED:
        # Clear fulfilled_at if closing without fulfillment
        if ask.get("fulfilled_at") is None:
            update_dict["fulfilled_at"] = None

    # Update ask in ZeroDB
    await zerodb_client.update_rows(
        table_name="asks",
        filter={"id": str(ask_id)},
        update={"$set": update_dict}
    )

    # Fetch updated ask
    updated_ask = await zerodb_client.get_by_id(
        table_name="asks",
        id=str(ask_id)
    )

    return AskResponse(**updated_ask)


@router.delete(
    "/{ask_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an ask",
    description="Delete an ask and its embedding"
)
async def delete_ask(
    ask_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> None:
    """
    Delete an ask.

    - Verifies ask belongs to authenticated user
    - Deletes from database
    - Attempts to delete embedding from ZeroDB
    - Returns 204 on success
    """
    user_id = current_user["id"]

    # Fetch ask
    ask = await zerodb_client.get_by_id(
        table_name="asks",
        id=str(ask_id)
    )

    if not ask or ask["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ask {ask_id} not found"
        )

    # Delete from database
    await zerodb_client.delete_rows(
        table_name="asks",
        filter={"id": str(ask_id)}
    )

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
    status_filter: Optional[AskStatus] = Query(None, description="Filter by status"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    min_similarity: float = Query(0.7, ge=0.0, le=1.0, description="Minimum similarity threshold"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> AskListResponse:
    """
    Search for asks semantically similar to the query.

    - Performs semantic search using embeddings
    - Filters by urgency and/or status if specified
    - Returns results with similarity scores
    - Tracks interaction for RLHF learning
    """
    user_id = current_user["id"]

    try:
        # Build metadata filters
        metadata_filters = {}
        if urgency_filter:
            metadata_filters["urgency"] = urgency_filter.value
        if status_filter:
            metadata_filters["status"] = status_filter.value

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
                    ask_ids.append(source_id)  # Keep as string
                    similarity_scores.append(result.get("similarity", 0.0))
                except ValueError:
                    logger.warning(f"Invalid UUID in source_id: {source_id}")
                    continue

        # Fetch asks from database
        asks_list = []
        if ask_ids:
            # Query ZeroDB for matching asks
            all_asks = await zerodb_client.query_rows(
                table_name="asks",
                limit=1000  # Large limit to get all matches
            )

            # Filter to matching IDs and create mapping
            ask_map = {ask["id"]: ask for ask in all_asks if ask["id"] in ask_ids}

            # Maintain order by similarity
            asks_list = [ask_map[ask_id] for ask_id in ask_ids if ask_id in ask_map]

        # Track RLHF interaction for learning
        try:
            await rlhf_service.track_ask_match(
                query_ask_id=uuid4(),  # Synthetic ID for search query
                query_ask_description=query,
                matched_ask_ids=[UUID(ask_id) for ask_id in ask_ids],
                similarity_scores=similarity_scores,
                context={
                    "user_id": user_id,
                    "urgency": urgency_filter.value if urgency_filter else None,
                    "status": status_filter.value if status_filter else None,
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
            user_id=user_id
        )

        return AskListResponse(
            asks=[AskResponse(**ask) for ask in asks_list],
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
            context={"query": query, "user_id": user_id}
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Semantic search temporarily unavailable"
        )
