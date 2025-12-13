"""
Database Configuration Stub
This file exists to prevent import errors from legacy SQLAlchemy models.
The actual database layer uses ZeroDB through zerodb_client.
"""
from sqlalchemy.ext.declarative import declarative_base

# Create a base class for SQLAlchemy models (legacy compatibility)
Base = declarative_base()


# Stub function for dependency injection (not used with ZeroDB)
async def get_db():
    """Legacy database session getter - not used with ZeroDB"""
    raise NotImplementedError("This application uses ZeroDB, not SQLAlchemy sessions")
