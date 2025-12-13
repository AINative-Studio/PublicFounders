"""
ZeroDB Client - NoSQL Table Operations via Direct API

This client handles all NoSQL table CRUD operations for PublicFounders.
Replaces PostgreSQL/SQLAlchemy for relational data storage.

Tables:
- users: User accounts and authentication
- founder_profiles: Founder profile details
- goals: Founder goals and objectives
- asks: Help requests
- posts: Founder updates and content
- companies: Company information
- company_roles: User-company relationships
- introductions: Introduction tracking
"""
import logging
import httpx
from typing import Any, Dict, List, Optional
from datetime import datetime
from uuid import UUID
from app.core.config import settings

logger = logging.getLogger(__name__)


class ZeroDBClient:
    """
    Client for ZeroDB NoSQL table operations via direct API calls.

    Uses ZeroDB REST API for all database operations.
    """

    def __init__(self):
        """Initialize ZeroDB client with API credentials."""
        self.project_id = settings.ZERODB_PROJECT_ID
        self.api_key = settings.ZERODB_API_KEY
        self.base_url = "https://api.zerodb.ai/v1"
        logger.info(f"ZeroDB Client initialized for project: {self.project_id}")

    def _get_headers(self) -> Dict[str, str]:
        """Get API request headers."""
        return {
            "X-Project-ID": self.project_id,
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }

    async def insert_rows(
        self,
        table_name: str,
        rows: List[Dict[str, Any]],
        return_ids: bool = True
    ) -> Dict[str, Any]:
        """
        Insert rows into ZeroDB NoSQL table.

        Args:
            table_name: Name of the table
            rows: List of row dictionaries to insert
            return_ids: Whether to return inserted row IDs

        Returns:
            Result dictionary with status and optional IDs

        Example:
            await client.insert_rows("users", [{
                "id": str(uuid4()),
                "email": "founder@example.com",
                "name": "Jane Founder",
                "created_at": datetime.utcnow().isoformat()
            }])
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/tables/{table_name}/rows",
                    headers=self._get_headers(),
                    json={"rows": rows, "return_ids": return_ids},
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()
                logger.info(f"Inserted {len(rows)} rows into {table_name}")
                return result
        except httpx.HTTPStatusError as e:
            logger.error(f"Error inserting rows into {table_name}: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error inserting rows into {table_name}: {e}")
            raise

    async def query_rows(
        self,
        table_name: str,
        filter: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
        projection: Optional[Dict[str, Any]] = None,
        sort: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Query rows from ZeroDB NoSQL table.

        Args:
            table_name: Name of the table
            filter: MongoDB-style query filter (e.g., {"email": "test@example.com"})
            limit: Maximum number of results
            offset: Number of results to skip
            projection: Fields to include/exclude
            sort: Sort specification

        Returns:
            List of matching rows

        Example:
            users = await client.query_rows(
                table_name="users",
                filter={"linkedin_id": "abc123"},
                limit=1
            )
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/tables/{table_name}/query",
                    headers=self._get_headers(),
                    json={
                        "filter": filter or {},
                        "limit": limit,
                        "offset": offset,
                        "projection": projection,
                        "sort": sort
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()
                rows = result.get("rows", [])
                logger.debug(f"Queried {len(rows)} rows from {table_name}")
                return rows
        except httpx.HTTPStatusError as e:
            logger.error(f"Error querying {table_name}: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error querying {table_name}: {e}")
            raise

    async def update_rows(
        self,
        table_name: str,
        filter: Dict[str, Any],
        update: Dict[str, Any],
        upsert: bool = False
    ) -> Dict[str, Any]:
        """
        Update rows in ZeroDB NoSQL table.

        Args:
            table_name: Name of the table
            filter: Query filter to match rows to update
            update: Update operations (e.g., {"$set": {"name": "New Name"}})
            upsert: If True, insert if not found

        Returns:
            Result dictionary with update status

        Example:
            await client.update_rows(
                table_name="users",
                filter={"id": user_id},
                update={"$set": {"name": "Updated Name", "updated_at": datetime.utcnow().isoformat()}}
            )
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"{self.base_url}/tables/{table_name}/rows",
                    headers=self._get_headers(),
                    json={
                        "filter": filter,
                        "update": update,
                        "upsert": upsert
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()
                logger.info(f"Updated rows in {table_name} with filter: {filter}")
                return result
        except httpx.HTTPStatusError as e:
            logger.error(f"Error updating {table_name}: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error updating {table_name}: {e}")
            raise

    async def delete_rows(
        self,
        table_name: str,
        filter: Dict[str, Any],
        limit: int = 0
    ) -> Dict[str, Any]:
        """
        Delete rows from ZeroDB NoSQL table.

        Args:
            table_name: Name of the table
            filter: Query filter to match rows to delete
            limit: Maximum rows to delete (0 = all matching)

        Returns:
            Result dictionary with deletion status

        Example:
            await client.delete_rows(
                table_name="users",
                filter={"id": user_id}
            )
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    "DELETE",
                    f"{self.base_url}/tables/{table_name}/rows",
                    headers=self._get_headers(),
                    json={
                        "filter": filter,
                        "limit": limit
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()
                logger.info(f"Deleted rows from {table_name} with filter: {filter}")
                return result
        except httpx.HTTPStatusError as e:
            logger.error(f"Error deleting from {table_name}: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error deleting from {table_name}: {e}")
            raise

    async def get_by_id(
        self,
        table_name: str,
        id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a single row by ID (convenience method).

        Args:
            table_name: Name of the table
            id: Row ID (as string)

        Returns:
            Row dictionary or None if not found
        """
        rows = await self.query_rows(
            table_name=table_name,
            filter={"id": id},
            limit=1
        )
        return rows[0] if rows else None

    async def get_by_field(
        self,
        table_name: str,
        field: str,
        value: Any
    ) -> Optional[Dict[str, Any]]:
        """
        Get a single row by field value (convenience method).

        Args:
            table_name: Name of the table
            field: Field name
            value: Field value

        Returns:
            Row dictionary or None if not found
        """
        rows = await self.query_rows(
            table_name=table_name,
            filter={field: value},
            limit=1
        )
        return rows[0] if rows else None

    # Helper methods for common patterns

    def prepare_insert_data(
        self,
        data: Dict[str, Any],
        id: Optional[UUID] = None,
        add_timestamps: bool = True
    ) -> Dict[str, Any]:
        """
        Prepare data for insertion with ID and timestamps.

        Args:
            data: Raw data dictionary
            id: Optional UUID (will generate if not provided)
            add_timestamps: Whether to add created_at/updated_at

        Returns:
            Data dictionary ready for insertion
        """
        from uuid import uuid4

        prepared = {**data}

        if id:
            prepared["id"] = str(id)
        elif "id" not in prepared:
            prepared["id"] = str(uuid4())

        if add_timestamps:
            now = datetime.utcnow().isoformat()
            if "created_at" not in prepared:
                prepared["created_at"] = now
            if "updated_at" not in prepared:
                prepared["updated_at"] = now

        return prepared

    def prepare_update_data(
        self,
        data: Dict[str, Any],
        add_timestamp: bool = True
    ) -> Dict[str, Any]:
        """
        Prepare data for update operation.

        Args:
            data: Fields to update
            add_timestamp: Whether to add updated_at

        Returns:
            Update dictionary with $set operator
        """
        update_data = {**data}

        if add_timestamp:
            update_data["updated_at"] = datetime.utcnow().isoformat()

        return {"$set": update_data}


# Singleton instance
zerodb_client = ZeroDBClient()
