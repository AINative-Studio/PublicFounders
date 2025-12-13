"""
Authentication API Endpoints
LinkedIn OAuth, JWT tokens, and phone verification
"""
import uuid
from typing import Optional
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse
import httpx

from app.core.config import settings
from app.core.security import create_access_token
from app.services.auth_service import AuthService
from app.services.phone_verification_service import PhoneVerificationService
from app.schemas.auth import Token, PhoneVerificationRequest, PhoneVerificationConfirm
from app.schemas.user import LinkedInUserData, UserResponse

router = APIRouter()


@router.get("/linkedin/initiate")
async def initiate_linkedin_oauth():
    """
    Initiate LinkedIn OAuth flow

    Redirects user to LinkedIn authorization page
    """
    if not settings.LINKEDIN_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="LinkedIn OAuth not configured"
        )

    # Build LinkedIn authorization URL
    auth_url = (
        f"https://www.linkedin.com/oauth/v2/authorization?"
        f"response_type=code&"
        f"client_id={settings.LINKEDIN_CLIENT_ID}&"
        f"redirect_uri={settings.LINKEDIN_REDIRECT_URI}&"
        f"scope={settings.LINKEDIN_SCOPE}"
    )

    return RedirectResponse(url=auth_url)


@router.get("/linkedin/callback")
async def linkedin_oauth_callback(
    code: str = Query(..., description="Authorization code from LinkedIn")
):
    """
    LinkedIn OAuth callback handler

    Exchanges authorization code for access token and creates/logs in user
    """
    if not settings.LINKEDIN_CLIENT_ID or not settings.LINKEDIN_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="LinkedIn OAuth not configured"
        )

    try:
        # Exchange code for access token
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://www.linkedin.com/oauth/v2/accessToken",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": settings.LINKEDIN_REDIRECT_URI,
                    "client_id": settings.LINKEDIN_CLIENT_ID,
                    "client_secret": settings.LINKEDIN_CLIENT_SECRET
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            if token_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to get access token from LinkedIn"
                )

            token_data = token_response.json()
            access_token = token_data.get("access_token")

            if not access_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No access token received from LinkedIn"
                )

            # Get user info from LinkedIn
            user_info_response = await client.get(
                "https://api.linkedin.com/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )

            if user_info_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to get user info from LinkedIn"
                )

            linkedin_user = user_info_response.json()

            # Map LinkedIn data to our schema
            linkedin_data = LinkedInUserData(
                linkedin_id=linkedin_user.get("sub"),
                name=linkedin_user.get("name", ""),
                headline=linkedin_user.get("headline"),
                profile_photo_url=linkedin_user.get("picture"),
                location=linkedin_user.get("locale"),
                email=linkedin_user.get("email")
            )

            # Create or get existing user (no DB session needed with ZeroDB)
            auth_service = AuthService()
            user, profile, created = await auth_service.get_or_create_user_from_linkedin(linkedin_data)

            # Create JWT token
            token_payload = {
                "sub": user["id"],
                "linkedin_id": user["linkedin_id"],
                "email": user["email"]
            }

            jwt_token = create_access_token(
                token_payload,
                expires_delta=timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
            )

            return {
                "access_token": jwt_token,
                "token_type": "bearer",
                "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # seconds
                "user": user,  # Already a dict from ZeroDB
                "created": created
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth flow failed: {str(e)}"
        )


@router.post("/verify-phone", status_code=status.HTTP_200_OK)
async def send_phone_verification(
    request: PhoneVerificationRequest,
    user_id: uuid.UUID = Query(..., description="User ID")
):
    """
    Send phone verification code via SMS

    Generates a 6-digit code and sends it to the provided phone number
    """
    phone_service = PhoneVerificationService()

    try:
        success = await phone_service.send_verification_code(
            user_id=user_id,
            phone_number=request.phone_number
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send verification code"
            )

        return {
            "message": "Verification code sent successfully",
            "phone_number": request.phone_number,
            "expires_in_minutes": settings.PHONE_VERIFICATION_CODE_EXPIRY_MINUTES
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send verification code: {str(e)}"
        )


@router.post("/confirm-phone", status_code=status.HTTP_200_OK)
async def confirm_phone_verification(
    request: PhoneVerificationConfirm,
    user_id: uuid.UUID = Query(..., description="User ID")
):
    """
    Confirm phone verification with code

    Validates the verification code and marks phone as verified
    """
    phone_service = PhoneVerificationService()

    try:
        success = await phone_service.verify_phone(
            user_id=user_id,
            phone_number=request.phone_number,
            verification_code=request.verification_code
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification code"
            )

        return {
            "message": "Phone verified successfully",
            "phone_number": request.phone_number,
            "verified": True
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Verification failed: {str(e)}"
        )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout():
    """
    Logout user

    (Stateless JWT - client should discard token)
    """
    return {
        "message": "Logged out successfully"
    }
