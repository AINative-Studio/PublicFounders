"""
FastAPI Application Entry Point
PublicFounders - Semantic AI Founder Network
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import API router with error handling
try:
    from app.api.v1 import api_router
    logger.info(f"API router imported successfully with {len(api_router.routes)} routes")
except Exception as e:
    logger.error(f"Failed to import API router: {type(e).__name__}: {str(e)}")
    logger.exception("Full traceback:")
    # Create empty router as fallback
    from fastapi import APIRouter
    api_router = APIRouter()
    logger.warning("Using empty API router as fallback")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    # Note: ZeroDB initialization handled via environment variables
    yield
    # Shutdown
    # Note: ZeroDB connections managed automatically


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Semantic AI-powered founder networking platform",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Configure CORS - local development and production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:4000",
        "http://localhost:8000",
        "http://localhost:9000",
        "https://publicfounders.ainative.studio",
        "https://foundersapi.ainative.studio",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "PublicFounders API",
        "version": settings.APP_VERSION,
        "docs": "/api/docs"
    }
