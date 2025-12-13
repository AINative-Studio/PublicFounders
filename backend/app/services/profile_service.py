"""
Profile Service - ZeroDB Edition
Handles founder profile CRUD operations using ZeroDB NoSQL
"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from app.services.zerodb_client import zerodb_client
from app.schemas.founder_profile import FounderProfileUpdate
from app.services.embedding_service import embedding_service


class ProfileService:
    """Service for founder profile management using ZeroDB"""

    def __init__(self):
        """Initialize profile service (no DB session needed)"""
        self.embedding_service = embedding_service

    async def get_profile(self, user_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """
        Get founder profile by user ID

        Args:
            user_id: User UUID

        Returns:
            Profile dictionary if found, None otherwise
        """
        profiles = await zerodb_client.query_rows(
            table_name="founder_profiles",
            filter={"user_id": str(user_id)},
            limit=1
        )
        return profiles[0] if profiles else None

    async def update_profile(
        self,
        user_id: uuid.UUID,
        update_data: FounderProfileUpdate
    ) -> Dict[str, Any]:
        """
        Update founder profile

        Args:
            user_id: User UUID
            update_data: Profile update data

        Returns:
            Updated profile dictionary

        Raises:
            ValueError: If profile not found
            Exception: If embedding generation fails
        """
        # Get profile
        profile = await self.get_profile(user_id)
        if not profile:
            raise ValueError("Profile not found")

        # Get user (needed for embedding)
        user = await zerodb_client.get_by_id(
            table_name="users",
            id=str(user_id)
        )
        if not user:
            raise ValueError("User not found")

        try:
            # Prepare update fields (only non-None values)
            update_dict = update_data.model_dump(exclude_unset=True)
            update_dict["updated_at"] = datetime.utcnow().isoformat()

            # Check if content changed (for embedding)
            content_changed = (
                update_data.bio is not None or
                update_data.current_focus is not None
            )

            if content_changed:
                # Create/update embedding
                # Note: embedding_service.create_profile_embedding expects User and FounderProfile objects
                # We'll need to create mock objects or update the embedding service
                # For now, we'll merge the profile with updates
                updated_profile = {**profile, **update_dict}

                # Generate embedding text
                embedding_text = f"{updated_profile.get('bio', '')} {updated_profile.get('current_focus', '')}"

                if embedding_text.strip():
                    try:
                        # Store embedding in ZeroDB vectors
                        from uuid import UUID as UUIDClass
                        embedding_vector = await self.embedding_service.generate_embedding(embedding_text)

                        # Store vector
                        vector_id = await self.embedding_service.upsert_vector(
                            entity_type="founder",
                            entity_id=UUIDClass(profile["id"]),
                            embedding=embedding_vector,
                            document=embedding_text,
                            metadata={
                                "user_id": str(user_id),
                                "bio": updated_profile.get("bio"),
                                "current_focus": updated_profile.get("current_focus")
                            }
                        )

                        update_dict["embedding_id"] = vector_id
                        update_dict["embedding_updated_at"] = datetime.utcnow().isoformat()
                    except Exception as e:
                        # Log error but don't fail the entire update
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"Failed to create embedding for profile {user_id}: {e}")

            # Update profile in ZeroDB
            await zerodb_client.update_rows(
                table_name="founder_profiles",
                filter={"user_id": str(user_id)},
                update={"$set": update_dict}
            )

            # Fetch updated profile
            updated_profile = await self.get_profile(user_id)
            return updated_profile

        except Exception as e:
            raise e

    async def get_public_profiles(
        self,
        limit: int = 10,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get public founder profiles

        Args:
            limit: Maximum number of profiles to return
            offset: Pagination offset

        Returns:
            List of public profile dictionaries
        """
        profiles = await zerodb_client.query_rows(
            table_name="founder_profiles",
            filter={"public_visibility": True},
            limit=limit,
            offset=offset
        )
        return profiles

    async def get_profile_with_user(
        self,
        user_id: uuid.UUID
    ) -> Optional[tuple[Dict[str, Any], Dict[str, Any]]]:
        """
        Get user and profile together

        Args:
            user_id: User UUID

        Returns:
            Tuple of (user_dict, profile_dict) if found, None otherwise
        """
        user = await zerodb_client.get_by_id(
            table_name="users",
            id=str(user_id)
        )
        if not user:
            return None

        profile = await self.get_profile(user_id)
        if not profile:
            return None

        return user, profile
