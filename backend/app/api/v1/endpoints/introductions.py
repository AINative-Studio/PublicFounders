"""
Introductions API Endpoints

Implements introduction request and execution system for founder connections.

Endpoints:
- POST   /api/v1/introductions/request - Request an introduction
- GET    /api/v1/introductions/suggestions - Get AI-powered introduction suggestions (Story 7.1)
- GET    /api/v1/introductions/received - Get received introduction requests
- GET    /api/v1/introductions/sent - Get sent introduction requests
- GET    /api/v1/introductions/{intro_id} - Get specific introduction
- PUT    /api/v1/introductions/{intro_id}/respond - Respond to introduction
- PUT    /api/v1/introductions/{intro_id}/complete - Mark introduction complete
"""
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.services.introduction_service import (
    introduction_service,
    IntroductionServiceError,
    IntroductionOutcome
)
from app.services.matching_service import matching_service, MatchingServiceError
from app.services.cache_service import cache_service
from app.services.rlhf_service import rlhf_service
from app.services.zerodb_client import zerodb_client
from app.schemas.introduction import (
    IntroductionRequest,
    IntroductionResponseRequest,
    IntroductionCompletion,
    IntroductionResponse,
    IntroductionListResponse,
    IntroductionSuggestion,
    GoalHelper,
    AskMatcher
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/introductions", tags=["introductions"])


# TODO: Replace with actual auth dependency from Sprint 1
async def get_current_user() -> dict:
    """Mock auth dependency - replace with Sprint 1 implementation."""
    # For now, return first user from ZeroDB
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


@router.get(
    "/suggestions",
    response_model=List[IntroductionSuggestion],
    summary="Get AI-powered introduction suggestions",
    description="""
    Get personalized introduction suggestions based on your goals and asks.

    Uses semantic matching to find founders who:
    - Are working on similar goals
    - Can help with your asks
    - Have complementary expertise
    - Are looking for what you offer

    Suggestions are ranked by match quality (relevance, trust, reciprocity).

    - **limit**: Maximum number of suggestions (1-50, default 20)
    - **min_score**: Minimum match score threshold (0.0-1.0, default 0.6)
    - **match_type**: Type of matching - "goal_based", "ask_based", or "all" (default "all")

    Results are cached for 1 hour for performance.
    """
)
async def get_introduction_suggestions(
    limit: int = Query(20, ge=1, le=50, description="Maximum number of suggestions"),
    min_score: float = Query(0.6, ge=0.0, le=1.0, description="Minimum match score threshold"),
    match_type: str = Query("all", pattern="^(goal_based|ask_based|all)$", description="Type of matching"),
    current_user: dict = Depends(get_current_user)
) -> List[IntroductionSuggestion]:
    """
    Get personalized introduction suggestions using semantic matching.

    This endpoint:
    1. Retrieves user's active goals and asks
    2. Performs vector search for semantically similar founders
    3. Calculates multi-dimensional match scores (relevance, trust, reciprocity)
    4. Generates human-readable reasoning for each match
    5. Returns ranked suggestions

    Performance:
    - Cache hit: < 200ms
    - Cache miss: 1-3s (depends on goal/ask count)
    - Results cached for 1 hour

    RLHF Tracking:
    - Tracks which suggestions are viewed
    - Will track click-through and intro request rates
    """
    try:
        user_id = UUID(current_user["id"])

        # Check cache first
        cache_key = f"intro_suggestions:{user_id}:{match_type}:{min_score}"
        cached = await cache_service.get_cached_discovery(
            user_id=user_id,
            goal_descriptions=[cache_key]  # Use cache key as identifier
        )

        if cached and isinstance(cached, list):
            logger.info(f"Cache HIT for intro suggestions (user {user_id})")
            # Track cache hit interaction
            await rlhf_service.track_goal_match(
                query_goal_id=user_id,
                query_goal_description=f"intro_suggestions_{match_type}",
                matched_goal_ids=[],
                similarity_scores=[],
                context={
                    "cache_hit": True,
                    "match_type": match_type,
                    "min_score": min_score
                }
            )
            return cached[:limit]

        # Generate suggestions
        logger.info(
            f"Generating intro suggestions for user {user_id} "
            f"(type={match_type}, min_score={min_score})"
        )

        suggestions = await matching_service.suggest_introductions(
            user_id=user_id,
            limit=limit,
            min_score=min_score,
            match_type=match_type
        )

        # Convert to IntroductionSuggestion schema
        suggestion_responses = []
        for suggestion in suggestions:
            suggestion_responses.append(
                IntroductionSuggestion(
                    target_user_id=UUID(suggestion["target_user_id"]),
                    target_name=suggestion["target_name"],
                    target_headline=suggestion.get("target_headline"),
                    target_location=suggestion.get("target_location"),
                    match_score=suggestion["match_score"],
                    reasoning=suggestion["reasoning"],
                    matching_goals=suggestion.get("matching_goals", []),
                    matching_asks=suggestion.get("matching_asks", [])
                )
            )

        # Cache results (1 hour TTL)
        if suggestion_responses:
            # Convert to dict for caching
            cache_data = [s.model_dump() for s in suggestion_responses]
            await cache_service.cache_discovery_results(
                user_id=user_id,
                goal_descriptions=[cache_key],
                results=cache_data,
                ttl_seconds=3600
            )
            logger.info(f"Cached {len(suggestion_responses)} intro suggestions")

        # Track interaction for RLHF
        matched_ids = [UUID(s["target_user_id"]) for s in suggestions]
        scores = [s["match_score"]["overall_score"] for s in suggestions]

        await rlhf_service.track_goal_match(
            query_goal_id=user_id,
            query_goal_description=f"intro_suggestions_{match_type}",
            matched_goal_ids=matched_ids,
            similarity_scores=scores,
            context={
                "match_type": match_type,
                "min_score": min_score,
                "total_suggestions": len(suggestion_responses),
                "cache_miss": True
            }
        )

        logger.info(
            f"Generated {len(suggestion_responses)} intro suggestions for user {user_id}"
        )

        return suggestion_responses

    except MatchingServiceError as e:
        logger.error(f"Matching service error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate suggestions: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_introduction_suggestions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch introduction suggestions"
        )


@router.post(
    "/request",
    response_model=IntroductionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Request an introduction to another founder",
    description="""
    Request an introduction to another founder.

    - **target_id**: Founder you want to be introduced to
    - **message**: Your personalized message explaining why (10-500 chars)
    - **connector_id**: Optional mutual connection to facilitate
    - **context**: Optional additional context (shared goals, etc.)

    The introduction will be pending until the target responds.
    Automatically expires after 7 days if no response.
    """
)
async def request_introduction(
    request: IntroductionRequest,
    current_user: dict = Depends(get_current_user)
) -> IntroductionResponse:
    """
    Request an introduction to another founder.

    Creates a pending introduction request that the target can accept or decline.
    Generates semantic embedding for the request message for future matching.
    Tracks the request in RLHF system for learning.
    """
    try:
        introduction = await introduction_service.request_introduction(
            requester_id=UUID(current_user["id"]),
            target_id=request.target_id,
            message=request.message,
            connector_id=request.connector_id,
            context=request.context
        )

        logger.info(
            f"User {current_user['id']} requested introduction to {request.target_id}"
        )

        return IntroductionResponse(**introduction)

    except IntroductionServiceError as e:
        logger.warning(f"Introduction request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error in request_introduction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create introduction request"
        )


@router.get(
    "/received",
    response_model=List[IntroductionResponse],
    summary="Get introduction requests you've received",
    description="""
    Get introduction requests that others have sent to you.

    - **status**: Optional filter by status (pending, accepted, declined, completed, expired)
    - **limit**: Maximum number of results (1-50, default 20)
    - **offset**: Pagination offset (default 0)

    Results are sorted by request date (newest first).
    """
)
async def get_received_introductions(
    status: Optional[str] = Query(
        None,
        pattern="^(pending|accepted|declined|completed|expired)$",
        description="Filter by introduction status"
    ),
    limit: int = Query(20, ge=1, le=50, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: dict = Depends(get_current_user)
) -> List[IntroductionResponse]:
    """
    Get introduction requests received by the authenticated user.

    Returns list of introductions sorted by most recent first.
    Uses caching for performance.
    """
    try:
        introductions = await introduction_service.get_received_introductions(
            user_id=UUID(current_user["id"]),
            status=status,
            limit=limit,
            offset=offset
        )

        return [IntroductionResponse(**intro) for intro in introductions]

    except Exception as e:
        logger.error(f"Error fetching received introductions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch introductions"
        )


@router.get(
    "/sent",
    response_model=List[IntroductionResponse],
    summary="Get introduction requests you've sent",
    description="""
    Get introduction requests that you have sent to others.

    - **status**: Optional filter by status (pending, accepted, declined, completed, expired)
    - **limit**: Maximum number of results (1-50, default 20)
    - **offset**: Pagination offset (default 0)

    Results are sorted by request date (newest first).
    """
)
async def get_sent_introductions(
    status: Optional[str] = Query(
        None,
        pattern="^(pending|accepted|declined|completed|expired)$",
        description="Filter by introduction status"
    ),
    limit: int = Query(20, ge=1, le=50, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: dict = Depends(get_current_user)
) -> List[IntroductionResponse]:
    """
    Get introduction requests sent by the authenticated user.

    Returns list of introductions sorted by most recent first.
    Uses caching for performance.
    """
    try:
        introductions = await introduction_service.get_sent_introductions(
            user_id=UUID(current_user["id"]),
            status=status,
            limit=limit,
            offset=offset
        )

        return [IntroductionResponse(**intro) for intro in introductions]

    except Exception as e:
        logger.error(f"Error fetching sent introductions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch introductions"
        )


@router.get(
    "/{intro_id}",
    response_model=IntroductionResponse,
    summary="Get details of a specific introduction",
    description="""
    Get full details of a specific introduction.

    You must be either the requester, target, or connector to view the introduction.
    """
)
async def get_introduction(
    intro_id: UUID,
    current_user: dict = Depends(get_current_user)
) -> IntroductionResponse:
    """
    Get details of a specific introduction.

    Validates that the authenticated user is involved in the introduction
    (requester, target, or connector).
    """
    try:
        intro = await zerodb_client.get_by_id("introductions", str(intro_id))

        if not intro:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Introduction not found"
            )

        # Verify user is involved in this introduction
        user_id = current_user["id"]
        if user_id not in [
            intro["requester_id"],
            intro["target_id"],
            intro.get("connector_id")
        ]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this introduction"
            )

        return IntroductionResponse(**intro)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching introduction {intro_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch introduction"
        )


@router.put(
    "/{intro_id}/respond",
    response_model=IntroductionResponse,
    summary="Accept or decline an introduction request",
    description="""
    Respond to an introduction request.

    - **accept**: True to accept, False to decline
    - **message**: Optional response message

    Only the target of the introduction can respond.
    Cannot respond to already responded/expired introductions.
    """
)
async def respond_to_introduction(
    intro_id: UUID,
    response: IntroductionResponseRequest,
    current_user: dict = Depends(get_current_user)
) -> IntroductionResponse:
    """
    Accept or decline an introduction request.

    Updates introduction status to accepted or declined.
    Tracks outcome in RLHF system for learning.
    Sends notification to requester (if notification system exists).
    """
    try:
        updated_intro = await introduction_service.respond_to_introduction(
            intro_id=intro_id,
            user_id=UUID(current_user["id"]),
            accept=response.accept,
            message=response.message
        )

        logger.info(
            f"User {current_user['id']} "
            f"{'accepted' if response.accept else 'declined'} "
            f"introduction {intro_id}"
        )

        return IntroductionResponse(**updated_intro)

    except IntroductionServiceError as e:
        logger.warning(f"Introduction response failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error in respond_to_introduction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to respond to introduction"
        )


@router.put(
    "/{intro_id}/complete",
    response_model=IntroductionResponse,
    summary="Mark introduction as completed with outcome",
    description="""
    Mark an introduction as completed and record the outcome.

    - **outcome**: One of: meeting_scheduled, email_exchanged, no_response, not_relevant
    - **notes**: Optional notes about the outcome

    Either the requester or target can complete the introduction.
    This helps improve future matching through RLHF learning.
    """
)
async def complete_introduction(
    intro_id: UUID,
    completion: IntroductionCompletion,
    current_user: dict = Depends(get_current_user)
) -> IntroductionResponse:
    """
    Mark introduction as completed with outcome.

    Records the outcome for RLHF learning to improve future introductions.
    Can only be done by users involved in the introduction.
    """
    try:
        # Convert string outcome to enum
        outcome_enum = IntroductionOutcome(completion.outcome)

        updated_intro = await introduction_service.complete_introduction(
            intro_id=intro_id,
            user_id=UUID(current_user["id"]),
            outcome=outcome_enum,
            notes=completion.notes
        )

        logger.info(
            f"User {current_user['id']} completed introduction {intro_id} "
            f"with outcome {completion.outcome}"
        )

        return IntroductionResponse(**updated_intro)

    except IntroductionServiceError as e:
        logger.warning(f"Introduction completion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid outcome value: {e}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in complete_introduction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete introduction"
        )
