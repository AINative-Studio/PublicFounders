"""
Integration tests for API health and basic endpoints.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestHealthEndpoints:
    """Test health check and basic API endpoints."""

    async def test_health_check(self, client: AsyncClient):
        """Test health check endpoint."""
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert "service" in data
        assert "version" in data
        assert "environment" in data

    async def test_root_endpoint(self, client: AsyncClient):
        """Test root endpoint."""
        response = await client.get("/")

        assert response.status_code == 200
        data = response.json()

        assert "message" in data
        assert "version" in data
        assert "docs" in data

    async def test_docs_available(self, client: AsyncClient):
        """Test API docs are accessible."""
        response = await client.get("/api/docs")

        assert response.status_code == 200

    async def test_openapi_schema(self, client: AsyncClient):
        """Test OpenAPI schema is available."""
        response = await client.get("/api/openapi.json")

        assert response.status_code == 200
        schema = response.json()

        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema
