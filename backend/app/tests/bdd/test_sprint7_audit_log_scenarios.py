"""
BDD Scenarios for Sprint 7: Action Audit Log (Story 10.1)
Behavior-Driven Development tests for immutable audit logging
Uses ZeroDB NoSQL + Vectors (not PostgreSQL)

Story 10.1: Action Audit Log
As an admin, I want a full audit log, So that agent actions are traceable

TDD Acceptance Tests:
1. Logs are immutable
2. Logs reference source embeddings
"""
import pytest
import uuid
from datetime import datetime
from unittest.mock import patch, AsyncMock, MagicMock

from app.models.advisor_agent import AgentStatus, MemoryType
from app.core.enums import AutonomyMode


@pytest.mark.bdd
class TestStory10_1_LogsAreImmutable:
    """
    Story 10.1: Action Audit Log
    TDD Acceptance Test: Logs are immutable

    These tests verify that once an audit log entry is created,
    it cannot be modified or deleted.
    """

    @pytest.mark.asyncio
    async def test_scenario_audit_log_entries_cannot_be_updated(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """
        Scenario: Audit log entries cannot be updated
        Given an audit log entry has been created
        When someone attempts to update the entry
        Then the update is rejected
        And an ImmutableLogError is raised
        """
        from app.services.audit_log_service import (
            AuditLogService,
            ImmutableLogError
        )

        user, profile, agent = sample_user_with_profile_and_agent_dict
        log_id = str(uuid.uuid4())

        # Given: An audit log entry exists
        existing_log = {
            "id": log_id,
            "agent_id": agent["id"],
            "action_type": "suggest",
            "action_details": {"suggestion": "Connect with John"},
            "timestamp": datetime.utcnow().isoformat(),
            "is_immutable": True
        }
        mock_zerodb_client.get_by_id.return_value = existing_log

        service = AuditLogService()

        # When/Then: Attempting to update should raise ImmutableLogError
        with pytest.raises(ImmutableLogError) as exc_info:
            await service.update_log_entry(
                log_id=log_id,
                updates={"action_details": {"modified": "data"}}
            )

        assert "immutable" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_scenario_audit_log_entries_cannot_be_deleted(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """
        Scenario: Audit log entries cannot be deleted
        Given an audit log entry has been created
        When someone attempts to delete the entry
        Then the deletion is rejected
        And an ImmutableLogError is raised
        """
        from app.services.audit_log_service import (
            AuditLogService,
            ImmutableLogError
        )

        user, profile, agent = sample_user_with_profile_and_agent_dict
        log_id = str(uuid.uuid4())

        # Given: An audit log entry exists
        existing_log = {
            "id": log_id,
            "agent_id": agent["id"],
            "action_type": "act",
            "is_immutable": True
        }
        mock_zerodb_client.get_by_id.return_value = existing_log

        service = AuditLogService()

        # When/Then: Attempting to delete should raise ImmutableLogError
        with pytest.raises(ImmutableLogError) as exc_info:
            await service.delete_log_entry(log_id=log_id)

        assert "immutable" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_scenario_audit_log_created_with_immutable_flag(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """
        Scenario: New audit log entries are created with immutable flag
        Given I create a new audit log entry
        Then the entry is marked as immutable
        And the immutable flag cannot be changed
        """
        from app.services.audit_log_service import AuditLogService

        user, profile, agent = sample_user_with_profile_and_agent_dict

        mock_zerodb_client.insert_rows.return_value = {"success": True}

        service = AuditLogService()

        # When: Creating a new audit log entry
        log_entry = await service.create_log_entry(
            agent_id=uuid.UUID(agent["id"]),
            action_type="suggest",
            action_details={"suggestion": "Network with founders"},
            user_id=uuid.UUID(user["id"])
        )

        # Then: The entry should be marked as immutable
        insert_call = mock_zerodb_client.insert_rows.call_args
        inserted_data = insert_call.args[1][0]
        assert inserted_data["is_immutable"] is True

    @pytest.mark.asyncio
    async def test_scenario_audit_log_includes_creation_timestamp(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """
        Scenario: Audit log includes creation timestamp
        Given I create a new audit log entry
        Then the entry includes a creation timestamp
        And the timestamp is in ISO 8601 format
        """
        from app.services.audit_log_service import AuditLogService

        user, profile, agent = sample_user_with_profile_and_agent_dict
        mock_zerodb_client.insert_rows.return_value = {"success": True}

        service = AuditLogService()

        await service.create_log_entry(
            agent_id=uuid.UUID(agent["id"]),
            action_type="act",
            action_details={"action": "Sent email"},
            user_id=uuid.UUID(user["id"])
        )

        insert_call = mock_zerodb_client.insert_rows.call_args
        inserted_data = insert_call.args[1][0]

        assert "created_at" in inserted_data
        # Verify ISO 8601 format by parsing
        datetime.fromisoformat(inserted_data["created_at"])


@pytest.mark.bdd
class TestStory10_1_LogsReferenceSourceEmbeddings:
    """
    Story 10.1: Action Audit Log
    TDD Acceptance Test: Logs reference source embeddings

    These tests verify that audit log entries include references
    to the source embeddings that triggered the agent action.
    """

    @pytest.mark.asyncio
    async def test_scenario_audit_log_includes_embedding_reference(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """
        Scenario: Audit log includes embedding reference
        Given an agent action is triggered by a memory embedding
        When the action is logged
        Then the log entry includes the source embedding ID
        """
        from app.services.audit_log_service import AuditLogService

        user, profile, agent = sample_user_with_profile_and_agent_dict
        embedding_id = f"vec_{uuid.uuid4()}"

        mock_zerodb_client.insert_rows.return_value = {"success": True}

        service = AuditLogService()

        # When: Creating a log entry with embedding reference
        await service.create_log_entry(
            agent_id=uuid.UUID(agent["id"]),
            action_type="suggest",
            action_details={"suggestion": "Based on your connections"},
            user_id=uuid.UUID(user["id"]),
            source_embedding_id=embedding_id
        )

        # Then: The log entry includes the embedding ID
        insert_call = mock_zerodb_client.insert_rows.call_args
        inserted_data = insert_call.args[1][0]
        assert inserted_data["source_embedding_id"] == embedding_id

    @pytest.mark.asyncio
    async def test_scenario_audit_log_includes_multiple_embedding_references(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """
        Scenario: Audit log can reference multiple embeddings
        Given an agent action is triggered by multiple memory embeddings
        When the action is logged
        Then the log entry includes all source embedding IDs
        """
        from app.services.audit_log_service import AuditLogService

        user, profile, agent = sample_user_with_profile_and_agent_dict
        embedding_ids = [
            f"vec_{uuid.uuid4()}",
            f"vec_{uuid.uuid4()}",
            f"vec_{uuid.uuid4()}"
        ]

        mock_zerodb_client.insert_rows.return_value = {"success": True}

        service = AuditLogService()

        # When: Creating a log entry with multiple embedding references
        await service.create_log_entry(
            agent_id=uuid.UUID(agent["id"]),
            action_type="suggest",
            action_details={"suggestion": "Based on multiple memories"},
            user_id=uuid.UUID(user["id"]),
            source_embedding_ids=embedding_ids
        )

        # Then: The log entry includes all embedding IDs
        insert_call = mock_zerodb_client.insert_rows.call_args
        inserted_data = insert_call.args[1][0]
        assert inserted_data["source_embedding_ids"] == embedding_ids

    @pytest.mark.asyncio
    async def test_scenario_query_logs_by_embedding_id(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """
        Scenario: Query audit logs by embedding ID
        Given multiple audit log entries exist
        When I query logs by a specific embedding ID
        Then only logs referencing that embedding are returned
        """
        from app.services.audit_log_service import AuditLogService

        user, profile, agent = sample_user_with_profile_and_agent_dict
        target_embedding_id = f"vec_{uuid.uuid4()}"

        # Mock returning matching logs
        matching_logs = [
            {
                "id": str(uuid.uuid4()),
                "source_embedding_id": target_embedding_id,
                "action_type": "suggest"
            }
        ]
        mock_zerodb_client.query_rows.return_value = matching_logs

        service = AuditLogService()

        # When: Querying by embedding ID
        results = await service.get_logs_by_embedding(
            embedding_id=target_embedding_id
        )

        # Then: Query was made with correct filter
        query_call = mock_zerodb_client.query_rows.call_args
        assert query_call.kwargs["filter"]["source_embedding_id"] == target_embedding_id
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_scenario_embedding_reference_is_optional(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """
        Scenario: Embedding reference is optional for logs
        Given I create an audit log without an embedding reference
        Then the log is created successfully
        And the embedding fields are null/empty
        """
        from app.services.audit_log_service import AuditLogService

        user, profile, agent = sample_user_with_profile_and_agent_dict
        mock_zerodb_client.insert_rows.return_value = {"success": True}

        service = AuditLogService()

        # When: Creating a log without embedding reference
        await service.create_log_entry(
            agent_id=uuid.UUID(agent["id"]),
            action_type="suggest",
            action_details={"suggestion": "General suggestion"},
            user_id=uuid.UUID(user["id"])
            # No embedding_id provided
        )

        # Then: Log is created with null embedding fields
        insert_call = mock_zerodb_client.insert_rows.call_args
        inserted_data = insert_call.args[1][0]
        assert inserted_data.get("source_embedding_id") is None
        assert inserted_data.get("source_embedding_ids") == []


@pytest.mark.bdd
class TestAuditLogAdminQueries:
    """
    BDD scenarios for admin audit log queries
    Ensures admins can trace and investigate agent actions
    """

    @pytest.mark.asyncio
    async def test_scenario_admin_can_query_all_logs_for_agent(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """
        Scenario: Admin can query all logs for an agent
        Given multiple audit log entries exist for an agent
        When an admin queries logs by agent ID
        Then all logs for that agent are returned
        """
        from app.services.audit_log_service import AuditLogService

        user, profile, agent = sample_user_with_profile_and_agent_dict

        mock_logs = [
            {"id": str(uuid.uuid4()), "agent_id": agent["id"], "action_type": "suggest"},
            {"id": str(uuid.uuid4()), "agent_id": agent["id"], "action_type": "act"}
        ]
        mock_zerodb_client.query_rows.return_value = mock_logs

        service = AuditLogService()

        # When: Admin queries logs for agent
        results = await service.get_logs_by_agent(
            agent_id=uuid.UUID(agent["id"])
        )

        # Then: All logs for that agent are returned
        assert len(results) == 2
        query_call = mock_zerodb_client.query_rows.call_args
        assert query_call.kwargs["filter"]["agent_id"] == agent["id"]

    @pytest.mark.asyncio
    async def test_scenario_admin_can_query_logs_by_time_range(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """
        Scenario: Admin can query logs by time range
        Given audit log entries exist across different times
        When an admin queries logs within a specific time range
        Then only logs within that range are returned
        """
        from app.services.audit_log_service import AuditLogService
        from datetime import timedelta

        user, profile, agent = sample_user_with_profile_and_agent_dict
        start_time = datetime.utcnow() - timedelta(hours=1)
        end_time = datetime.utcnow()

        mock_zerodb_client.query_rows.return_value = []

        service = AuditLogService()

        # When: Admin queries logs within time range
        await service.get_logs_by_time_range(
            start_time=start_time,
            end_time=end_time
        )

        # Then: Query includes time range filter
        query_call = mock_zerodb_client.query_rows.call_args
        assert "created_at" in str(query_call)

    @pytest.mark.asyncio
    async def test_scenario_admin_can_query_logs_by_action_type(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """
        Scenario: Admin can query logs by action type
        Given audit log entries exist with different action types
        When an admin queries logs by action type
        Then only logs with that action type are returned
        """
        from app.services.audit_log_service import AuditLogService

        user, profile, agent = sample_user_with_profile_and_agent_dict

        mock_zerodb_client.query_rows.return_value = [
            {"id": str(uuid.uuid4()), "action_type": "act"}
        ]

        service = AuditLogService()

        # When: Admin queries logs by action type
        results = await service.get_logs_by_action_type(action_type="act")

        # Then: Query filters by action type
        query_call = mock_zerodb_client.query_rows.call_args
        assert query_call.kwargs["filter"]["action_type"] == "act"

    @pytest.mark.asyncio
    async def test_scenario_logs_include_full_traceability_data(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """
        Scenario: Logs include full traceability data
        Given I create an audit log entry
        Then the entry includes agent_id, user_id, timestamp, action details
        And can be used to trace the complete action history
        """
        from app.services.audit_log_service import AuditLogService

        user, profile, agent = sample_user_with_profile_and_agent_dict
        mock_zerodb_client.insert_rows.return_value = {"success": True}

        service = AuditLogService()

        await service.create_log_entry(
            agent_id=uuid.UUID(agent["id"]),
            action_type="suggest",
            action_details={
                "suggestion": "Connect with investor",
                "context": "Based on your funding goals"
            },
            user_id=uuid.UUID(user["id"]),
            source_embedding_id="vec_123"
        )

        insert_call = mock_zerodb_client.insert_rows.call_args
        inserted_data = insert_call.args[1][0]

        # Verify full traceability data
        assert "id" in inserted_data
        assert inserted_data["agent_id"] == agent["id"]
        assert inserted_data["user_id"] == user["id"]
        assert inserted_data["action_type"] == "suggest"
        assert "action_details" in inserted_data
        assert "created_at" in inserted_data
        assert inserted_data["is_immutable"] is True
        assert inserted_data["source_embedding_id"] == "vec_123"
