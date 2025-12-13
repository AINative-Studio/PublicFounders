"""
Authentication Service
Handles LinkedIn OAuth, user creation, and authentication
"""
import uuid
from datetime import datetime
from typing import Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.founder_profile import FounderProfile, AutonomyMode
from app.schemas.user import LinkedInUserData


class AuthService:
    """Service for authentication and user management"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_user_from_linkedin(
        self,
        linkedin_data: LinkedInUserData
    ) -> Tuple[User, FounderProfile]:
        """
        Create user and founder profile from LinkedIn OAuth data

        Args:
            linkedin_data: LinkedIn user data from OAuth

        Returns:
            Tuple of (User, FounderProfile)

        Raises:
            ValueError: If linkedin_data is invalid
            IntegrityError: If LinkedIn ID already exists
        """
        if not linkedin_data:
            raise ValueError("LinkedIn data is required")

        # Create user
        user = User(
            id=uuid.uuid4(),
            linkedin_id=linkedin_data.linkedin_id,
            name=linkedin_data.name,
            headline=linkedin_data.headline,
            profile_photo_url=linkedin_data.profile_photo_url,
            location=linkedin_data.location,
            email=linkedin_data.email,
            phone_verified=False,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        self.db.add(user)
        await self.db.flush()  # Get user.id

        # Create founder profile (transactional with user)
        profile = FounderProfile(
            user_id=user.id,
            bio=None,
            current_focus=None,
            autonomy_mode=AutonomyMode.SUGGEST,
            public_visibility=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        self.db.add(profile)
        await self.db.commit()
        await self.db.refresh(user)
        await self.db.refresh(profile)

        return user, profile

    async def get_user_by_linkedin_id(self, linkedin_id: str) -> Optional[User]:
        """
        Retrieve user by LinkedIn ID

        Args:
            linkedin_id: LinkedIn user ID

        Returns:
            User if found, None otherwise
        """
        stmt = select(User).where(User.linkedin_id == linkedin_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """
        Retrieve user by UUID

        Args:
            user_id: User UUID

        Returns:
            User if found, None otherwise
        """
        return await self.db.get(User, user_id)

    async def update_last_login(self, user_id: uuid.UUID) -> None:
        """
        Update user's last login timestamp

        Args:
            user_id: User UUID
        """
        user = await self.db.get(User, user_id)
        if user:
            user.last_login_at = datetime.utcnow()
            user.updated_at = datetime.utcnow()
            await self.db.commit()

    async def get_or_create_user_from_linkedin(
        self,
        linkedin_data: LinkedInUserData
    ) -> Tuple[User, FounderProfile, bool]:
        """
        Get existing user or create new one from LinkedIn data

        Args:
            linkedin_data: LinkedIn user data

        Returns:
            Tuple of (User, FounderProfile, created: bool)
        """
        # Check if user exists
        existing_user = await self.get_user_by_linkedin_id(linkedin_data.linkedin_id)

        if existing_user:
            # Load founder profile
            stmt = select(FounderProfile).where(FounderProfile.user_id == existing_user.id)
            result = await self.db.execute(stmt)
            profile = result.scalar_one_or_none()

            # Update last login
            await self.update_last_login(existing_user.id)

            return existing_user, profile, False

        # Create new user
        user, profile = await self.create_user_from_linkedin(linkedin_data)
        return user, profile, True
