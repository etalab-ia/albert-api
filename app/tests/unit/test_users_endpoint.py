"""Unit tests for the users endpoint that don't require full application startup."""

from datetime import datetime
from http import HTTPMethod
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.endpoints.users import get_user_usage
from app.schemas.auth import User
from app.schemas.users import UserUsageResponse
from app.sql.models import Usage as UsageModel


class TestUsersEndpointUnit:
    """Unit tests for users endpoint functions."""

    @pytest.mark.asyncio
    async def test_get_user_usage_query_construction(self):
        """Test that the usage query is constructed correctly."""
        # Mock dependencies
        mock_session = AsyncMock(spec=AsyncSession)
        mock_user = User(id=123, name="test_user", role=1, created_at=1640995200, updated_at=1640995200)

        # Mock database results
        mock_usage = MagicMock(spec=UsageModel)
        mock_usage.id = 1
        mock_usage.datetime = datetime.now()
        mock_usage.user_id = 123
        mock_usage.endpoint = "/test"
        mock_usage.method = HTTPMethod.GET
        mock_usage.model = "test_model"
        mock_usage.duration = None
        mock_usage.time_to_first_token = None
        mock_usage.token_id = None
        mock_usage.request_model = None
        mock_usage.prompt_tokens = None
        mock_usage.completion_tokens = None
        mock_usage.total_tokens = None
        mock_usage.cost = None
        mock_usage.status = None
        mock_usage.kwh_min = None
        mock_usage.kwh_max = None
        mock_usage.kgco2eq_min = None
        mock_usage.kgco2eq_max = None

        # Mock session.execute to return our mock usage
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_usage]
        mock_session.execute.return_value = mock_result

        # Mock the count query
        mock_count_result = MagicMock()
        mock_count_result.scalars.return_value.all.return_value = [1]
        mock_session.execute.side_effect = [mock_result, mock_count_result]

        # Call the function
        response = await get_user_usage(limit=50, order_by="datetime", order_direction="desc", session=mock_session, current_user=mock_user)

        # Verify the response
        assert response.status_code == 200
        response_data = response.body.decode()
        assert "test_model" in response_data
        assert "123" in response_data  # user_id should be present

        # Verify session.execute was called twice (main query + count query)
        assert mock_session.execute.call_count == 2

    def test_user_usage_response_schema_validation(self):
        """Test that UserUsageResponse schema validation works."""
        # Test valid data
        valid_data = {"object": "list", "data": [], "total": 0, "has_more": False}

        response = UserUsageResponse(**valid_data)
        assert response.object == "list"
        assert response.data == []
        assert response.total == 0
        assert response.has_more is False

        # Test with actual usage data
        usage_data = {
            "id": 1,
            "datetime": int(datetime.now().timestamp()),
            "user_id": 123,
            "endpoint": "/test",
            "method": "GET",
            "model": "test_model",
        }

        response_with_data = UserUsageResponse(data=[usage_data], total=1, has_more=False)

        assert len(response_with_data.data) == 1
        assert response_with_data.total == 1
