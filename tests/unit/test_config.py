"""
Unit tests for application configuration.
"""
import pytest
from backend.app.core.config import Settings


@pytest.mark.unit
class TestSettings:
    """Test application settings."""

    def test_settings_defaults(self):
        """Test default settings values."""
        settings = Settings()

        assert settings.APP_NAME == "PublicFounders API"
        assert settings.APP_VERSION == "1.0.0"
        assert settings.ENVIRONMENT == "development"
        assert settings.DEBUG is False
        assert settings.HOST == "0.0.0.0"
        assert settings.PORT == 8000

    def test_settings_database_url_validation(self):
        """Test database URL validation."""
        with pytest.raises(ValueError):
            Settings(DATABASE_URL="")

    def test_settings_jwt_defaults(self):
        """Test JWT settings defaults."""
        settings = Settings()

        assert settings.JWT_ALGORITHM == "HS256"
        assert settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES == 60 * 24 * 7

    def test_settings_embedding_defaults(self):
        """Test embedding settings defaults."""
        settings = Settings()

        assert settings.EMBEDDING_MODEL == "text-embedding-3-small"
        assert settings.EMBEDDING_DIMENSIONS == 1536

    def test_settings_cors_defaults(self):
        """Test CORS settings defaults."""
        settings = Settings()

        assert isinstance(settings.CORS_ORIGINS, list)
        assert "http://localhost:3000" in settings.CORS_ORIGINS
        assert "http://localhost:8000" in settings.CORS_ORIGINS
