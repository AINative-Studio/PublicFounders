"""
Profile API Endpoints
Founder profile CRUD operations
"""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.services.profile_service import ProfileService
from app.services.auth_service import AuthService
from app.schemas.founder_profile import (
    FounderProfileResponse,
    FounderProfileUpdate
)
from app.schemas.user import UserResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter()
security = HTTPBearer()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> uuid.UUID:
    """
    Extract user ID from JWT token

    Args:
        credentials: HTTP Authorization header with Bearer token

    Returns:
        User UUID

    Raises:
        HTTPException: If token is invalid or expired
    """
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

    try:
        return uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token"
        )


@router.get("/me", response_model=dict)
async def get_my_profile(
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user's profile

    Returns user data and founder profile
    """
    profile_service = ProfileService(db)
    auth_service = AuthService(db)

    # Get user
    user = await auth_service.get_user_by_id(current_user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Get profile
    profile = await profile_service.get_profile(current_user_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )

    return {
        "user": UserResponse.from_orm(user),
        "profile": FounderProfileResponse.from_orm(profile)
    }


@router.put("/me", response_model=FounderProfileResponse)
async def update_my_profile(
    update_data: FounderProfileUpdate,
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current user's profile

    Triggers embedding regeneration if bio or focus changes
    """
    profile_service = ProfileService(db)

    try:
        updated_profile = await profile_service.update_profile(
            user_id=current_user_id,
            update_data=update_data
        )

        return FounderProfileResponse.from_orm(updated_profile)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile: {str(e)}"
        )


@router.get("/{user_id}", response_model=dict)
async def get_user_profile(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get another user's profile (public profiles only)

    Args:
        user_id: User UUID to retrieve
    """
    profile_service = ProfileService(db)
    auth_service = AuthService(db)

    # Get user
    user = await auth_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Get profile
    profile = await profile_service.get_profile(user_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )

    # Check visibility
    if not profile.public_visibility:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This profile is private"
        )

    return {
        "user": UserResponse.from_orm(user),
        "profile": FounderProfileResponse.from_orm(profile)
    }


@router.get("/", response_model=list)
async def list_public_profiles(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    List public founder profiles

    Args:
        limit: Maximum number of profiles to return (1-100)
        offset: Pagination offset
    """
    profile_service = ProfileService(db)

    profiles = await profile_service.get_public_profiles(
        limit=limit,
        offset=offset
    )

    # Get users for each profile
    auth_service = AuthService(db)
    result = []

    for profile in profiles:
        user = await auth_service.get_user_by_id(profile.user_id)
        if user:
            result.append({
                "user": UserResponse.from_orm(user),
                "profile": FounderProfileResponse.from_orm(profile)
            })

    return result
