"""
Authentication Schemas
Pydantic models for authentication and verification
"""
from typing import Optional
from pydantic import BaseModel, Field, validator
import re


class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class TokenData(BaseModel):
    """JWT token payload data"""
    user_id: Optional[str] = None
    linkedin_id: Optional[str] = None


class PhoneVerificationRequest(BaseModel):
    """Phone verification request"""
    phone_number: str = Field(
        ...,
        description="Phone number in E.164 format (e.g., +1234567890)",
        min_length=10,
        max_length=20
    )

    @validator("phone_number")
    def validate_phone_number(cls, v: str) -> str:
        """Validate phone number format"""
        # Remove all non-digit characters except +
        cleaned = re.sub(r'[^\d+]', '', v)

        # Must start with + and have at least 10 digits
        if not re.match(r'^\+\d{10,15}$', cleaned):
            raise ValueError(
                "Phone number must be in E.164 format (e.g., +1234567890)"
            )

        return cleaned


class PhoneVerificationConfirm(BaseModel):
    """Phone verification confirmation"""
    phone_number: str = Field(
        ...,
        description="Phone number being verified",
        min_length=10,
        max_length=20
    )
    verification_code: str = Field(
        ...,
        description="6-digit verification code",
        min_length=6,
        max_length=6
    )

    @validator("verification_code")
    def validate_code(cls, v: str) -> str:
        """Validate verification code is 6 digits"""
        if not v.isdigit():
            raise ValueError("Verification code must be 6 digits")
        return v
