"""
Phone Verification Service - ZeroDB Edition
Handles phone number verification with SMS codes using ZeroDB NoSQL
"""
import uuid
import re
from datetime import datetime, timedelta
from typing import Optional
from app.services.zerodb_client import zerodb_client
from app.core.config import settings
from app.core.security import generate_verification_code


class PhoneVerificationService:
    """Service for phone number verification"""

    def __init__(self):
        """Initialize phone verification service (no DB session needed)"""
        pass

    def _validate_phone_format(self, phone_number: str) -> str:
        """
        Validate phone number format (E.164)

        Args:
            phone_number: Phone number to validate

        Returns:
            Cleaned phone number

        Raises:
            ValueError: If phone number is invalid
        """
        if not phone_number:
            raise ValueError("Phone number is required")

        # Remove all non-digit characters except +
        cleaned = re.sub(r'[^\d+]', '', phone_number)

        # Must start with + and have 10-15 digits
        if not re.match(r'^\+\d{10,15}$', cleaned):
            raise ValueError(
                "Phone number must be in E.164 format (e.g., +1234567890)"
            )

        return cleaned

    async def _send_sms(self, phone_number: str, code: str) -> bool:
        """
        Send SMS verification code
        (Mock implementation - integrate with Twilio in production)

        Args:
            phone_number: Phone number to send to
            code: Verification code

        Returns:
            True if sent successfully
        """
        # TODO: Integrate with Twilio Verify API
        # For MVP, we'll just log the code (in production this sends SMS)
        print(f"[SMS] Sending verification code {code} to {phone_number}")
        return True

    async def send_verification_code(
        self,
        user_id: uuid.UUID,
        phone_number: str
    ) -> bool:
        """
        Generate and send verification code to phone number

        Args:
            user_id: User UUID
            phone_number: Phone number to verify

        Returns:
            True if code sent successfully

        Raises:
            ValueError: If phone number format is invalid
        """
        # Validate format
        cleaned_phone = self._validate_phone_format(phone_number)

        # Get user
        user = await zerodb_client.get_by_id(
            table_name="users",
            id=str(user_id)
        )
        if not user:
            raise ValueError("User not found")

        # Generate verification code
        code = generate_verification_code(
            length=settings.PHONE_VERIFICATION_CODE_LENGTH
        )

        # Set expiry time
        expires_at = datetime.utcnow() + timedelta(
            minutes=settings.PHONE_VERIFICATION_CODE_EXPIRY_MINUTES
        )

        # Update user with verification code
        await zerodb_client.update_rows(
            table_name="users",
            filter={"id": str(user_id)},
            update={"$set": {
                "phone_number": cleaned_phone,
                "phone_verification_code": code,
                "phone_verification_expires_at": expires_at.isoformat(),
                "phone_verified": False,
                "updated_at": datetime.utcnow().isoformat()
            }}
        )

        # Send SMS
        await self._send_sms(cleaned_phone, code)

        return True

    async def verify_phone(
        self,
        user_id: uuid.UUID,
        phone_number: str,
        verification_code: str
    ) -> bool:
        """
        Verify phone number with code

        Args:
            user_id: User UUID
            phone_number: Phone number being verified
            verification_code: Verification code from SMS

        Returns:
            True if verification successful, False otherwise
        """
        # Get user
        user = await zerodb_client.get_by_id(
            table_name="users",
            id=str(user_id)
        )
        if not user:
            return False

        # Check if phone number matches
        if user.get("phone_number") != phone_number:
            return False

        # Check if code exists
        if not user.get("phone_verification_code"):
            return False

        # Check if code matches
        if user.get("phone_verification_code") != verification_code:
            return False

        # Check if code has expired
        expires_at_str = user.get("phone_verification_expires_at")
        if not expires_at_str:
            return False

        # Parse ISO timestamp - remove timezone info for comparison with utcnow()
        try:
            # Handle various ISO formats
            clean_str = expires_at_str.replace('Z', '').replace('+00:00', '')
            # Remove microseconds timezone suffix if present
            if '+' in clean_str:
                clean_str = clean_str.split('+')[0]
            expires_at = datetime.fromisoformat(clean_str)
        except ValueError:
            return False

        if expires_at < datetime.utcnow():
            return False

        # Verification successful
        await zerodb_client.update_rows(
            table_name="users",
            filter={"id": str(user_id)},
            update={"$set": {
                "phone_verified": True,
                "phone_verification_code": None,
                "phone_verification_expires_at": None,
                "updated_at": datetime.utcnow().isoformat()
            }}
        )

        return True

    async def is_phone_verified(self, user_id: uuid.UUID) -> bool:
        """
        Check if user's phone is verified

        Args:
            user_id: User UUID

        Returns:
            True if phone is verified
        """
        user = await zerodb_client.get_by_id(
            table_name="users",
            id=str(user_id)
        )
        if not user:
            return False

        return user.get("phone_verified", False)
