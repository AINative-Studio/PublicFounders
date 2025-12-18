"""
Authentication API Endpoints
LinkedIn OAuth, JWT tokens, and phone verification
"""
import logging
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

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/linkedin/initiate")
async def initiate_linkedin_oauth(
    redirect_uri: Optional[str] = Query(None, description="Frontend callback URL to redirect after auth")
):
    """
    Initiate LinkedIn OAuth flow

    Redirects user to LinkedIn authorization page
    """
    if not settings.LINKEDIN_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="LinkedIn OAuth not configured"
        )

    # Use state parameter to pass frontend redirect URI
    import base64
    state = base64.urlsafe_b64encode((redirect_uri or "http://localhost:4000/auth/callback").encode()).decode()

    # Build LinkedIn authorization URL
    auth_url = (
        f"https://www.linkedin.com/oauth/v2/authorization?"
        f"response_type=code&"
        f"client_id={settings.LINKEDIN_CLIENT_ID}&"
        f"redirect_uri={settings.LINKEDIN_REDIRECT_URI}&"
        f"scope={settings.LINKEDIN_SCOPE}&"
        f"state={state}"
    )

    return RedirectResponse(url=auth_url)


@router.get("/linkedin/callback")
async def linkedin_oauth_callback(
    code: str = Query(..., description="Authorization code from LinkedIn"),
    state: Optional[str] = Query(None, description="State parameter with frontend redirect URI")
):
    """
    LinkedIn OAuth callback handler

    Exchanges authorization code for access token and creates/logs in user
    Redirects to frontend with token or error
    """
    import base64
    import urllib.parse

    logger.info(f"=== LinkedIn OAuth Callback Started ===")
    logger.info(f"Code received: {code[:15]}... (length: {len(code)})")
    logger.info(f"State parameter: {state}")
    logger.info(f"Redirect URI configured: {settings.LINKEDIN_REDIRECT_URI}")

    # Decode frontend redirect URI from state
    frontend_redirect = "http://localhost:4000/auth/callback"
    if state:
        try:
            frontend_redirect = base64.urlsafe_b64decode(state.encode()).decode()
        except Exception:
            pass  # Use default if decode fails

    if not settings.LINKEDIN_CLIENT_ID or not settings.LINKEDIN_CLIENT_SECRET:
        logger.error("LinkedIn OAuth credentials not configured")
        error_url = f"{frontend_redirect}?error=config_error&error_description=LinkedIn+OAuth+not+configured"
        return RedirectResponse(url=error_url)

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
                logger.error(f"LinkedIn token exchange failed: {token_response.status_code}")
                logger.error(f"Response: {token_response.text}")
                error_url = f"{frontend_redirect}?error=token_error&error_description=Failed+to+get+access+token+from+LinkedIn"
                return RedirectResponse(url=error_url)

            token_data = token_response.json()
            access_token = token_data.get("access_token")
            logger.info(f"Successfully received access token from LinkedIn")

            if not access_token:
                error_url = f"{frontend_redirect}?error=token_error&error_description=No+access+token+received"
                return RedirectResponse(url=error_url)

            # Get user info from LinkedIn
            logger.info("Fetching user info from LinkedIn API")
            user_info_response = await client.get(
                "https://api.linkedin.com/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )

            if user_info_response.status_code != 200:
                logger.error(f"LinkedIn user info fetch failed: {user_info_response.status_code}")
                logger.error(f"Response: {user_info_response.text}")
                error_url = f"{frontend_redirect}?error=user_info_error&error_description=Failed+to+get+user+info"
                return RedirectResponse(url=error_url)

            linkedin_user = user_info_response.json()
            logger.info(f"LinkedIn user data received: {linkedin_user.get('sub', 'N/A')}, {linkedin_user.get('email', 'N/A')}")

            # Handle locale - LinkedIn returns it as an object {'country': 'US', 'language': 'en'}
            locale_data = linkedin_user.get("locale")
            location_str = None
            if locale_data:
                if isinstance(locale_data, dict):
                    country = locale_data.get("country", "")
                    location_str = f"{country}" if country else None
                elif isinstance(locale_data, str):
                    location_str = locale_data

            # Map LinkedIn data to our schema
            # LinkedIn userinfo provides: sub, name, given_name, family_name, picture, email, locale
            linkedin_data = LinkedInUserData(
                linkedin_id=linkedin_user.get("sub"),
                name=linkedin_user.get("name", ""),
                first_name=linkedin_user.get("given_name"),
                last_name=linkedin_user.get("family_name"),
                headline=linkedin_user.get("headline"),  # Note: Not available via userinfo endpoint
                profile_photo_url=linkedin_user.get("picture"),
                location=location_str,
                email=linkedin_user.get("email")
            )

            # Create or get existing user (no DB session needed with ZeroDB)
            logger.info("Creating or retrieving user from database")
            auth_service = AuthService()
            user, profile, created = await auth_service.get_or_create_user_from_linkedin(linkedin_data)
            logger.info(f"User {'created' if created else 'found'}: {user.get('id', 'N/A')}")

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
            logger.info(f"JWT token created successfully")

            # Redirect to frontend with token
            params = {
                "token": jwt_token,
                "created": str(created).lower(),
                "user_id": user["id"],
                "phone_verified": str(user.get("phone_verified", False)).lower()
            }
            query_string = urllib.parse.urlencode(params)
            success_url = f"{frontend_redirect}?{query_string}"
            return RedirectResponse(url=success_url)

    except Exception as e:
        logger.error(f"Unexpected error in OAuth flow: {type(e).__name__}: {str(e)}")
        logger.exception("Full traceback:")
        error_msg = urllib.parse.quote(str(e))
        error_url = f"{frontend_redirect}?error=oauth_error&error_description={error_msg}"
        return RedirectResponse(url=error_url)


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
