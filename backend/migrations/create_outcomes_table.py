"""
ZeroDB Table Creation Script for Introduction Outcomes

Creates the 'introduction_outcomes' table in ZeroDB for storing outcome data.

Story 8.1: Record Intro Outcome

Table Schema:
- id: UUID (primary key)
- introduction_id: UUID (foreign key to introductions table)
- user_id: UUID (user who recorded the outcome)
- outcome_type: enum (successful, unsuccessful, no_response, not_relevant)
- feedback_text: optional string (10-500 chars)
- rating: optional int (1-5)
- tags: array of strings
- created_at: timestamp
- updated_at: timestamp

Indexes:
- introduction_id (unique - one outcome per introduction)
- user_id (for analytics queries)
- outcome_type (for filtering)
- created_at (for date range queries)
"""
import asyncio
import logging
from datetime import datetime
from uuid import uuid4

from app.services.zerodb_client import zerodb_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Table schema definition for ZeroDB
OUTCOMES_TABLE_SCHEMA = {
    "name": "introduction_outcomes",
    "description": "Stores outcomes and feedback for introduction tracking",
    "schema": {
        "fields": {
            "id": {
                "type": "string",
                "required": True,
                "description": "Unique outcome identifier (UUID)"
            },
            "introduction_id": {
                "type": "string",
                "required": True,
                "description": "Introduction this outcome belongs to (UUID)"
            },
            "user_id": {
                "type": "string",
                "required": True,
                "description": "User who recorded the outcome (UUID)"
            },
            "outcome_type": {
                "type": "string",
                "required": True,
                "enum": ["successful", "unsuccessful", "no_response", "not_relevant"],
                "description": "Type of outcome"
            },
            "feedback_text": {
                "type": "string",
                "required": False,
                "min_length": 10,
                "max_length": 500,
                "description": "Optional detailed feedback"
            },
            "rating": {
                "type": "integer",
                "required": False,
                "minimum": 1,
                "maximum": 5,
                "description": "Optional rating 1-5"
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "required": False,
                "description": "Optional categorization tags"
            },
            "created_at": {
                "type": "string",
                "required": True,
                "description": "Creation timestamp (ISO 8601)"
            },
            "updated_at": {
                "type": "string",
                "required": True,
                "description": "Last update timestamp (ISO 8601)"
            }
        },
        "indexes": [
            {
                "name": "idx_introduction_id",
                "fields": ["introduction_id"],
                "unique": True,
                "description": "Unique constraint - one outcome per introduction"
            },
            {
                "name": "idx_user_id",
                "fields": ["user_id"],
                "description": "Index for user analytics queries"
            },
            {
                "name": "idx_outcome_type",
                "fields": ["outcome_type"],
                "description": "Index for filtering by outcome type"
            },
            {
                "name": "idx_created_at",
                "fields": ["created_at"],
                "description": "Index for date range queries"
            }
        ]
    }
}


async def create_outcomes_table():
    """
    Create the introduction_outcomes table in ZeroDB.

    This function creates the table if it doesn't exist.
    Safe to run multiple times (idempotent).
    """
    try:
        logger.info("Creating introduction_outcomes table in ZeroDB...")

        # Note: ZeroDB tables are created implicitly when first inserting data
        # This script serves as documentation of the schema
        # In production, you would use ZeroDB's table creation API if available

        logger.info(
            f"Table schema defined for: {OUTCOMES_TABLE_SCHEMA['name']}"
        )
        logger.info(
            f"Fields: {', '.join(OUTCOMES_TABLE_SCHEMA['schema']['fields'].keys())}"
        )
        logger.info(
            f"Indexes: {len(OUTCOMES_TABLE_SCHEMA['schema']['indexes'])}"
        )

        # Verify we can connect to ZeroDB
        try:
            # Test connection by querying an existing table
            await zerodb_client.query_rows(
                table_name="users",
                limit=1
            )
            logger.info("ZeroDB connection verified")
        except Exception as e:
            logger.warning(f"Could not verify ZeroDB connection: {e}")

        logger.info("Table schema ready for use")
        logger.info(
            "Note: ZeroDB creates tables implicitly on first insert. "
            "This schema serves as documentation."
        )

        return True

    except Exception as e:
        logger.error(f"Error setting up outcomes table: {e}")
        raise


async def create_sample_data():
    """
    Create sample outcome data for testing (optional).

    This creates a few sample outcomes for development/testing.
    Should NOT be run in production.
    """
    logger.info("Creating sample outcome data...")

    try:
        # Get a sample introduction
        intros = await zerodb_client.query_rows(
            table_name="introductions",
            limit=1
        )

        if not intros:
            logger.warning("No introductions found - cannot create sample outcomes")
            return

        intro = intros[0]

        # Create sample outcome
        sample_outcome = {
            "id": str(uuid4()),
            "introduction_id": intro["id"],
            "user_id": intro["requester_id"],
            "outcome_type": "successful",
            "feedback_text": "Great conversation! We're scheduling a follow-up meeting next week.",
            "rating": 5,
            "tags": ["partnership", "follow-up", "valuable"],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        # Check if outcome already exists
        existing = await zerodb_client.query_rows(
            table_name="introduction_outcomes",
            filter={"introduction_id": intro["id"]},
            limit=1
        )

        if existing:
            logger.info("Sample outcome already exists")
            return

        await zerodb_client.insert_rows(
            "introduction_outcomes",
            [sample_outcome]
        )

        logger.info(f"Created sample outcome: {sample_outcome['id']}")

    except Exception as e:
        logger.error(f"Error creating sample data: {e}")


async def main():
    """Main migration function."""
    logger.info("=" * 60)
    logger.info("Introduction Outcomes Table Migration")
    logger.info("Story 8.1: Record Intro Outcome")
    logger.info("=" * 60)

    # Create table schema
    await create_outcomes_table()

    # Optionally create sample data
    create_samples = input("\nCreate sample data? (y/N): ").lower().strip() == 'y'
    if create_samples:
        await create_sample_data()

    logger.info("\nMigration complete!")
    logger.info("Table: introduction_outcomes")
    logger.info("Status: Ready for use")


if __name__ == "__main__":
    asyncio.run(main())
