"""
Profile Service
Handles founder profile CRUD operations
"""
import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.founder_profile import FounderProfile
from app.schemas.founder_profile import FounderProfileUpdate
from app.services.embedding_service import embedding_service


class ProfileService:
    """Service for founder profile management"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_service = embedding_service

    async def get_profile(self, user_id: uuid.UUID) -> Optional[FounderProfile]:
        """
        Get founder profile by user ID

        Args:
            user_id: User UUID

        Returns:
            FounderProfile if found, None otherwise
        """
        return await self.db.get(FounderProfile, user_id)

    async def update_profile(
        self,
        user_id: uuid.UUID,
        update_data: FounderProfileUpdate
    ) -> FounderProfile:
        """
        Update founder profile

        Args:
            user_id: User UUID
            update_data: Profile update data

        Returns:
            Updated FounderProfile

        Raises:
            ValueError: If profile not found
            Exception: If embedding generation fails (triggers rollback)
        """
        # Get profile
        profile = await self.db.get(FounderProfile, user_id)
        if not profile:
            raise ValueError("Profile not found")

        # Get user (needed for embedding)
        user = await self.db.get(User, user_id)
        if not user:
            raise ValueError("User not found")

        try:
            # Update fields (only non-None values)
            update_dict = update_data.model_dump(exclude_unset=True)

            for field, value in update_dict.items():
                setattr(profile, field, value)

            profile.updated_at = datetime.utcnow()

            # Flush changes to DB (but don't commit yet)
            await self.db.flush()

            # Trigger embedding pipeline if content changed
            if update_data.bio is not None or update_data.current_focus is not None:
                embedding_id = await self.embedding_service.create_profile_embedding(
                    user, profile
                )

                # Update embedding metadata
                profile.embedding_id = embedding_id
                profile.embedding_updated_at = datetime.utcnow()

            # Commit transaction (atomic update)
            await self.db.commit()
            await self.db.refresh(profile)

            return profile

        except Exception as e:
            # Rollback on any error (no partial updates)
            await self.db.rollback()
            raise e

    async def get_public_profiles(
        self,
        limit: int = 10,
        offset: int = 0
    ) -> List[FounderProfile]:
        """
        Get public founder profiles

        Args:
            limit: Maximum number of profiles to return
            offset: Pagination offset

        Returns:
            List of public FounderProfile objects
        """
        stmt = (
            select(FounderProfile)
            .where(FounderProfile.public_visibility == True)
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_profile_with_user(
        self,
        user_id: uuid.UUID
    ) -> Optional[tuple[User, FounderProfile]]:
        """
        Get user and profile together

        Args:
            user_id: User UUID

        Returns:
            Tuple of (User, FounderProfile) if found, None otherwise
        """
        user = await self.db.get(User, user_id)
        if not user:
            return None

        profile = await self.db.get(FounderProfile, user_id)
        if not profile:
            return None

        return user, profile
