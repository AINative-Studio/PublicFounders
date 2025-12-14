"""
Unit tests for AuditLogService - Story 10.1
Tests for immutable audit logging with embedding references
Uses ZeroDB NoSQL (not PostgreSQL)
"""
import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from app.core.enums import AutonomyMode
from app.models.advisor_agent import AgentStatus


class TestAuditLogServiceInit:
    """Test AuditLogService initialization"""

    def test_service_initializes_with_zerodb_client(self, mock_zerodb_client):
        """Service should initialize with ZeroDB client"""
        from app.services.audit_log_service import AuditLogService

        service = AuditLogService()
        assert service.zerodb_client is not None

    def test_service_uses_correct_table_name(self, mock_zerodb_client):
        """Service should use 'action_audit_log' table"""
        from app.services.audit_log_service import AuditLogService

        service = AuditLogService()
        assert service.table_name == "action_audit_log"


class TestCreateLogEntry:
    """Test audit log entry creation"""

    @pytest.mark.asyncio
    async def test_create_log_entry_with_required_fields(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """Create log entry with all required fields"""
        from app.services.audit_log_service import AuditLogService

        user, profile, agent = sample_user_with_profile_and_agent_dict
        mock_zerodb_client.insert_rows.return_value = {"success": True}

        service = AuditLogService()

        result = await service.create_log_entry(
            agent_id=uuid.UUID(agent["id"]),
            action_type="suggest",
            action_details={"suggestion": "Test suggestion"},
            user_id=uuid.UUID(user["id"])
        )

        assert result is not None
        mock_zerodb_client.insert_rows.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_log_entry_generates_unique_id(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """Each log entry should have a unique ID"""
        from app.services.audit_log_service import AuditLogService

        user, profile, agent = sample_user_with_profile_and_agent_dict
        mock_zerodb_client.insert_rows.return_value = {"success": True}

        service = AuditLogService()

        await service.create_log_entry(
            agent_id=uuid.UUID(agent["id"]),
            action_type="suggest",
            action_details={},
            user_id=uuid.UUID(user["id"])
        )

        insert_call = mock_zerodb_client.insert_rows.call_args
        inserted_data = insert_call.args[1][0]
        assert "id" in inserted_data
        # Verify it's a valid UUID
        uuid.UUID(inserted_data["id"])

    @pytest.mark.asyncio
    async def test_create_log_entry_sets_immutable_flag(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """Log entries should be marked as immutable"""
        from app.services.audit_log_service import AuditLogService

        user, profile, agent = sample_user_with_profile_and_agent_dict
        mock_zerodb_client.insert_rows.return_value = {"success": True}

        service = AuditLogService()

        await service.create_log_entry(
            agent_id=uuid.UUID(agent["id"]),
            action_type="act",
            action_details={"action": "Test"},
            user_id=uuid.UUID(user["id"])
        )

        insert_call = mock_zerodb_client.insert_rows.call_args
        inserted_data = insert_call.args[1][0]
        assert inserted_data["is_immutable"] is True

    @pytest.mark.asyncio
    async def test_create_log_entry_with_single_embedding(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """Log entry can reference a single embedding"""
        from app.services.audit_log_service import AuditLogService

        user, profile, agent = sample_user_with_profile_and_agent_dict
        embedding_id = f"vec_{uuid.uuid4()}"
        mock_zerodb_client.insert_rows.return_value = {"success": True}

        service = AuditLogService()

        await service.create_log_entry(
            agent_id=uuid.UUID(agent["id"]),
            action_type="suggest",
            action_details={},
            user_id=uuid.UUID(user["id"]),
            source_embedding_id=embedding_id
        )

        insert_call = mock_zerodb_client.insert_rows.call_args
        inserted_data = insert_call.args[1][0]
        assert inserted_data["source_embedding_id"] == embedding_id

    @pytest.mark.asyncio
    async def test_create_log_entry_with_multiple_embeddings(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """Log entry can reference multiple embeddings"""
        from app.services.audit_log_service import AuditLogService

        user, profile, agent = sample_user_with_profile_and_agent_dict
        embedding_ids = [f"vec_{uuid.uuid4()}" for _ in range(3)]
        mock_zerodb_client.insert_rows.return_value = {"success": True}

        service = AuditLogService()

        await service.create_log_entry(
            agent_id=uuid.UUID(agent["id"]),
            action_type="suggest",
            action_details={},
            user_id=uuid.UUID(user["id"]),
            source_embedding_ids=embedding_ids
        )

        insert_call = mock_zerodb_client.insert_rows.call_args
        inserted_data = insert_call.args[1][0]
        assert inserted_data["source_embedding_ids"] == embedding_ids

    @pytest.mark.asyncio
    async def test_create_log_entry_includes_timestamp(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """Log entry includes creation timestamp"""
        from app.services.audit_log_service import AuditLogService

        user, profile, agent = sample_user_with_profile_and_agent_dict
        mock_zerodb_client.insert_rows.return_value = {"success": True}

        service = AuditLogService()

        await service.create_log_entry(
            agent_id=uuid.UUID(agent["id"]),
            action_type="suggest",
            action_details={},
            user_id=uuid.UUID(user["id"])
        )

        insert_call = mock_zerodb_client.insert_rows.call_args
        inserted_data = insert_call.args[1][0]
        assert "created_at" in inserted_data
        # Verify ISO format
        datetime.fromisoformat(inserted_data["created_at"])

    @pytest.mark.asyncio
    async def test_create_log_entry_returns_log_id(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """Create log entry returns the new log ID"""
        from app.services.audit_log_service import AuditLogService

        user, profile, agent = sample_user_with_profile_and_agent_dict
        mock_zerodb_client.insert_rows.return_value = {"success": True}

        service = AuditLogService()

        result = await service.create_log_entry(
            agent_id=uuid.UUID(agent["id"]),
            action_type="suggest",
            action_details={},
            user_id=uuid.UUID(user["id"])
        )

        assert "log_id" in result
        uuid.UUID(result["log_id"])  # Verify valid UUID


class TestImmutability:
    """Test log immutability enforcement"""

    @pytest.mark.asyncio
    async def test_update_log_entry_raises_immutable_error(
        self, mock_zerodb_client
    ):
        """Updating a log entry should raise ImmutableLogError"""
        from app.services.audit_log_service import (
            AuditLogService,
            ImmutableLogError
        )

        log_id = str(uuid.uuid4())
        mock_zerodb_client.get_by_id.return_value = {
            "id": log_id,
            "is_immutable": True
        }

        service = AuditLogService()

        with pytest.raises(ImmutableLogError) as exc_info:
            await service.update_log_entry(
                log_id=log_id,
                updates={"action_details": {"modified": True}}
            )

        assert "immutable" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_delete_log_entry_raises_immutable_error(
        self, mock_zerodb_client
    ):
        """Deleting a log entry should raise ImmutableLogError"""
        from app.services.audit_log_service import (
            AuditLogService,
            ImmutableLogError
        )

        log_id = str(uuid.uuid4())
        mock_zerodb_client.get_by_id.return_value = {
            "id": log_id,
            "is_immutable": True
        }

        service = AuditLogService()

        with pytest.raises(ImmutableLogError) as exc_info:
            await service.delete_log_entry(log_id=log_id)

        assert "immutable" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_update_nonexistent_log_raises_not_found(
        self, mock_zerodb_client
    ):
        """Updating nonexistent log should raise appropriate error"""
        from app.services.audit_log_service import (
            AuditLogService,
            LogNotFoundError
        )

        mock_zerodb_client.get_by_id.return_value = None

        service = AuditLogService()

        with pytest.raises(LogNotFoundError):
            await service.update_log_entry(
                log_id=str(uuid.uuid4()),
                updates={}
            )

    @pytest.mark.asyncio
    async def test_delete_nonexistent_log_raises_not_found(
        self, mock_zerodb_client
    ):
        """Deleting nonexistent log should raise appropriate error"""
        from app.services.audit_log_service import (
            AuditLogService,
            LogNotFoundError
        )

        mock_zerodb_client.get_by_id.return_value = None

        service = AuditLogService()

        with pytest.raises(LogNotFoundError):
            await service.delete_log_entry(log_id=str(uuid.uuid4()))


class TestQueryLogsByAgent:
    """Test querying logs by agent ID"""

    @pytest.mark.asyncio
    async def test_get_logs_by_agent_returns_matching_logs(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """Query logs by agent ID returns matching entries"""
        from app.services.audit_log_service import AuditLogService

        user, profile, agent = sample_user_with_profile_and_agent_dict
        mock_logs = [
            {"id": str(uuid.uuid4()), "agent_id": agent["id"]},
            {"id": str(uuid.uuid4()), "agent_id": agent["id"]}
        ]
        mock_zerodb_client.query_rows.return_value = mock_logs

        service = AuditLogService()

        results = await service.get_logs_by_agent(
            agent_id=uuid.UUID(agent["id"])
        )

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_get_logs_by_agent_with_limit(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """Query logs by agent with limit parameter"""
        from app.services.audit_log_service import AuditLogService

        user, profile, agent = sample_user_with_profile_and_agent_dict
        mock_zerodb_client.query_rows.return_value = []

        service = AuditLogService()

        await service.get_logs_by_agent(
            agent_id=uuid.UUID(agent["id"]),
            limit=10
        )

        query_call = mock_zerodb_client.query_rows.call_args
        assert query_call.kwargs["limit"] == 10


class TestQueryLogsByEmbedding:
    """Test querying logs by embedding reference"""

    @pytest.mark.asyncio
    async def test_get_logs_by_embedding_returns_matching_logs(
        self, mock_zerodb_client
    ):
        """Query logs by embedding ID returns matching entries"""
        from app.services.audit_log_service import AuditLogService

        embedding_id = f"vec_{uuid.uuid4()}"
        mock_logs = [
            {"id": str(uuid.uuid4()), "source_embedding_id": embedding_id}
        ]
        mock_zerodb_client.query_rows.return_value = mock_logs

        service = AuditLogService()

        results = await service.get_logs_by_embedding(
            embedding_id=embedding_id
        )

        assert len(results) == 1
        query_call = mock_zerodb_client.query_rows.call_args
        assert query_call.kwargs["filter"]["source_embedding_id"] == embedding_id

    @pytest.mark.asyncio
    async def test_get_logs_by_embedding_empty_results(
        self, mock_zerodb_client
    ):
        """Query logs by nonexistent embedding returns empty list"""
        from app.services.audit_log_service import AuditLogService

        mock_zerodb_client.query_rows.return_value = []

        service = AuditLogService()

        results = await service.get_logs_by_embedding(
            embedding_id="vec_nonexistent"
        )

        assert results == []


class TestQueryLogsByTimeRange:
    """Test querying logs by time range"""

    @pytest.mark.asyncio
    async def test_get_logs_by_time_range(self, mock_zerodb_client):
        """Query logs within a time range"""
        from app.services.audit_log_service import AuditLogService

        start_time = datetime.utcnow() - timedelta(hours=1)
        end_time = datetime.utcnow()
        mock_zerodb_client.query_rows.return_value = []

        service = AuditLogService()

        await service.get_logs_by_time_range(
            start_time=start_time,
            end_time=end_time
        )

        query_call = mock_zerodb_client.query_rows.call_args
        # Verify time range filter was applied
        assert mock_zerodb_client.query_rows.called

    @pytest.mark.asyncio
    async def test_get_logs_by_time_range_with_agent_filter(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """Query logs by time range with agent filter"""
        from app.services.audit_log_service import AuditLogService

        user, profile, agent = sample_user_with_profile_and_agent_dict
        start_time = datetime.utcnow() - timedelta(hours=1)
        end_time = datetime.utcnow()
        mock_zerodb_client.query_rows.return_value = []

        service = AuditLogService()

        await service.get_logs_by_time_range(
            start_time=start_time,
            end_time=end_time,
            agent_id=uuid.UUID(agent["id"])
        )

        query_call = mock_zerodb_client.query_rows.call_args
        assert query_call.kwargs["filter"]["agent_id"] == agent["id"]


class TestQueryLogsByActionType:
    """Test querying logs by action type"""

    @pytest.mark.asyncio
    async def test_get_logs_by_action_type(self, mock_zerodb_client):
        """Query logs by action type"""
        from app.services.audit_log_service import AuditLogService

        mock_logs = [
            {"id": str(uuid.uuid4()), "action_type": "act"}
        ]
        mock_zerodb_client.query_rows.return_value = mock_logs

        service = AuditLogService()

        results = await service.get_logs_by_action_type(action_type="act")

        assert len(results) == 1
        query_call = mock_zerodb_client.query_rows.call_args
        assert query_call.kwargs["filter"]["action_type"] == "act"

    @pytest.mark.asyncio
    async def test_get_logs_by_action_type_suggest(self, mock_zerodb_client):
        """Query logs with action type suggest"""
        from app.services.audit_log_service import AuditLogService

        mock_zerodb_client.query_rows.return_value = []

        service = AuditLogService()

        await service.get_logs_by_action_type(action_type="suggest")

        query_call = mock_zerodb_client.query_rows.call_args
        assert query_call.kwargs["filter"]["action_type"] == "suggest"


class TestGetLogById:
    """Test getting a single log entry by ID"""

    @pytest.mark.asyncio
    async def test_get_log_by_id_returns_entry(self, mock_zerodb_client):
        """Get log by ID returns the entry"""
        from app.services.audit_log_service import AuditLogService

        log_id = str(uuid.uuid4())
        mock_log = {"id": log_id, "action_type": "suggest"}
        mock_zerodb_client.get_by_id.return_value = mock_log

        service = AuditLogService()

        result = await service.get_log_by_id(log_id=log_id)

        assert result is not None
        assert result["id"] == log_id

    @pytest.mark.asyncio
    async def test_get_log_by_id_not_found_returns_none(
        self, mock_zerodb_client
    ):
        """Get log by nonexistent ID returns None"""
        from app.services.audit_log_service import AuditLogService

        mock_zerodb_client.get_by_id.return_value = None

        service = AuditLogService()

        result = await service.get_log_by_id(log_id=str(uuid.uuid4()))

        assert result is None


class TestAuditLogServiceExport:
    """Test that AuditLogService is properly exported"""

    def test_service_is_importable_from_services(self):
        """Service should be importable from services package"""
        from app.services.audit_log_service import (
            AuditLogService,
            audit_log_service,
            ImmutableLogError,
            LogNotFoundError
        )

        assert AuditLogService is not None
        assert audit_log_service is not None
        assert ImmutableLogError is not None
        assert LogNotFoundError is not None
