from unittest.mock import MagicMock, patch, call

from app.clients._cacheclient import CacheClient, logger


class TestCacheClient:
    @patch("app.clients._cacheclient.SyncRedis")
    @patch("app.clients._cacheclient.AsyncRedis.__init__")
    @patch("app.clients._cacheclient.settings")
    def test_init_no_stored_version(self, mock_settings, mock_async_init, mock_sync_redis):
        """Test initialization when no version is stored in Redis."""
        # Setup
        mock_settings.app_version = "2.0.0"
        mock_redis_instance = MagicMock()
        mock_sync_redis.return_value = mock_redis_instance
        mock_redis_instance.get.return_value = None  # No stored version
        mock_async_init.return_value = None

        # Create connection kwargs as expected by Redis client
        connection_kwargs = {"host": "localhost", "port": 6379}
        connection_pool = MagicMock()
        connection_pool.connection_kwargs = connection_kwargs

        # Execute
        with patch.object(logger, "info") as mock_logger:
            client = CacheClient(connection_pool=connection_pool)

        # Assert
        mock_sync_redis.assert_called_once_with(**connection_kwargs)
        mock_redis_instance.ping.assert_called_once()
        mock_redis_instance.get.assert_called_once_with(CacheClient.VERSION_KEY)
        mock_redis_instance.flushall.assert_called_once()
        mock_redis_instance.set.assert_called_once_with(CacheClient.VERSION_KEY, "2.0.0")
        mock_redis_instance.close.assert_called_once()
        mock_async_init.assert_called_once_with(connection_pool=connection_pool)
        mock_logger.assert_has_calls(
            [call("Cache version mismatch. Stored: None, Current: 2.0.0. Flushing cache."), call("Cache flushed and version updated to 2.0.0")]
        )

    @patch("app.clients._cacheclient.SyncRedis")
    @patch("app.clients._cacheclient.AsyncRedis.__init__")
    @patch("app.clients._cacheclient.settings")
    def test_init_version_match(self, mock_settings, mock_async_init, mock_sync_redis):
        """Test initialization when version matches."""
        # Setup
        mock_settings.app_version = "2.0.0"
        mock_redis_instance = MagicMock()
        mock_sync_redis.return_value = mock_redis_instance
        mock_redis_instance.get.return_value = b"2.0.0"  # Same version
        mock_async_init.return_value = None

        connection_kwargs = {"host": "localhost", "port": 6379}
        connection_pool = MagicMock()
        connection_pool.connection_kwargs = connection_kwargs

        # Execute
        with patch.object(logger, "info") as mock_logger:
            client = CacheClient(connection_pool=connection_pool)

        # Assert
        mock_sync_redis.assert_called_once_with(**connection_kwargs)
        mock_redis_instance.ping.assert_called_once()
        mock_redis_instance.get.assert_called_once_with(CacheClient.VERSION_KEY)
        mock_redis_instance.flushall.assert_not_called()
        mock_redis_instance.set.assert_not_called()
        mock_redis_instance.close.assert_called_once()
        mock_async_init.assert_called_once_with(connection_pool=connection_pool)
        mock_logger.assert_called_once_with("Cache version match: 2.0.0. Using existing cache.")

    @patch("app.clients._cacheclient.SyncRedis")
    @patch("app.clients._cacheclient.AsyncRedis.__init__")
    @patch("app.clients._cacheclient.settings")
    def test_init_version_mismatch(self, mock_settings, mock_async_init, mock_sync_redis):
        """Test initialization when version doesn't match."""
        # Setup
        mock_settings.app_version = "2.0.0"
        mock_redis_instance = MagicMock()
        mock_sync_redis.return_value = mock_redis_instance
        mock_redis_instance.get.return_value = b"1.0.0"  # Different version
        mock_async_init.return_value = None

        connection_kwargs = {"host": "localhost", "port": 6379}
        connection_pool = MagicMock()
        connection_pool.connection_kwargs = connection_kwargs

        # Execute
        with patch.object(logger, "info") as mock_logger:
            client = CacheClient(connection_pool=connection_pool)

        # Assert
        mock_sync_redis.assert_called_once_with(**connection_kwargs)
        mock_redis_instance.ping.assert_called_once()
        mock_redis_instance.get.assert_called_once_with(CacheClient.VERSION_KEY)
        mock_redis_instance.flushall.assert_called_once()
        mock_redis_instance.set.assert_called_once_with(CacheClient.VERSION_KEY, "2.0.0")
        mock_redis_instance.close.assert_called_once()
        mock_async_init.assert_called_once_with(connection_pool=connection_pool)
        mock_logger.assert_has_calls(
            [call("Cache version mismatch. Stored: 1.0.0, Current: 2.0.0. Flushing cache."), call("Cache flushed and version updated to 2.0.0")]
        )
