"""
Unit Tests for Phone Verification Service
TDD tests for phone number verification
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.phone_verification_service import PhoneVerificationService
from app.models.user import User


@pytest.mark.unit
class TestPhoneVerification:
    """Test suite for phone verification operations"""

    @pytest.mark.asyncio
    async def test_send_verification_code_generates_code(self, db_session: AsyncSession, sample_user: User):
        """Test sending verification code generates and stores code"""
        # Arrange
        phone_service = PhoneVerificationService(db_session)
        phone_number = "+14155551234"

        # Act
        with patch.object(phone_service, '_send_sms', new_callable=AsyncMock) as mock_sms:
            mock_sms.return_value = True
            result = await phone_service.send_verification_code(sample_user.id, phone_number)

        # Assert
        assert result is True
        updated_user = await db_session.get(User, sample_user.id)
        assert updated_user.phone_verification_code is not None
        assert len(updated_user.phone_verification_code) == 6
        assert updated_user.phone_verification_code.isdigit()

    @pytest.mark.asyncio
    async def test_send_verification_code_sets_expiry(self, db_session: AsyncSession, sample_user: User):
        """Test verification code has expiry timestamp"""
        # Arrange
        phone_service = PhoneVerificationService(db_session)
        phone_number = "+14155559999"

        # Act
        with patch.object(phone_service, '_send_sms', new_callable=AsyncMock) as mock_sms:
            mock_sms.return_value = True
            await phone_service.send_verification_code(sample_user.id, phone_number)

        # Assert
        updated_user = await db_session.get(User, sample_user.id)
        assert updated_user.phone_verification_expires_at is not None
        assert updated_user.phone_verification_expires_at > datetime.utcnow()

    @pytest.mark.asyncio
    async def test_verify_phone_with_valid_code_succeeds(self, db_session: AsyncSession, sample_user: User):
        """Test verifying phone with valid code"""
        # Arrange
        phone_service = PhoneVerificationService(db_session)
        phone_number = "+14155551111"
        verification_code = "123456"

        # Set up user with verification code
        sample_user.phone_number = phone_number
        sample_user.phone_verification_code = verification_code
        sample_user.phone_verification_expires_at = datetime.utcnow() + timedelta(minutes=5)
        sample_user.phone_verified = False
        await db_session.commit()

        # Act
        result = await phone_service.verify_phone(sample_user.id, phone_number, verification_code)

        # Assert
        assert result is True
        updated_user = await db_session.get(User, sample_user.id)
        assert updated_user.phone_verified is True
        assert updated_user.phone_verification_code is None  # Code should be cleared

    @pytest.mark.asyncio
    async def test_verify_phone_with_invalid_code_fails(self, db_session: AsyncSession, sample_user: User):
        """TDD: Invalid codes fail verification"""
        # Arrange
        phone_service = PhoneVerificationService(db_session)
        phone_number = "+14155552222"
        correct_code = "123456"
        wrong_code = "654321"

        # Set up user with verification code
        sample_user.phone_number = phone_number
        sample_user.phone_verification_code = correct_code
        sample_user.phone_verification_expires_at = datetime.utcnow() + timedelta(minutes=5)
        sample_user.phone_verified = False
        await db_session.commit()

        # Act
        result = await phone_service.verify_phone(sample_user.id, phone_number, wrong_code)

        # Assert
        assert result is False
        updated_user = await db_session.get(User, sample_user.id)
        assert updated_user.phone_verified is False

    @pytest.mark.asyncio
    async def test_verify_phone_with_expired_code_fails(self, db_session: AsyncSession, sample_user: User):
        """Test verification fails with expired code"""
        # Arrange
        phone_service = PhoneVerificationService(db_session)
        phone_number = "+14155553333"
        verification_code = "123456"

        # Set up user with expired verification code
        sample_user.phone_number = phone_number
        sample_user.phone_verification_code = verification_code
        sample_user.phone_verification_expires_at = datetime.utcnow() - timedelta(minutes=1)  # Expired
        sample_user.phone_verified = False
        await db_session.commit()

        # Act
        result = await phone_service.verify_phone(sample_user.id, phone_number, verification_code)

        # Assert
        assert result is False
        updated_user = await db_session.get(User, sample_user.id)
        assert updated_user.phone_verified is False

    @pytest.mark.asyncio
    async def test_verified_number_cannot_be_changed_without_reverification(
        self, db_session: AsyncSession, sample_user: User
    ):
        """TDD: Verified numbers are immutable without re-verification"""
        # Arrange
        phone_service = PhoneVerificationService(db_session)
        original_phone = "+14155554444"
        new_phone = "+14155555555"

        # Set up verified phone
        sample_user.phone_number = original_phone
        sample_user.phone_verified = True
        await db_session.commit()

        # Act - Try to send code to new number
        with patch.object(phone_service, '_send_sms', new_callable=AsyncMock) as mock_sms:
            mock_sms.return_value = True
            await phone_service.send_verification_code(sample_user.id, new_phone)

        # Assert - Phone verification should be reset
        updated_user = await db_session.get(User, sample_user.id)
        assert updated_user.phone_number == new_phone
        assert updated_user.phone_verified is False  # Verification reset

    @pytest.mark.asyncio
    async def test_verification_code_expiry_duration(self, db_session: AsyncSession, sample_user: User):
        """Test verification code expiry is 5 minutes"""
        # Arrange
        phone_service = PhoneVerificationService(db_session)
        phone_number = "+14155556666"

        # Act
        with patch.object(phone_service, '_send_sms', new_callable=AsyncMock) as mock_sms:
            mock_sms.return_value = True
            before_time = datetime.utcnow()
            await phone_service.send_verification_code(sample_user.id, phone_number)
            after_time = datetime.utcnow()

        # Assert
        updated_user = await db_session.get(User, sample_user.id)
        expiry = updated_user.phone_verification_expires_at

        # Expiry should be approximately 5 minutes from now
        expected_expiry_min = before_time + timedelta(minutes=4, seconds=55)
        expected_expiry_max = after_time + timedelta(minutes=5, seconds=5)

        assert expected_expiry_min <= expiry <= expected_expiry_max

    @pytest.mark.asyncio
    async def test_phone_number_format_validation(self, db_session: AsyncSession, sample_user: User):
        """Test phone number must be in E.164 format"""
        # Arrange
        phone_service = PhoneVerificationService(db_session)
        invalid_phones = [
            "1234567890",  # Missing +
            "+1234",  # Too short
            "abcd",  # Not numeric
            "",  # Empty
        ]

        # Act & Assert
        for invalid_phone in invalid_phones:
            with pytest.raises(ValueError):
                await phone_service.send_verification_code(sample_user.id, invalid_phone)

    @pytest.mark.asyncio
    async def test_cannot_verify_without_sending_code_first(self, db_session: AsyncSession, sample_user: User):
        """Test verification requires code to be sent first"""
        # Arrange
        phone_service = PhoneVerificationService(db_session)
        phone_number = "+14155557777"
        code = "123456"

        # User has no verification code set
        sample_user.phone_verification_code = None
        await db_session.commit()

        # Act
        result = await phone_service.verify_phone(sample_user.id, phone_number, code)

        # Assert
        assert result is False
