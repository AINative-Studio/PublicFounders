"""
ZeroDB Client - NoSQL Table Operations via AINative API

This client handles all NoSQL table CRUD operations for PublicFounders.
Uses the AINative ZeroDB API: https://api.ainative.studio/v1/public/{project_id}/...

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
    Client for ZeroDB NoSQL table operations via AINative API.

    API Documentation: https://api.ainative.studio/docs
    """

    def __init__(self):
        """Initialize ZeroDB client with API credentials."""
        self.project_id = settings.ZERODB_PROJECT_ID
        self.api_key = settings.ZERODB_API_KEY
        self.base_url = f"https://api.ainative.studio/v1/public/{self.project_id}"
        logger.info(f"ZeroDB Client initialized for project: {self.project_id}")

    def _get_headers(self) -> Dict[str, str]:
        """Get API request headers."""
        return {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }

    async def create_table(
        self,
        table_name: str,
        description: str = "",
        schema: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Create a new table in ZeroDB.

        Args:
            table_name: Name of the table
            description: Table description
            schema: Optional schema definition

        Returns:
            Result dictionary with table info
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/database/tables",
                    headers=self._get_headers(),
                    json={
                        "name": table_name,
                        "description": description,
                        "schema": schema or {}
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()
                logger.info(f"Created table: {table_name}")
                return result
        except httpx.HTTPStatusError as e:
            logger.error(f"Error creating table {table_name}: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error creating table {table_name}: {e}")
            raise

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
        """
        results = []
        try:
            async with httpx.AsyncClient() as client:
                # Insert rows one at a time using row_data parameter
                for row in rows:
                    response = await client.post(
                        f"{self.base_url}/database/tables/{table_name}/rows",
                        headers=self._get_headers(),
                        json={"row_data": row},
                        timeout=30.0
                    )
                    response.raise_for_status()
                    results.append(response.json())

                logger.info(f"Inserted {len(rows)} rows into {table_name}")
                return {"success": True, "inserted": len(rows), "results": results}
        except httpx.HTTPStatusError as e:
            error_text = e.response.text
            logger.error(f"Error inserting rows into {table_name}: {error_text}")
            print(f"Error inserting rows: {error_text}")
            raise
        except Exception as e:
            logger.error(f"Error inserting rows into {table_name}: {e}")
            print(f"Error inserting rows: {e}")
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
        """
        try:
            async with httpx.AsyncClient() as client:
                # Build query parameters - ZeroDB API has max limit of 1000
                capped_limit = min(limit, 1000)
                params = {"limit": capped_limit, "offset": offset}

                response = await client.get(
                    f"{self.base_url}/database/tables/{table_name}/rows",
                    headers=self._get_headers(),
                    params=params,
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()

                # Handle different response formats
                if isinstance(result, list):
                    rows = result
                elif isinstance(result, dict):
                    # ZeroDB API returns data in 'data' array with row_data nested inside
                    raw_rows = result.get("data", result.get("rows", result.get("items", [])))
                    # Extract row_data from each item, preserving row_id for updates
                    rows = []
                    for item in raw_rows:
                        if isinstance(item, dict) and "row_data" in item:
                            row_data = item["row_data"].copy()
                            # Preserve row_id as _row_id for update/delete operations
                            row_data["_row_id"] = item.get("row_id")
                            rows.append(row_data)
                        else:
                            rows.append(item)
                else:
                    rows = []

                # Apply client-side filter if provided
                if filter:
                    filtered_rows = []
                    for row in rows:
                        match = True
                        for key, value in filter.items():
                            if row.get(key) != value:
                                match = False
                                break
                        if match:
                            filtered_rows.append(row)
                    rows = filtered_rows

                logger.debug(f"Queried {len(rows)} rows from {table_name}")
                return rows
        except httpx.HTTPStatusError as e:
            error_text = e.response.text
            logger.error(f"Error querying {table_name}: {error_text}")
            print(f"Error querying {table_name}: {error_text}")
            return []
        except Exception as e:
            logger.error(f"Error querying {table_name}: {e}")
            print(f"Error querying {table_name}: {e}")
            return []

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
        """
        try:
            # First find the row(s) to update
            rows = await self.query_rows(table_name=table_name, filter=filter)

            if not rows and not upsert:
                return {"matched": 0, "modified": 0}

            async with httpx.AsyncClient() as client:
                modified = 0
                update_data = update.get("$set", update)

                for row in rows:
                    # Use _row_id (ZeroDB's row identifier) for the API call
                    row_id = row.get("_row_id")
                    if row_id:
                        # Merge existing row data with updates
                        merged_data = {k: v for k, v in row.items() if k != "_row_id"}
                        merged_data.update(update_data)

                        # Update the row
                        response = await client.put(
                            f"{self.base_url}/database/tables/{table_name}/rows/{row_id}",
                            headers=self._get_headers(),
                            json={"row_data": merged_data},
                            timeout=30.0
                        )
                        if response.status_code == 200:
                            modified += 1

                logger.info(f"Updated {modified} rows in {table_name}")
                return {"matched": len(rows), "modified": modified}
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
        """
        try:
            # First find the row(s) to delete
            rows = await self.query_rows(table_name=table_name, filter=filter)

            if limit > 0:
                rows = rows[:limit]

            async with httpx.AsyncClient() as client:
                deleted = 0
                for row in rows:
                    # Use _row_id (ZeroDB's row identifier) for the API call
                    row_id = row.get("_row_id")
                    if row_id:
                        response = await client.delete(
                            f"{self.base_url}/database/tables/{table_name}/rows/{row_id}",
                            headers=self._get_headers(),
                            timeout=30.0
                        )
                        if response.status_code in [200, 204]:
                            deleted += 1

                logger.info(f"Deleted {deleted} rows from {table_name}")
                return {"deleted": deleted}
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
        # Fetch all rows since ZeroDB doesn't support server-side filtering
        # Then apply client-side filter to find the matching ID
        rows = await self.query_rows(
            table_name=table_name,
            filter={"id": id},
            limit=1000  # Fetch enough to find the match
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
        # Fetch all rows since ZeroDB doesn't support server-side filtering
        # Then apply client-side filter to find the matching field
        rows = await self.query_rows(
            table_name=table_name,
            filter={field: value},
            limit=1000  # Fetch enough to find the match
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
