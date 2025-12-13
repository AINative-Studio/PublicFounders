"""
Unit Tests for Security Module
TDD tests for JWT token generation and validation
"""
import pytest
from datetime import datetime, timedelta
from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_verification_code,
    verify_password,
    get_password_hash
)


class TestJWTToken:
    """Test suite for JWT token operations"""

    def test_create_access_token_with_default_expiry(self):
        """Test JWT token creation with default expiration"""
        # Arrange
        payload = {"sub": "user_123", "linkedin_id": "linkedin_abc"}

        # Act
        token = create_access_token(payload)

        # Assert
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_custom_expiry(self):
        """Test JWT token creation with custom expiration"""
        # Arrange
        payload = {"sub": "user_123"}
        expires_delta = timedelta(minutes=30)

        # Act
        token = create_access_token(payload, expires_delta=expires_delta)

        # Assert
        assert token is not None
        assert isinstance(token, str)

    def test_decode_valid_access_token(self):
        """Test decoding a valid JWT token"""
        # Arrange
        original_payload = {
            "sub": "user_456",
            "linkedin_id": "linkedin_xyz",
            "email": "test@example.com"
        }
        token = create_access_token(original_payload)

        # Act
        decoded_payload = decode_access_token(token)

        # Assert
        assert decoded_payload is not None
        assert decoded_payload["sub"] == original_payload["sub"]
        assert decoded_payload["linkedin_id"] == original_payload["linkedin_id"]
        assert "exp" in decoded_payload
        assert "iat" in decoded_payload

    def test_decode_invalid_token(self):
        """Test decoding an invalid JWT token"""
        # Arrange
        invalid_token = "invalid.token.here"

        # Act
        decoded_payload = decode_access_token(invalid_token)

        # Assert
        assert decoded_payload is None

    def test_decode_expired_token(self):
        """Test decoding an expired JWT token"""
        # Arrange
        payload = {"sub": "user_789"}
        # Create token that expired 1 hour ago
        expires_delta = timedelta(hours=-1)
        token = create_access_token(payload, expires_delta=expires_delta)

        # Act
        decoded_payload = decode_access_token(token)

        # Assert
        assert decoded_payload is None

    def test_token_contains_issued_at_claim(self):
        """Test JWT token contains 'iat' (issued at) claim"""
        # Arrange
        payload = {"sub": "user_999"}

        # Act
        token = create_access_token(payload)
        decoded = decode_access_token(token)

        # Assert
        assert decoded is not None
        assert "iat" in decoded
        assert isinstance(decoded["iat"], int)

    def test_token_contains_expiration_claim(self):
        """Test JWT token contains 'exp' (expiration) claim"""
        # Arrange
        payload = {"sub": "user_111"}

        # Act
        token = create_access_token(payload)
        decoded = decode_access_token(token)

        # Assert
        assert decoded is not None
        assert "exp" in decoded
        assert isinstance(decoded["exp"], int)
        assert decoded["exp"] > decoded["iat"]


class TestPasswordHashing:
    """Test suite for password hashing and verification"""

    def test_get_password_hash(self):
        """Test password hashing"""
        # Arrange
        plain_password = "SecurePassword123!"

        # Act
        hashed_password = get_password_hash(plain_password)

        # Assert
        assert hashed_password is not None
        assert hashed_password != plain_password
        assert len(hashed_password) > 0

    def test_verify_correct_password(self):
        """Test verification of correct password"""
        # Arrange
        plain_password = "MyPassword456"
        hashed_password = get_password_hash(plain_password)

        # Act
        is_valid = verify_password(plain_password, hashed_password)

        # Assert
        assert is_valid is True

    def test_verify_incorrect_password(self):
        """Test verification of incorrect password"""
        # Arrange
        plain_password = "CorrectPassword"
        wrong_password = "WrongPassword"
        hashed_password = get_password_hash(plain_password)

        # Act
        is_valid = verify_password(wrong_password, hashed_password)

        # Assert
        assert is_valid is False

    def test_same_password_generates_different_hashes(self):
        """Test same password generates different hashes (salt)"""
        # Arrange
        plain_password = "SamePassword123"

        # Act
        hash1 = get_password_hash(plain_password)
        hash2 = get_password_hash(plain_password)

        # Assert
        assert hash1 != hash2  # Different hashes due to different salts
        assert verify_password(plain_password, hash1)
        assert verify_password(plain_password, hash2)


class TestVerificationCode:
    """Test suite for verification code generation"""

    def test_generate_verification_code_default_length(self):
        """Test generating verification code with default length (6)"""
        # Act
        code = generate_verification_code()

        # Assert
        assert code is not None
        assert len(code) == 6
        assert code.isdigit()

    def test_generate_verification_code_custom_length(self):
        """Test generating verification code with custom length"""
        # Arrange
        custom_length = 8

        # Act
        code = generate_verification_code(length=custom_length)

        # Assert
        assert len(code) == custom_length
        assert code.isdigit()

    def test_generate_verification_code_uniqueness(self):
        """Test that generated codes are different (randomness)"""
        # Act
        codes = [generate_verification_code() for _ in range(10)]

        # Assert
        # All codes should be digits
        assert all(code.isdigit() for code in codes)
        # At least some codes should be different (very high probability)
        assert len(set(codes)) > 1

    def test_verification_code_only_digits(self):
        """Test verification code contains only numeric digits"""
        # Act
        code = generate_verification_code()

        # Assert
        assert code.isdigit()
        assert all(c in '0123456789' for c in code)
