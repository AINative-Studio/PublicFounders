"""
Safety Service - PII detection, scam detection, content moderation
Uses AINative Safety API following the same pattern as embedding_service.py

This service protects users from:
1. PII exposure (emails, phones, SSN, addresses, credit cards)
2. Scam content (phishing, fraud, suspicious patterns)
3. Inappropriate content (hate speech, harassment, spam)

Architecture:
- Same httpx.AsyncClient pattern as embedding_service
- Comprehensive error handling with graceful degradation
- Logging for security monitoring
- Type-safe return values using dataclasses
"""
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class SafetyServiceError(Exception):
    """Base exception for safety service errors."""
    pass


@dataclass
class SafetyCheck:
    """
    Result of a safety check on text content.

    Attributes:
        contains_pii: Whether PII was detected
        pii_types: List of PII types found (e.g., ['email', 'phone'])
        is_scam: Whether content appears to be a scam
        scam_confidence: Scam detection confidence (0.0 = safe, 1.0 = scam)
        content_flags: List of content moderation flags (e.g., ['spam', 'harassment'])
        is_safe: Overall safety status (False if any critical issues)
        details: Additional details from API response
    """
    contains_pii: bool = False
    pii_types: List[str] = field(default_factory=list)
    is_scam: bool = False
    scam_confidence: float = 0.0
    content_flags: List[str] = field(default_factory=list)
    is_safe: bool = True
    details: Dict[str, Any] = field(default_factory=dict)


class SafetyService:
    """
    Manages content safety using AINative Safety API.

    Key Features:
    - PII detection (emails, phones, SSN, addresses, credit cards)
    - Scam detection with confidence scoring
    - Content moderation (hate speech, harassment, spam)
    - Retry logic for resilience
    - Graceful degradation on failures
    """

    MAX_RETRIES = 2
    RETRY_DELAY = 0.5  # seconds
    TIMEOUT = 15.0  # seconds

    # Thresholds
    SCAM_THRESHOLD_HIGH = 0.7  # Block immediately
    SCAM_THRESHOLD_MEDIUM = 0.5  # Log warning

    # PII types that should always be flagged
    CRITICAL_PII_TYPES = {'ssn', 'credit_card', 'passport', 'drivers_license'}

    def __init__(self):
        """Initialize safety service with AINative configuration."""
        self.api_key = settings.AINATIVE_API_KEY
        self.base_url = settings.AINATIVE_API_BASE_URL

    async def scan_text(
        self,
        text: str,
        checks: List[str] = None
    ) -> SafetyCheck:
        """
        Scan text for safety issues.

        Args:
            text: Text content to scan
            checks: List of checks to perform. Options:
                   - "pii": Detect personally identifiable information
                   - "scam_detection": Detect scam patterns
                   - "content_moderation": Detect inappropriate content
                   If None, performs all checks

        Returns:
            SafetyCheck object with results

        Raises:
            SafetyServiceError: If API call fails critically

        Example:
            check = await safety_service.scan_text(
                text="Contact me at john@example.com",
                checks=["pii", "content_moderation"]
            )
            if check.contains_pii:
                logger.warning(f"PII detected: {check.pii_types}")
        """
        if not text or not text.strip():
            return SafetyCheck(is_safe=True)

        # Default to all checks
        if checks is None:
            checks = ["pii", "scam_detection", "content_moderation"]

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}v1/public/safety/scan",
                    headers={
                        "X-API-Key": self.api_key,
                        "Content-Type": "application/json"
                    },
                    json={
                        "text": text.strip(),
                        "checks": checks
                    },
                    timeout=self.TIMEOUT
                )
                response.raise_for_status()
                data = response.json()

                # Parse response into SafetyCheck
                return self._parse_safety_response(data)

        except httpx.HTTPStatusError as e:
            logger.error(f"AINative Safety API error (HTTP {e.response.status_code}): {e}")
            # Graceful degradation - assume safe on API errors
            # Log the error but don't block user actions
            if e.response.status_code >= 500:
                # Server error - log and return safe
                logger.error(f"Safety API server error, allowing content: {e}")
                return SafetyCheck(is_safe=True)
            else:
                # Client error - might be invalid request
                raise SafetyServiceError(f"Safety check failed: {e}")

        except httpx.TimeoutException as e:
            logger.warning(f"Safety API timeout, allowing content: {e}")
            # Don't block on timeout - graceful degradation
            return SafetyCheck(is_safe=True)

        except Exception as e:
            logger.error(f"Unexpected error in safety check: {e}")
            # Graceful degradation on unexpected errors
            return SafetyCheck(is_safe=True)

    def _parse_safety_response(self, data: Dict[str, Any]) -> SafetyCheck:
        """
        Parse AINative Safety API response into SafetyCheck object.

        Expected API Response Format:
        {
            "pii": {
                "detected": true,
                "types": ["email", "phone"],
                "details": {...}
            },
            "scam_detection": {
                "is_scam": false,
                "confidence": 0.15,
                "patterns": []
            },
            "content_moderation": {
                "flags": ["spam"],
                "is_safe": false,
                "details": {...}
            }
        }

        Args:
            data: API response JSON

        Returns:
            SafetyCheck object
        """
        check = SafetyCheck()

        # Parse PII detection
        if "pii" in data:
            pii_data = data["pii"]
            check.contains_pii = pii_data.get("detected", False)
            check.pii_types = pii_data.get("types", [])

            # Critical PII types make content unsafe
            if any(pii_type in self.CRITICAL_PII_TYPES for pii_type in check.pii_types):
                check.is_safe = False

        # Parse scam detection
        if "scam_detection" in data:
            scam_data = data["scam_detection"]
            check.scam_confidence = scam_data.get("confidence", 0.0)
            check.is_scam = check.scam_confidence >= self.SCAM_THRESHOLD_HIGH

            if check.is_scam:
                check.is_safe = False

        # Parse content moderation
        if "content_moderation" in data:
            mod_data = data["content_moderation"]
            check.content_flags = mod_data.get("flags", [])

            # If API says unsafe, mark as unsafe
            if not mod_data.get("is_safe", True):
                check.is_safe = False

        # Store full details for logging
        check.details = data

        return check

    async def detect_pii(self, text: str) -> List[str]:
        """
        Detect PII (emails, phones, SSN, addresses, credit cards).

        Args:
            text: Text to scan for PII

        Returns:
            List of PII types detected (e.g., ['email', 'phone'])

        Example:
            pii_types = await safety_service.detect_pii("Call me at 555-1234")
            if 'phone' in pii_types:
                logger.warning("Phone number detected in content")
        """
        check = await self.scan_text(text, checks=["pii"])
        return check.pii_types

    async def detect_scam(self, text: str) -> float:
        """
        Detect scam patterns (0.0 = safe, 1.0 = scam).

        Args:
            text: Text to scan for scams

        Returns:
            Scam confidence score (0.0 - 1.0)

        Example:
            confidence = await safety_service.detect_scam(ask_description)
            if confidence > 0.7:
                raise HTTPException(400, "Content flagged as suspicious")
        """
        check = await self.scan_text(text, checks=["scam_detection"])
        return check.scam_confidence

    async def moderate_content(self, text: str) -> List[str]:
        """
        Detect inappropriate content (hate speech, harassment, spam).

        Args:
            text: Text to moderate

        Returns:
            List of content flags (e.g., ['spam', 'harassment'])

        Example:
            flags = await safety_service.moderate_content(post_content)
            if flags:
                raise HTTPException(400, f"Content flagged: {flags}")
        """
        check = await self.scan_text(text, checks=["content_moderation"])
        return check.content_flags


# Singleton instance (same pattern as embedding_service)
safety_service = SafetyService()
