"""
Unit tests for Safety Service

Tests PII detection, scam detection, and content moderation
using mocked AINative Safety API responses.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from app.services.safety_service import (
    SafetyService,
    SafetyCheck,
    SafetyServiceError,
    safety_service
)


class TestSafetyService:
    """Test suite for SafetyService class."""

    @pytest.fixture
    def mock_httpx_response(self):
        """Create a mock httpx response."""
        def _create_mock(status_code=200, json_data=None):
            mock_response = MagicMock()
            mock_response.status_code = status_code
            mock_response.json.return_value = json_data or {}
            mock_response.raise_for_status = MagicMock()

            # Simulate HTTPStatusError for non-2xx status codes
            if status_code >= 400:
                error = httpx.HTTPStatusError(
                    message=f"HTTP {status_code}",
                    request=MagicMock(),
                    response=mock_response
                )
                mock_response.raise_for_status.side_effect = error

            return mock_response

        return _create_mock

    @pytest.mark.asyncio
    async def test_scan_text_with_pii(self, mock_httpx_response):
        """Test scanning text that contains PII."""
        # Mock API response
        api_response = {
            "pii": {
                "detected": True,
                "types": ["email", "phone"],
                "details": {
                    "email": ["john@example.com"],
                    "phone": ["555-1234"]
                }
            },
            "scam_detection": {
                "is_scam": False,
                "confidence": 0.05,
                "patterns": []
            },
            "content_moderation": {
                "flags": [],
                "is_safe": True,
                "details": {}
            }
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_httpx_response(200, api_response)
            )

            service = SafetyService()
            result = await service.scan_text(
                "Contact me at john@example.com or 555-1234",
                checks=["pii", "scam_detection", "content_moderation"]
            )

            assert result.contains_pii is True
            assert "email" in result.pii_types
            assert "phone" in result.pii_types
            assert result.is_scam is False
            assert result.is_safe is True  # PII warning doesn't make content unsafe

    @pytest.mark.asyncio
    async def test_scan_text_with_critical_pii(self, mock_httpx_response):
        """Test scanning text with critical PII (SSN, credit card)."""
        api_response = {
            "pii": {
                "detected": True,
                "types": ["ssn", "credit_card"],
                "details": {}
            },
            "scam_detection": {
                "is_scam": False,
                "confidence": 0.0,
                "patterns": []
            },
            "content_moderation": {
                "flags": [],
                "is_safe": True,
                "details": {}
            }
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_httpx_response(200, api_response)
            )

            service = SafetyService()
            result = await service.scan_text("My SSN is 123-45-6789")

            assert result.contains_pii is True
            assert "ssn" in result.pii_types
            assert result.is_safe is False  # Critical PII makes content unsafe

    @pytest.mark.asyncio
    async def test_scan_text_with_scam(self, mock_httpx_response):
        """Test scanning text that contains scam patterns."""
        api_response = {
            "pii": {
                "detected": False,
                "types": [],
                "details": {}
            },
            "scam_detection": {
                "is_scam": True,
                "confidence": 0.85,
                "patterns": ["urgent_money_request", "suspicious_link"]
            },
            "content_moderation": {
                "flags": [],
                "is_safe": True,
                "details": {}
            }
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_httpx_response(200, api_response)
            )

            service = SafetyService()
            result = await service.scan_text(
                "URGENT: Send $1000 to this account immediately!"
            )

            assert result.is_scam is True
            assert result.scam_confidence == 0.85
            assert result.is_safe is False  # High-confidence scam is unsafe

    @pytest.mark.asyncio
    async def test_scan_text_with_inappropriate_content(self, mock_httpx_response):
        """Test scanning text with inappropriate content."""
        api_response = {
            "pii": {
                "detected": False,
                "types": [],
                "details": {}
            },
            "scam_detection": {
                "is_scam": False,
                "confidence": 0.0,
                "patterns": []
            },
            "content_moderation": {
                "flags": ["spam", "harassment"],
                "is_safe": False,
                "details": {
                    "spam_score": 0.9,
                    "harassment_detected": True
                }
            }
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_httpx_response(200, api_response)
            )

            service = SafetyService()
            result = await service.scan_text("This is spam and harassment!")

            assert result.is_safe is False
            assert "spam" in result.content_flags
            assert "harassment" in result.content_flags

    @pytest.mark.asyncio
    async def test_scan_text_clean_content(self, mock_httpx_response):
        """Test scanning clean text with no issues."""
        api_response = {
            "pii": {
                "detected": False,
                "types": [],
                "details": {}
            },
            "scam_detection": {
                "is_scam": False,
                "confidence": 0.02,
                "patterns": []
            },
            "content_moderation": {
                "flags": [],
                "is_safe": True,
                "details": {}
            }
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_httpx_response(200, api_response)
            )

            service = SafetyService()
            result = await service.scan_text(
                "Looking for a technical co-founder for my SaaS startup!"
            )

            assert result.contains_pii is False
            assert result.is_scam is False
            assert result.is_safe is True
            assert len(result.content_flags) == 0

    @pytest.mark.asyncio
    async def test_scan_text_empty_string(self):
        """Test scanning empty text returns safe."""
        service = SafetyService()
        result = await service.scan_text("")

        assert result.is_safe is True
        assert result.contains_pii is False
        assert result.is_scam is False

    @pytest.mark.asyncio
    async def test_scan_text_whitespace_only(self):
        """Test scanning whitespace-only text returns safe."""
        service = SafetyService()
        result = await service.scan_text("   \n\t  ")

        assert result.is_safe is True

    @pytest.mark.asyncio
    async def test_detect_pii_standalone(self, mock_httpx_response):
        """Test detect_pii convenience method."""
        api_response = {
            "pii": {
                "detected": True,
                "types": ["email", "address"],
                "details": {}
            }
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_httpx_response(200, api_response)
            )

            service = SafetyService()
            pii_types = await service.detect_pii("Email: test@example.com")

            assert "email" in pii_types
            assert "address" in pii_types

    @pytest.mark.asyncio
    async def test_detect_scam_standalone(self, mock_httpx_response):
        """Test detect_scam convenience method."""
        api_response = {
            "scam_detection": {
                "is_scam": True,
                "confidence": 0.92,
                "patterns": ["phishing"]
            }
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_httpx_response(200, api_response)
            )

            service = SafetyService()
            confidence = await service.detect_scam("Click this link to claim your prize!")

            assert confidence == 0.92

    @pytest.mark.asyncio
    async def test_moderate_content_standalone(self, mock_httpx_response):
        """Test moderate_content convenience method."""
        api_response = {
            "content_moderation": {
                "flags": ["hate_speech", "violence"],
                "is_safe": False,
                "details": {}
            }
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_httpx_response(200, api_response)
            )

            service = SafetyService()
            flags = await service.moderate_content("Offensive content here")

            assert "hate_speech" in flags
            assert "violence" in flags

    @pytest.mark.asyncio
    async def test_api_timeout_graceful_degradation(self):
        """Test that timeout errors don't block content (graceful degradation)."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.TimeoutException("Request timeout")
            )

            service = SafetyService()
            result = await service.scan_text("Some content")

            # Should return safe on timeout (graceful degradation)
            assert result.is_safe is True

    @pytest.mark.asyncio
    async def test_api_500_error_graceful_degradation(self, mock_httpx_response):
        """Test that 500 errors don't block content (graceful degradation)."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = mock_httpx_response(500, {})
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            service = SafetyService()
            result = await service.scan_text("Some content")

            # Should return safe on server error (graceful degradation)
            assert result.is_safe is True

    @pytest.mark.asyncio
    async def test_api_400_error_raises_exception(self, mock_httpx_response):
        """Test that 400 errors raise SafetyServiceError."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = mock_httpx_response(400, {"error": "Invalid request"})
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            service = SafetyService()

            with pytest.raises(SafetyServiceError):
                await service.scan_text("Some content")

    @pytest.mark.asyncio
    async def test_scam_confidence_threshold(self, mock_httpx_response):
        """Test scam confidence threshold logic."""
        # Test medium confidence (0.5) - not flagged as scam
        api_response = {
            "scam_detection": {
                "is_scam": False,
                "confidence": 0.5,
                "patterns": []
            },
            "pii": {"detected": False, "types": []},
            "content_moderation": {"flags": [], "is_safe": True}
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_httpx_response(200, api_response)
            )

            service = SafetyService()
            result = await service.scan_text("Some content")

            # 0.5 < 0.7 threshold, so not marked as scam
            assert result.scam_confidence == 0.5
            assert result.is_scam is False
            assert result.is_safe is True

    @pytest.mark.asyncio
    async def test_safety_check_dataclass_defaults(self):
        """Test SafetyCheck dataclass default values."""
        check = SafetyCheck()

        assert check.contains_pii is False
        assert check.pii_types == []
        assert check.is_scam is False
        assert check.scam_confidence == 0.0
        assert check.content_flags == []
        assert check.is_safe is True
        assert check.details == {}

    @pytest.mark.asyncio
    async def test_singleton_instance(self):
        """Test that safety_service is a singleton."""
        from app.services.safety_service import safety_service as service1
        from app.services.safety_service import safety_service as service2

        assert service1 is service2
        assert isinstance(service1, SafetyService)

    @pytest.mark.asyncio
    async def test_parse_response_with_missing_fields(self):
        """Test parsing API response with missing optional fields."""
        service = SafetyService()

        # Minimal response
        api_response = {
            "pii": {"detected": False},
            "scam_detection": {},
            "content_moderation": {}
        }

        result = service._parse_safety_response(api_response)

        assert result.contains_pii is False
        assert result.pii_types == []
        assert result.scam_confidence == 0.0
        assert result.is_safe is True

    @pytest.mark.asyncio
    async def test_checks_parameter_filtering(self, mock_httpx_response):
        """Test that checks parameter filters requested checks."""
        api_response = {
            "pii": {
                "detected": True,
                "types": ["email"],
                "details": {}
            }
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_httpx_response(200, api_response))
            mock_client.return_value.__aenter__.return_value.post = mock_post

            service = SafetyService()
            await service.scan_text("test@example.com", checks=["pii"])

            # Verify the API was called with the correct checks parameter
            call_args = mock_post.call_args
            assert call_args[1]["json"]["checks"] == ["pii"]

    @pytest.mark.asyncio
    async def test_medium_scam_confidence_logged_but_safe(self, mock_httpx_response):
        """Test medium confidence scams (0.5-0.7) are logged but don't block."""
        api_response = {
            "scam_detection": {
                "is_scam": False,
                "confidence": 0.6,
                "patterns": ["suspicious_language"]
            },
            "pii": {"detected": False, "types": []},
            "content_moderation": {"flags": [], "is_safe": True}
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_httpx_response(200, api_response)
            )

            service = SafetyService()
            result = await service.scan_text("Somewhat suspicious content")

            # Medium confidence doesn't trigger is_scam (threshold is 0.7)
            assert result.scam_confidence == 0.6
            assert result.is_scam is False
            assert result.is_safe is True


class TestSafetyCheckDataclass:
    """Test SafetyCheck dataclass behavior."""

    def test_safety_check_creation(self):
        """Test creating SafetyCheck with custom values."""
        check = SafetyCheck(
            contains_pii=True,
            pii_types=["email", "phone"],
            is_scam=True,
            scam_confidence=0.9,
            content_flags=["spam"],
            is_safe=False,
            details={"test": "data"}
        )

        assert check.contains_pii is True
        assert check.pii_types == ["email", "phone"]
        assert check.is_scam is True
        assert check.scam_confidence == 0.9
        assert check.content_flags == ["spam"]
        assert check.is_safe is False
        assert check.details == {"test": "data"}

    def test_safety_check_list_mutation(self):
        """Test that default list fields don't share state."""
        check1 = SafetyCheck()
        check2 = SafetyCheck()

        check1.pii_types.append("email")

        # check2 should not be affected
        assert "email" not in check2.pii_types
        assert len(check2.pii_types) == 0
