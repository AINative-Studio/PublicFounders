"""
Application Configuration
Centralized settings management using Pydantic
"""
from typing import Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings and environment variables"""

    # Application
    APP_NAME: str = "PublicFounders API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database (Optional - using ZeroDB instead)
    DATABASE_URL: Optional[str] = Field(
        default=None,
        description="PostgreSQL connection string (optional - using ZeroDB)"
    )

    # JWT Authentication
    JWT_SECRET_KEY: str = Field(
        default="your-secret-key-change-in-production",
        description="Secret key for JWT token generation"
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # LinkedIn OAuth
    LINKEDIN_CLIENT_ID: Optional[str] = None
    LINKEDIN_CLIENT_SECRET: Optional[str] = None
    LINKEDIN_REDIRECT_URI: str = "http://localhost:9000/api/v1/auth/linkedin/callback"
    LINKEDIN_SCOPE: str = "openid profile email"

    # Twilio (Phone Verification)
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None
    TWILIO_VERIFY_SERVICE_SID: Optional[str] = None

    # ZeroDB / AINative
    AINATIVE_API_KEY: str = Field(
        default="",
        description="AINative API key for ZeroDB"
    )
    AINATIVE_API_BASE_URL: str = "https://api.ainative.studio/"
    AINATIVE_PROJECT_ID: Optional[str] = None

    # ZeroDB Direct Access
    ZERODB_PROJECT_ID: str = Field(
        default="",
        description="ZeroDB Project ID"
    )
    ZERODB_API_KEY: str = Field(
        default="",
        description="ZeroDB API Key"
    )

    # AINative for embeddings (FREE - HuggingFace BAAI/bge-small-en-v1.5)
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_DIMENSIONS: int = 384

    # Frontend URL for OAuth redirects
    FRONTEND_URL: str = Field(
        default="http://localhost:4000",
        description="Frontend URL for OAuth callback redirects"
    )

    # CORS - list of allowed origins
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:4000",
        "http://localhost:8000",
        "http://localhost:9000",
        "https://publicfounders.ainative.studio",
        "https://foundersapi.ainative.studio"
    ]

    # Phone Verification Settings
    PHONE_VERIFICATION_CODE_LENGTH: int = 6
    PHONE_VERIFICATION_CODE_EXPIRY_MINUTES: int = 5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    @validator("DATABASE_URL", pre=True)
    def validate_database_url(cls, v: Optional[str]) -> Optional[str]:
        """Ensure database URL is properly formatted if provided"""
        # DATABASE_URL is optional since we're using ZeroDB
        return v


# Global settings instance
settings = Settings()
