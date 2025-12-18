"""
Authentication Service - ZeroDB Edition
Handles LinkedIn OAuth, user creation, and authentication using ZeroDB NoSQL
"""
import uuid
from datetime import datetime
from typing import Optional, Tuple
from app.services.zerodb_client import zerodb_client
from app.schemas.user import LinkedInUserData
from app.core.enums import AutonomyMode


class AuthService:
    """Service for authentication and user management using ZeroDB"""

    def __init__(self):
        """Initialize auth service (no DB session needed anymore)"""
        pass

    async def create_user_from_linkedin(
        self,
        linkedin_data: LinkedInUserData
    ) -> Tuple[dict, dict]:
        """
        Create user and founder profile from LinkedIn OAuth data

        Args:
            linkedin_data: LinkedIn user data from OAuth

        Returns:
            Tuple of (user_dict, profile_dict)

        Raises:
            ValueError: If linkedin_data is invalid
            Exception: If LinkedIn ID already exists
        """
        if not linkedin_data:
            raise ValueError("LinkedIn data is required")

        # Check if user already exists
        existing_user = await zerodb_client.get_by_field(
            table_name="users",
            field="linkedin_id",
            value=linkedin_data.linkedin_id
        )

        if existing_user:
            raise Exception(f"User with LinkedIn ID {linkedin_data.linkedin_id} already exists")

        # Generate user ID
        user_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        # Create user data
        user_data = {
            "id": user_id,
            "linkedin_id": linkedin_data.linkedin_id,
            "full_name": linkedin_data.name,  # Used by frontend
            "first_name": linkedin_data.first_name,
            "last_name": linkedin_data.last_name,
            "headline": linkedin_data.headline,
            "profile_photo_url": linkedin_data.profile_photo_url,
            "location": linkedin_data.location,
            "email": linkedin_data.email,
            "phone_number": None,
            "phone_verified": False,
            "created_at": now,
            "updated_at": now
        }

        # Insert user into ZeroDB
        await zerodb_client.insert_rows(
            table_name="users",
            rows=[user_data]
        )

        # Create founder profile data
        profile_id = str(uuid.uuid4())
        profile_data = {
            "id": profile_id,
            "user_id": user_id,
            "bio": None,
            "current_focus": None,
            "autonomy_mode": AutonomyMode.SUGGEST.value,
            "public_visibility": True,
            "embedding_id": None,
            "created_at": now,
            "updated_at": now
        }

        # Insert profile into ZeroDB
        await zerodb_client.insert_rows(
            table_name="founder_profiles",
            rows=[profile_data]
        )

        return user_data, profile_data

    async def get_user_by_linkedin_id(self, linkedin_id: str) -> Optional[dict]:
        """
        Retrieve user by LinkedIn ID

        Args:
            linkedin_id: LinkedIn user ID

        Returns:
            User dictionary if found, None otherwise
        """
        return await zerodb_client.get_by_field(
            table_name="users",
            field="linkedin_id",
            value=linkedin_id
        )

    async def get_user_by_id(self, user_id: uuid.UUID) -> Optional[dict]:
        """
        Retrieve user by UUID

        Args:
            user_id: User UUID

        Returns:
            User dictionary if found, None otherwise
        """
        return await zerodb_client.get_by_id(
            table_name="users",
            id=str(user_id)
        )

    async def update_last_login(self, user_id: uuid.UUID) -> None:
        """
        Update user's last login timestamp

        Args:
            user_id: User UUID
        """
        await zerodb_client.update_rows(
            table_name="users",
            filter={"id": str(user_id)},
            update={"$set": {
                "last_login_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }}
        )

    async def get_or_create_user_from_linkedin(
        self,
        linkedin_data: LinkedInUserData
    ) -> Tuple[dict, dict, bool]:
        """
        Get existing user or create new one from LinkedIn data

        Args:
            linkedin_data: LinkedIn user data

        Returns:
            Tuple of (user_dict, profile_dict, created: bool)
        """
        # Check if user exists
        existing_user = await self.get_user_by_linkedin_id(linkedin_data.linkedin_id)

        if existing_user:
            # Load founder profile
            profiles = await zerodb_client.query_rows(
                table_name="founder_profiles",
                filter={"user_id": existing_user["id"]},
                limit=1
            )
            profile = profiles[0] if profiles else None

            # Update last login
            await self.update_last_login(uuid.UUID(existing_user["id"]))

            return existing_user, profile, False

        # Create new user
        user, profile = await self.create_user_from_linkedin(linkedin_data)
        return user, profile, True
