"""
ZeroDB Client - REST API Implementation
Handles all NoSQL table CRUD operations for PublicFounders.
Uses direct HTTP requests following the official ZeroDB Developer Guide.
API Base: https://api.ainative.studio/v1/public/{project_id}/database/...
"""
import logging
from typing import Any, Dict, List, Optional
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

# Import MCP tools wrapper
try:
    from ainative_mcp_wrapper import ZeroDBMCPClient
    HAS_MCP = True
except ImportError:
    HAS_MCP = False
    logger.warning("MCP wrapper not available, using fallback implementation")


class ZeroDBClient:
    """
    Client for ZeroDB NoSQL table operations using direct HTTP requests.
    API Base: https://api.ainative.studio/v1/public/{project_id}/database/...
    """

    def __init__(self):
        """Initialize ZeroDB client with API credentials."""
        self.project_id = settings.ZERODB_PROJECT_ID
        self.api_key = settings.ZERODB_API_KEY
        self.base_url = "https://api.ainative.studio/v1/public"

        # Create httpx client with timeout and default headers
        self.client = httpx.Client(
            timeout=30.0,
            headers={
                "X-API-Key": self.api_key,
                "Content-Type": "application/json"
            }
        )

        logger.info(f"ZeroDB Client initialized for project: {self.project_id}")

    async def insert_rows(
        self,
        table_name: str,
        rows: List[Dict[str, Any]],
        return_ids: bool = True
    ) -> Dict[str, Any]:
        """
        Insert rows into ZeroDB NoSQL table.
        POST /v1/public/{project_id}/database/tables/{table_name}/rows
        """
        try:
            results = []
            for row in rows:
                url = f"{self.base_url}/{self.project_id}/database/tables/{table_name}/rows"
                response = self.client.post(url, json={"row_data": row})
                response.raise_for_status()
                results.append(response.json())

            logger.info(f"Inserted {len(rows)} rows into {table_name}")
            return {"status": "success", "inserted": len(rows), "rows": results}
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
        GET /v1/public/{project_id}/database/tables/{table_name}/rows
        """
        try:
            url = f"{self.base_url}/{self.project_id}/database/tables/{table_name}/rows"
            params = {"skip": offset, "limit": limit}

            response = self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            # Handle response format
            rows = data if isinstance(data, list) else data.get("rows", data.get("data", []))

            # Apply client-side filtering
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
        except Exception as e:
            logger.error(f"Error querying rows from {table_name}: {e}")
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
        PUT /v1/public/{project_id}/database/tables/{table_name}/rows/{row_id}
        """
        try:
            # First, find the rows to update
            rows_to_update = await self.query_rows(table_name=table_name, filter=filter)

            updated_count = 0
            for row in rows_to_update:
                row_id = row.get("id")
                if row_id:
                    # Extract updates from $set operation
                    update_data = update.get("$set", update)

                    url = f"{self.base_url}/{self.project_id}/database/tables/{table_name}/rows/{row_id}"
                    response = self.client.put(url, json={"data": update_data})
                    response.raise_for_status()
                    updated_count += 1

            logger.info(f"Updated {updated_count} rows in {table_name}")
            return {"status": "success", "updated": updated_count}
        except Exception as e:
            logger.error(f"Error updating rows in {table_name}: {e}")
            raise

    async def delete_rows(
        self,
        table_name: str,
        filter: Dict[str, Any],
        limit: int = 0
    ) -> Dict[str, Any]:
        """
        Delete rows from ZeroDB NoSQL table.
        DELETE /v1/public/{project_id}/database/tables/{table_name}/rows/{row_id}
        """
        try:
            # First, find the rows to delete
            rows_to_delete = await self.query_rows(table_name=table_name, filter=filter)

            if limit > 0:
                rows_to_delete = rows_to_delete[:limit]

            deleted_count = 0
            for row in rows_to_delete:
                row_id = row.get("id")
                if row_id:
                    url = f"{self.base_url}/{self.project_id}/database/tables/{table_name}/rows/{row_id}"
                    response = self.client.delete(url)
                    response.raise_for_status()
                    deleted_count += 1

            logger.info(f"Deleted {deleted_count} rows from {table_name}")
            return {"status": "success", "deleted": deleted_count}
        except Exception as e:
            logger.error(f"Error deleting rows from {table_name}: {e}")
            raise

    async def get_by_id(
        self,
        table_name: str,
        id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a single row by ID.
        GET /v1/public/{project_id}/database/tables/{table_name}/rows/{row_id}
        """
        try:
            url = f"{self.base_url}/{self.project_id}/database/tables/{table_name}/rows/{id}"
            response = self.client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.debug(f"Row {id} not found in {table_name}")
                return None
            raise
        except Exception as e:
            logger.debug(f"Error getting row {id} from {table_name}: {e}")
            return None

    async def get_by_field(
        self,
        table_name: str,
        field: str,
        value: Any
    ) -> Optional[Dict[str, Any]]:
        """
        Get a single row by any field value.
        """
        rows = await self.query_rows(
            table_name=table_name,
            filter={field: value},
            limit=1
        )
        return rows[0] if rows else None

    async def create_table(
        self,
        table_name: str,
        schema: Dict[str, Any],
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new NoSQL table in ZeroDB.
        POST /v1/public/{project_id}/database/tables
        """
        try:
            url = f"{self.base_url}/{self.project_id}/database/tables"
            response = self.client.post(url, json={
                "name": table_name,
                "schema": schema,
                "description": description
            })
            response.raise_for_status()
            logger.info(f"Created table: {table_name}")
            return response.json()
        except Exception as e:
            logger.error(f"Error creating table {table_name}: {e}")
            raise

    async def list_tables(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        List all tables in the project.
        GET /v1/public/{project_id}/database/tables
        """
        try:
            url = f"{self.base_url}/{self.project_id}/database/tables"
            response = self.client.get(url)
            response.raise_for_status()
            data = response.json()

            # Handle pagination response format
            tables = data.get("data", []) if isinstance(data, dict) else data
            logger.debug(f"Listed {len(tables)} tables")
            return tables[:limit]
        except Exception as e:
            logger.error(f"Error listing tables: {e}")
            raise


# Global singleton instance
zerodb_client = ZeroDBClient()
