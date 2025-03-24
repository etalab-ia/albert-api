import json
import pytest
from unittest.mock import AsyncMock, patch

from app.clients._authenticationclient import AuthenticationClient


@pytest.mark.asyncio
async def test_check_api_key_with_no_name_in_cache():
    """Test that check_api_key handles users with missing name field in cache."""
    # Setup mock Redis
    mock_redis = AsyncMock()

    # Create a cached user without a name field
    user_id = AuthenticationClient.api_key_to_user_id("test-api-key")
    cached_user = {
        "id": user_id,
        "role": "USER",
        # No "name" field
    }

    # Configure Redis mock to return our cached user
    redis_key = f"TEST_{user_id}"
    mock_redis.get.return_value = json.dumps(cached_user)
    mock_redis.ttl.return_value = 3600  # TTL > 300 to return from cache

    # Create a mock for fetch_table
    mock_fetch_table = AsyncMock()
    mock_fetch_table.return_value = []  # This shouldn't be used in the test

    # Patch the ping method at the class level BEFORE initialization
    with patch.object(AuthenticationClient, "ping", return_value=True), patch.object(AuthenticationClient, "fetch_table", mock_fetch_table):
        # Create auth client with mocked Redis
        auth_client = AuthenticationClient(
            cache=mock_redis, table_id="TEST", doc_id="test-doc-id", server="https://example.com", api_key="test-grist-api-key"
        )

        user = await auth_client.check_api_key("test-api-key")

        # Verify Redis was called correctly
        mock_redis.get.assert_called_once_with(redis_key)

        # Verify we try to access Grist API even if the user is in cache (validation Error have been raised)
        mock_fetch_table.assert_called()  # Ensure fetch_table was called
