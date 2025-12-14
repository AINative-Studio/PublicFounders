"""
API v1 Router
Combines all endpoint routers
"""
from fastapi import APIRouter
from app.api.v1.endpoints import auth, profile, goals, asks, posts, introductions

api_router = APIRouter()

# Include sub-routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(profile.router, prefix="/profile", tags=["Profile"])

# Sprint 2: Goals, Asks & Posts
api_router.include_router(goals.router, tags=["Goals"])
api_router.include_router(asks.router, tags=["Asks"])
api_router.include_router(posts.router, tags=["Posts"])

# Sprint 3: Introductions
api_router.include_router(introductions.router, tags=["Introductions"])

# Story 8.1: Outcomes (separate router for analytics)
api_router.include_router(introductions.analytics_router, tags=["Outcomes"])
