"""
Audit Log Service - Story 10.1
Provides immutable audit logging with embedding references.
Uses ZeroDB NoSQL for storage.

This service provides:
1. Immutable audit log entries (cannot be updated or deleted)
2. Embedding references for traceability
3. Admin query capabilities for action tracing

Data Storage:
- Audit logs: ZeroDB NoSQL table 'action_audit_log'
"""
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from app.services.zerodb_client import zerodb_client

logger = logging.getLogger(__name__)


class ImmutableLogError(Exception):
    """Raised when attempting to modify an immutable log entry."""
    pass


class LogNotFoundError(Exception):
    """Raised when a log entry is not found."""
    pass


class AuditLogService:
    """
    Service for managing immutable audit logs.

    Features:
    - Immutable log entries (create only, no update/delete)
    - Embedding references for traceability
    - Query by agent, time range, action type, embedding

    Data Storage:
    - Audit logs: ZeroDB NoSQL table 'action_audit_log'
    """

    def __init__(self):
        """Initialize the audit log service."""
        self.zerodb_client = zerodb_client
        self.table_name = "action_audit_log"

    async def create_log_entry(
        self,
        agent_id: uuid.UUID,
        action_type: str,
        action_details: Dict[str, Any],
        user_id: uuid.UUID,
        source_embedding_id: Optional[str] = None,
        source_embedding_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a new immutable audit log entry.

        Args:
            agent_id: The agent that performed the action
            action_type: Type of action (e.g., "suggest", "act")
            action_details: Details of the action performed
            user_id: The user associated with the action
            source_embedding_id: Optional single embedding reference
            source_embedding_ids: Optional list of embedding references

        Returns:
            Dict with log_id of the created entry
        """
        log_id = str(uuid.uuid4())

        log_entry = {
            "id": log_id,
            "agent_id": str(agent_id),
            "user_id": str(user_id),
            "action_type": action_type,
            "action_details": action_details,
            "source_embedding_id": source_embedding_id,
            "source_embedding_ids": source_embedding_ids or [],
            "is_immutable": True,
            "created_at": datetime.utcnow().isoformat(),
        }

        try:
            await self.zerodb_client.insert_rows(self.table_name, [log_entry])
            logger.debug(
                f"Created audit log entry: id={log_id} agent={agent_id} "
                f"action={action_type}"
            )
        except Exception as e:
            logger.error(f"Failed to create audit log entry: {e}")
            raise

        return {"log_id": log_id}

    async def update_log_entry(
        self,
        log_id: str,
        updates: Dict[str, Any]
    ) -> None:
        """
        Attempt to update a log entry - always fails due to immutability.

        Args:
            log_id: The ID of the log entry
            updates: The updates to apply (ignored)

        Raises:
            LogNotFoundError: If the log entry doesn't exist
            ImmutableLogError: Always, if the entry exists
        """
        # Check if log exists
        log_entry = await self.zerodb_client.get_by_id(self.table_name, log_id)

        if not log_entry:
            raise LogNotFoundError(f"Log entry not found: {log_id}")

        # Log entries are immutable - always reject updates
        raise ImmutableLogError(
            f"Cannot update immutable audit log entry: {log_id}"
        )

    async def delete_log_entry(self, log_id: str) -> None:
        """
        Attempt to delete a log entry - always fails due to immutability.

        Args:
            log_id: The ID of the log entry

        Raises:
            LogNotFoundError: If the log entry doesn't exist
            ImmutableLogError: Always, if the entry exists
        """
        # Check if log exists
        log_entry = await self.zerodb_client.get_by_id(self.table_name, log_id)

        if not log_entry:
            raise LogNotFoundError(f"Log entry not found: {log_id}")

        # Log entries are immutable - always reject deletes
        raise ImmutableLogError(
            f"Cannot delete immutable audit log entry: {log_id}"
        )

    async def get_log_by_id(self, log_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a single log entry by ID.

        Args:
            log_id: The ID of the log entry

        Returns:
            The log entry dict, or None if not found
        """
        return await self.zerodb_client.get_by_id(self.table_name, log_id)

    async def get_logs_by_agent(
        self,
        agent_id: uuid.UUID,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get all log entries for an agent.

        Args:
            agent_id: The agent ID to filter by
            limit: Maximum number of entries to return

        Returns:
            List of log entries
        """
        return await self.zerodb_client.query_rows(
            table_name=self.table_name,
            filter={"agent_id": str(agent_id)},
            limit=limit,
            sort={"created_at": -1}
        )

    async def get_logs_by_embedding(
        self,
        embedding_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get log entries that reference a specific embedding.

        Args:
            embedding_id: The embedding ID to filter by

        Returns:
            List of log entries referencing the embedding
        """
        return await self.zerodb_client.query_rows(
            table_name=self.table_name,
            filter={"source_embedding_id": embedding_id},
            sort={"created_at": -1}
        )

    async def get_logs_by_time_range(
        self,
        start_time: datetime,
        end_time: datetime,
        agent_id: Optional[uuid.UUID] = None
    ) -> List[Dict[str, Any]]:
        """
        Get log entries within a time range.

        Args:
            start_time: Start of the time range
            end_time: End of the time range
            agent_id: Optional agent ID to filter by

        Returns:
            List of log entries within the time range
        """
        filter_query: Dict[str, Any] = {
            "created_at": {
                "$gte": start_time.isoformat(),
                "$lte": end_time.isoformat()
            }
        }

        if agent_id:
            filter_query["agent_id"] = str(agent_id)

        return await self.zerodb_client.query_rows(
            table_name=self.table_name,
            filter=filter_query,
            sort={"created_at": -1}
        )

    async def get_logs_by_action_type(
        self,
        action_type: str
    ) -> List[Dict[str, Any]]:
        """
        Get log entries by action type.

        Args:
            action_type: The action type to filter by

        Returns:
            List of log entries with the specified action type
        """
        return await self.zerodb_client.query_rows(
            table_name=self.table_name,
            filter={"action_type": action_type},
            sort={"created_at": -1}
        )


# Singleton instance
audit_log_service = AuditLogService()
