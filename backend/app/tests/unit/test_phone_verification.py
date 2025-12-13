"""
Unit Tests for Phone Verification Service - ZeroDB Edition
TDD tests for phone number verification using ZeroDB
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
import uuid

from app.services.phone_verification_service import PhoneVerificationService


@pytest.mark.unit
class TestPhoneVerification:
    """Test suite for phone verification operations"""

    @pytest.mark.asyncio
    async def test_send_verification_code_generates_code(self, mock_zerodb, sample_user_dict):
        """Test sending verification code generates and stores code"""
        # Arrange
        user_id = uuid.UUID(sample_user_dict["id"])
        phone_number = "+14155551234"

        mock_zerodb.get_by_id.return_value = sample_user_dict
        mock_zerodb.update_rows.return_value = {"success": True, "updated": 1}

        phone_service = PhoneVerificationService()

        # Act
        with patch('app.services.phone_verification_service.zerodb_client', mock_zerodb):
            with patch.object(phone_service, '_send_sms', new_callable=AsyncMock) as mock_sms:
                mock_sms.return_value = True
                result = await phone_service.send_verification_code(user_id, phone_number)

        # Assert
        assert result is True

        # Verify update was called with verification code
        mock_zerodb.update_rows.assert_called_once()
        call_args = mock_zerodb.update_rows.call_args
        update_data = call_args[1]["update"]["$set"]

        assert "phone_verification_code" in update_data
        assert len(update_data["phone_verification_code"]) == 6
        assert update_data["phone_verification_code"].isdigit()

    @pytest.mark.asyncio
    async def test_send_verification_code_sets_expiry(self, mock_zerodb, sample_user_dict):
        """Test verification code has expiry timestamp"""
        # Arrange
        user_id = uuid.UUID(sample_user_dict["id"])
        phone_number = "+14155559999"

        mock_zerodb.get_by_id.return_value = sample_user_dict
        mock_zerodb.update_rows.return_value = {"success": True, "updated": 1}

        phone_service = PhoneVerificationService()

        # Act
        with patch('app.services.phone_verification_service.zerodb_client', mock_zerodb):
            with patch.object(phone_service, '_send_sms', new_callable=AsyncMock) as mock_sms:
                mock_sms.return_value = True
                await phone_service.send_verification_code(user_id, phone_number)

        # Assert
        mock_zerodb.update_rows.assert_called_once()
        call_args = mock_zerodb.update_rows.call_args
        update_data = call_args[1]["update"]["$set"]

        assert "phone_verification_expires_at" in update_data
        # Verify it's an ISO timestamp string
        assert isinstance(update_data["phone_verification_expires_at"], str)

    @pytest.mark.asyncio
    async def test_verify_phone_with_valid_code_succeeds(self, mock_zerodb, sample_user_dict):
        """Test verifying phone with valid code"""
        # Arrange
        user_id = uuid.UUID(sample_user_dict["id"])
        phone_number = "+14155551111"
        verification_code = "123456"

        # Mock user with verification code
        user_with_code = {
            **sample_user_dict,
            "phone_number": phone_number,
            "phone_verification_code": verification_code,
            "phone_verification_expires_at": (datetime.utcnow() + timedelta(minutes=5)).isoformat(),
            "phone_verified": False
        }

        mock_zerodb.get_by_id.return_value = user_with_code
        mock_zerodb.update_rows.return_value = {"success": True, "updated": 1}

        phone_service = PhoneVerificationService()

        # Act
        with patch('app.services.phone_verification_service.zerodb_client', mock_zerodb):
            result = await phone_service.verify_phone(user_id, phone_number, verification_code)

        # Assert
        assert result is True

        # Verify update was called to mark as verified
        mock_zerodb.update_rows.assert_called_once()
        call_args = mock_zerodb.update_rows.call_args
        update_data = call_args[1]["update"]["$set"]

        assert update_data["phone_verified"] is True
        assert update_data["phone_verification_code"] is None

    @pytest.mark.asyncio
    async def test_verify_phone_with_invalid_code_fails(self, mock_zerodb, sample_user_dict):
        """TDD: Invalid codes fail verification"""
        # Arrange
        user_id = uuid.UUID(sample_user_dict["id"])
        phone_number = "+14155552222"
        correct_code = "123456"
        wrong_code = "654321"

        # Mock user with verification code
        user_with_code = {
            **sample_user_dict,
            "phone_number": phone_number,
            "phone_verification_code": correct_code,
            "phone_verification_expires_at": (datetime.utcnow() + timedelta(minutes=5)).isoformat(),
            "phone_verified": False
        }

        mock_zerodb.get_by_id.return_value = user_with_code

        phone_service = PhoneVerificationService()

        # Act
        with patch('app.services.phone_verification_service.zerodb_client', mock_zerodb):
            result = await phone_service.verify_phone(user_id, phone_number, wrong_code)

        # Assert
        assert result is False
        # Update should NOT have been called
        mock_zerodb.update_rows.assert_not_called()

    @pytest.mark.asyncio
    async def test_verify_phone_with_expired_code_fails(self, mock_zerodb, sample_user_dict):
        """Test verification fails with expired code"""
        # Arrange
        user_id = uuid.UUID(sample_user_dict["id"])
        phone_number = "+14155553333"
        verification_code = "123456"

        # Mock user with expired verification code
        user_with_code = {
            **sample_user_dict,
            "phone_number": phone_number,
            "phone_verification_code": verification_code,
            "phone_verification_expires_at": (datetime.utcnow() - timedelta(minutes=1)).isoformat(),
            "phone_verified": False
        }

        mock_zerodb.get_by_id.return_value = user_with_code

        phone_service = PhoneVerificationService()

        # Act
        with patch('app.services.phone_verification_service.zerodb_client', mock_zerodb):
            result = await phone_service.verify_phone(user_id, phone_number, verification_code)

        # Assert
        assert result is False
        mock_zerodb.update_rows.assert_not_called()

    @pytest.mark.asyncio
    async def test_verified_number_cannot_be_changed_without_reverification(
        self, mock_zerodb, sample_user_dict
    ):
        """TDD: Verified numbers are immutable without re-verification"""
        # Arrange
        user_id = uuid.UUID(sample_user_dict["id"])
        original_phone = "+14155554444"
        new_phone = "+14155555555"

        # Mock verified user
        verified_user = {
            **sample_user_dict,
            "phone_number": original_phone,
            "phone_verified": True
        }

        mock_zerodb.get_by_id.return_value = verified_user
        mock_zerodb.update_rows.return_value = {"success": True, "updated": 1}

        phone_service = PhoneVerificationService()

        # Act - Try to send code to new number
        with patch('app.services.phone_verification_service.zerodb_client', mock_zerodb):
            with patch.object(phone_service, '_send_sms', new_callable=AsyncMock) as mock_sms:
                mock_sms.return_value = True
                await phone_service.send_verification_code(user_id, new_phone)

        # Assert - Verification should be reset
        mock_zerodb.update_rows.assert_called_once()
        call_args = mock_zerodb.update_rows.call_args
        update_data = call_args[1]["update"]["$set"]

        assert update_data["phone_number"] == new_phone
        assert update_data["phone_verified"] is False  # Verification reset

    @pytest.mark.asyncio
    async def test_verification_code_expiry_duration(self, mock_zerodb, sample_user_dict):
        """Test verification code expiry is 5 minutes"""
        # Arrange
        user_id = uuid.UUID(sample_user_dict["id"])
        phone_number = "+14155556666"

        mock_zerodb.get_by_id.return_value = sample_user_dict
        mock_zerodb.update_rows.return_value = {"success": True, "updated": 1}

        phone_service = PhoneVerificationService()

        # Act
        with patch('app.services.phone_verification_service.zerodb_client', mock_zerodb):
            with patch.object(phone_service, '_send_sms', new_callable=AsyncMock) as mock_sms:
                mock_sms.return_value = True
                before_time = datetime.utcnow()
                await phone_service.send_verification_code(user_id, phone_number)
                after_time = datetime.utcnow()

        # Assert
        mock_zerodb.update_rows.assert_called_once()
        call_args = mock_zerodb.update_rows.call_args
        update_data = call_args[1]["update"]["$set"]

        expiry_str = update_data["phone_verification_expires_at"]
        expiry = datetime.fromisoformat(expiry_str)

        # Expiry should be approximately 5 minutes from now
        expected_expiry_min = before_time + timedelta(minutes=4, seconds=55)
        expected_expiry_max = after_time + timedelta(minutes=5, seconds=5)

        assert expected_expiry_min <= expiry <= expected_expiry_max

    @pytest.mark.asyncio
    async def test_phone_number_format_validation(self, mock_zerodb, sample_user_dict):
        """Test phone number must be in E.164 format"""
        # Arrange
        user_id = uuid.UUID(sample_user_dict["id"])
        phone_service = PhoneVerificationService()

        invalid_phones = [
            "1234567890",  # Missing +
            "+1234",  # Too short
            "abcd",  # Not numeric
            "",  # Empty
        ]

        # Act & Assert
        for invalid_phone in invalid_phones:
            with pytest.raises(ValueError):
                await phone_service.send_verification_code(user_id, invalid_phone)

    @pytest.mark.asyncio
    async def test_cannot_verify_without_sending_code_first(self, mock_zerodb, sample_user_dict):
        """Test verification requires code to be sent first"""
        # Arrange
        user_id = uuid.UUID(sample_user_dict["id"])
        phone_number = "+14155557777"
        code = "123456"

        # User has no verification code set
        user_without_code = {
            **sample_user_dict,
            "phone_number": phone_number,
            "phone_verification_code": None
        }

        mock_zerodb.get_by_id.return_value = user_without_code

        phone_service = PhoneVerificationService()

        # Act
        with patch('app.services.phone_verification_service.zerodb_client', mock_zerodb):
            result = await phone_service.verify_phone(user_id, phone_number, code)

        # Assert
        assert result is False
