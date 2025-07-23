import pytest
import json
import base64
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.endpoints.proconnect import (
    oauth2_login,
    oauth2_callback,
    generate_redirect_url,
    logout,
)
from app.endpoints.proconnect.encryption import (
    get_fernet,
    encrypt_redirect_data,
)
from app.endpoints.proconnect.token import (
    get_jwks_keys,
    verify_jwt_signature,
    retrieve_user_info,
    create_user,
    perform_proconnect_logout,
)
from app.schemas.auth import OAuth2LogoutRequest, User
from app.sql.models import User as UserTable


class TestOAuth2Module:
    """Test suite for OAuth2 module functionality"""

    @pytest.fixture
    def mock_config(self):
        """Mock configuration for OAuth2"""
        config = MagicMock()
        config.dependencies.proconnect.client_id = "test_client_id"
        config.dependencies.proconnect.client_secret = "test_client_secret"
        config.dependencies.proconnect.server_metadata_url = "https://test-provider.com/.well-known/openid_configuration"
        config.dependencies.proconnect.scope = "openid,email,profile"
        config.dependencies.proconnect.redirect_uri = "https://test-app.com/callback"
        config.dependencies.proconnect.encryption_key = "test_key_for_encryption_purposes_32"
        config.dependencies.proconnect.allowed_domains = "test-domain.com,localhost"
        config.dependencies.proconnect.default_role = "Freemium"
        return config

    @pytest.fixture
    def mock_oauth2_client(self):
        """Mock OAuth2 client"""
        client = MagicMock()
        client.authorize_redirect = AsyncMock()
        client.authorize_access_token = AsyncMock()
        client.server_metadata = {
            "userinfo_endpoint": "https://test-provider.com/userinfo",
            "jwks_uri": "https://test-provider.com/jwks",
            "end_session_endpoint": "https://test-provider.com/logout",
        }
        client.load_server_metadata = AsyncMock(return_value=client.server_metadata)
        return client

    @pytest.fixture
    def mock_request(self):
        """Mock FastAPI request"""
        request = MagicMock(spec=Request)
        request.headers = {"referer": "https://test-domain.com/app"}
        request.query_params = {}
        return request

    @pytest.fixture
    def mock_session(self):
        """Mock database session"""
        session = MagicMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.get = AsyncMock()
        return session

    @pytest.fixture
    def mock_user(self):
        """Mock user object"""
        user = MagicMock(spec=User)
        user.id = 123
        user.name = "Test User"
        user.email = "test@example.com"
        user.sub = "test_sub_id"
        return user

    @pytest.fixture
    def mock_user_table(self):
        """Mock user table object"""
        user = MagicMock(spec=UserTable)
        user.id = 123
        user.name = "Test User"
        user.email = "test@example.com"
        user.sub = "test_sub_id"
        return user

    @patch("app.endpoints.proconnect.encryption.configuration")
    def test_get_fernet_with_default_key(self, mock_config):
        """Test Fernet initialization with default 'changeme' key"""
        mock_config.settings.encryption_key = "changeme"

        with patch("app.endpoints.proconnect.encryption.logger") as mock_logger:
            fernet = get_fernet()

            assert fernet is not None
            mock_logger.warning.assert_called_once()
            assert "Using default encryption key" in mock_logger.warning.call_args[0][0]

    @patch("app.endpoints.proconnect.encryption.configuration")
    def test_get_fernet_with_custom_key(self, mock_config):
        """Test Fernet initialization with custom key"""
        # Generate a proper 32-byte key
        key = base64.urlsafe_b64encode(b"0" * 32).decode()
        mock_config.settings.encryption_key = key

        fernet = get_fernet()
        assert fernet is not None

    @patch("app.endpoints.proconnect.encryption.configuration")
    def test_get_fernet_invalid_key(self, mock_config):
        """Test Fernet initialization with invalid key"""
        mock_config.dependencies.proconnect.encryption_key = "invalid_key"

        with pytest.raises(HTTPException) as exc_info:
            get_fernet()

        assert exc_info.value.status_code == 500
        assert "Encryption initialization failed" in exc_info.value.detail

    @patch("app.endpoints.proconnect.encryption.get_fernet")
    def test_encrypt_redirect_data_success(self, mock_get_fernet):
        """Test successful encryption of redirect data"""
        # Mock Fernet instance
        mock_fernet = MagicMock()
        mock_fernet.encrypt.return_value = b"encrypted_data"
        mock_get_fernet.return_value = mock_fernet

        result = encrypt_redirect_data("app_token", "token_id", "proconnect_token")

        assert result is not None
        assert isinstance(result, str)
        mock_fernet.encrypt.assert_called_once()

    @patch("app.endpoints.proconnect.encryption.get_fernet")
    def test_encrypt_redirect_data_failure(self, mock_get_fernet):
        """Test encryption failure"""
        mock_get_fernet.side_effect = Exception("Encryption error")

        with pytest.raises(HTTPException) as exc_info:
            encrypt_redirect_data("app_token", "token_id", "proconnect_token")

        assert exc_info.value.status_code == 500
        assert "Encryption failed" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("app.endpoints.proconnect.get_oauth2_client")
    @patch("app.endpoints.proconnect.configuration")
    async def test_oauth2_login_success(self, mock_config, mock_get_oauth2_client, mock_request, mock_oauth2_client):
        """Test successful OAuth2 login initiation"""
        mock_config.dependencies.proconnect.redirect_uri = "https://test-app.com/callback"
        mock_config.dependencies.proconnect.scope = "openid,email"

        mock_oauth2_client.authorize_redirect = AsyncMock(return_value=RedirectResponse(url="https://provider.com/auth"))
        mock_get_oauth2_client.return_value = mock_oauth2_client

        result = await oauth2_login(mock_request, mock_oauth2_client)

        assert isinstance(result, RedirectResponse)
        mock_oauth2_client.authorize_redirect.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.endpoints.proconnect.get_oauth2_client")
    async def test_oauth2_login_failure(self, mock_get_oauth2_client, mock_request, mock_oauth2_client):
        """Test OAuth2 login failure"""
        mock_oauth2_client.authorize_redirect.side_effect = Exception("OAuth2 error")
        mock_get_oauth2_client.return_value = mock_oauth2_client

        with pytest.raises(HTTPException) as exc_info:
            await oauth2_login(mock_request, mock_oauth2_client)

        assert exc_info.value.status_code == 400
        assert "OAuth2 login failed" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("app.endpoints.proconnect.get_oauth2_client")
    @patch("app.endpoints.proconnect.retrieve_user_info")
    @patch("app.endpoints.proconnect.global_context")
    @patch("app.endpoints.proconnect.create_user")
    @patch("app.endpoints.proconnect.generate_redirect_url")
    async def test_oauth2_callback_existing_user(
        self,
        mock_generate_redirect,
        mock_create_user,
        mock_global_context,
        mock_retrieve_user_info,
        mock_get_oauth2_client,
        mock_request,
        mock_session,
        mock_user_table,
        mock_oauth2_client,
    ):
        """Test OAuth2 callback with existing user"""
        # Setup mocks
        mock_token = {"access_token": "access_token", "id_token": "id_token"}
        mock_oauth2_client.authorize_access_token = AsyncMock(return_value=mock_token)
        mock_get_oauth2_client.return_value = mock_oauth2_client

        mock_user_info = {"sub": "test_sub", "email": "test@example.com", "given_name": "John", "usual_name": "Doe"}
        mock_retrieve_user_info.return_value = mock_user_info

        mock_iam = MagicMock()
        mock_iam.get_user = AsyncMock(return_value=mock_user_table)
        mock_iam.refresh_token = AsyncMock(return_value=("token_id", "app_token"))
        mock_global_context.identity_access_manager = mock_iam

        mock_generate_redirect.return_value = "https://test-domain.com?encrypted_token=xyz"
        mock_request.query_params = {"state": "encoded_state"}

        result = await oauth2_callback(mock_request, mock_session, mock_oauth2_client)

        assert isinstance(result, RedirectResponse)
        mock_iam.get_user.assert_called_once()
        mock_create_user.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.endpoints.proconnect.get_oauth2_client")
    @patch("app.endpoints.proconnect.retrieve_user_info")
    @patch("app.endpoints.proconnect.global_context")
    @patch("app.endpoints.proconnect.create_user")
    @patch("app.endpoints.proconnect.generate_redirect_url")
    async def test_oauth2_callback_new_user(
        self,
        mock_generate_redirect,
        mock_create_user,
        mock_global_context,
        mock_retrieve_user_info,
        mock_get_oauth2_client,
        mock_request,
        mock_session,
        mock_user_table,
        mock_oauth2_client,
    ):
        """Test OAuth2 callback with new user creation"""
        # Setup mocks
        mock_token = {"access_token": "access_token", "id_token": "id_token"}
        mock_oauth2_client.authorize_access_token = AsyncMock(return_value=mock_token)
        mock_get_oauth2_client.return_value = mock_oauth2_client

        mock_user_info = {"sub": "test_sub", "email": "test@example.com", "given_name": "John", "usual_name": "Doe"}
        mock_retrieve_user_info.return_value = mock_user_info

        mock_iam = MagicMock()
        mock_iam.get_user = AsyncMock(return_value=None)  # No existing user
        mock_iam.refresh_token = AsyncMock(return_value=("token_id", "app_token"))
        mock_global_context.identity_access_manager = mock_iam

        mock_create_user.return_value = mock_user_table
        mock_generate_redirect.return_value = "https://test-domain.com?encrypted_token=xyz"
        mock_request.query_params = {"state": "encoded_state"}

        result = await oauth2_callback(mock_request, mock_session, mock_oauth2_client)

        assert isinstance(result, RedirectResponse)
        mock_iam.get_user.assert_called_once()
        mock_create_user.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.endpoints.proconnect.get_oauth2_client")
    async def test_oauth2_callback_missing_sub(self, mock_get_oauth2_client, mock_request, mock_session, mock_oauth2_client):
        """Test OAuth2 callback with missing subject"""
        mock_token = {"access_token": "access_token"}
        mock_oauth2_client.authorize_access_token = AsyncMock(return_value=mock_token)
        mock_get_oauth2_client.return_value = mock_oauth2_client

        with patch("app.endpoints.proconnect.retrieve_user_info") as mock_retrieve:
            mock_retrieve.return_value = {"email": "test@example.com"}  # Missing 'sub'

            with pytest.raises(HTTPException) as exc_info:
                await oauth2_callback(mock_request, mock_session, mock_oauth2_client)

            assert exc_info.value.status_code == 400
            assert "Missing subject (sub)" in exc_info.value.detail

    @patch("app.endpoints.proconnect.configuration")
    def test_generate_redirect_url_valid_domain(self, mock_config):
        """Test redirect URL generation with valid domain"""
        mock_config.dependencies.proconnect.allowed_domains = "test-domain.com,localhost"

        mock_request = MagicMock()
        state_data = {"original_url": "https://test-domain.com/app"}
        state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()

        with patch("app.endpoints.proconnect.encrypt_redirect_data") as mock_encrypt:
            mock_encrypt.return_value = "encrypted_token"

            result = generate_redirect_url(mock_request, "app_token", "token_id", "proconnect_token", state)

            assert result == "https://test-domain.com?encrypted_token=encrypted_token"

    @patch("app.endpoints.proconnect.configuration")
    def test_generate_redirect_url_invalid_domain(self, mock_config):
        """Test redirect URL generation with invalid domain"""
        mock_config.dependencies.proconnect.allowed_domains = "allowed-domain.com"

        mock_request = MagicMock()
        state_data = {"original_url": "https://malicious-domain.com/app"}
        state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()

        with pytest.raises(HTTPException) as exc_info:
            generate_redirect_url(mock_request, "app_token", "token_id", "proconnect_token", state)

        assert exc_info.value.status_code == 400
        assert "Invalid domain" in exc_info.value.detail

    def test_generate_redirect_url_no_original_url(self):
        """Test redirect URL generation without original URL in state"""
        mock_request = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            generate_redirect_url(mock_request, "app_token", "token_id", "proconnect_token", None)

        assert exc_info.value.status_code == 400
        assert "No original URL found" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("app.endpoints.proconnect.token.configuration")
    @patch("httpx.AsyncClient")
    async def test_get_jwks_keys_success(self, mock_client_class, mock_config):
        """Test successful JWKS retrieval"""
        mock_config.dependencies.proconnect.server_metadata_url = "https://provider.com/.well-known"

        mock_client = MagicMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # Mock metadata response
        metadata_response = MagicMock()
        metadata_response.json.return_value = {"jwks_uri": "https://provider.com/jwks"}

        # Mock JWKS response
        jwks_response = MagicMock()
        jwks_response.json.return_value = {"keys": [{"kid": "key1", "kty": "RSA"}]}

        mock_client.get = AsyncMock(side_effect=[metadata_response, jwks_response])

        result = await get_jwks_keys()

        assert result == {"keys": [{"kid": "key1", "kty": "RSA"}]}
        assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_get_jwks_keys_failure(self, mock_client_class):
        """Test JWKS retrieval failure"""
        mock_client = MagicMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.get.side_effect = Exception("Network error")

        result = await get_jwks_keys()

        assert result is None

    @pytest.mark.asyncio
    @patch("app.endpoints.proconnect.token.get_jwks_keys")
    @patch("app.endpoints.proconnect.token.jwt")
    @patch("app.endpoints.proconnect.token.jwk")
    @patch("app.endpoints.proconnect.token.configuration")
    async def test_verify_jwt_signature_success(self, mock_config, mock_jwk, mock_jwt, mock_get_jwks):
        """Test successful JWT signature verification"""
        mock_config.dependencies.proconnect.client_id = "test_client"

        mock_get_jwks.return_value = {"keys": [{"kid": "key1", "kty": "RSA", "n": "test", "e": "AQAB"}]}

        mock_jwt.get_unverified_header.return_value = {"kid": "key1"}
        mock_jwt.decode.return_value = {"sub": "test_user", "aud": "test_client"}

        mock_key = MagicMock()
        mock_jwk.construct.return_value = mock_key

        result = await verify_jwt_signature("test.jwt.token")

        assert result == {"sub": "test_user", "aud": "test_client"}

    @pytest.mark.asyncio
    @patch("app.endpoints.proconnect.token.get_jwks_keys")
    @patch("app.endpoints.proconnect.token.jwt")
    async def test_verify_jwt_signature_fallback(self, mock_jwt, mock_get_jwks):
        """Test JWT verification fallback to unverified claims"""
        mock_get_jwks.return_value = None
        mock_jwt.get_unverified_claims.return_value = {"sub": "test_user"}

        result = await verify_jwt_signature("test.jwt.token")

        assert result == {"sub": "test_user"}
        mock_jwt.get_unverified_claims.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.endpoints.proconnect.get_oauth2_client")
    @patch("httpx.AsyncClient")
    @patch("app.endpoints.proconnect.token.verify_jwt_signature")
    async def test_retrieve_user_info_success(self, mock_verify_jwt, mock_client_class, mock_get_oauth2_client, mock_oauth2_client):
        """Test successful user info retrieval"""
        token = {"access_token": "access_token"}

        mock_oauth2_client.server_metadata = {"userinfo_endpoint": "https://provider.com/userinfo"}
        mock_get_oauth2_client.return_value = mock_oauth2_client

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.text = "jwt.response.here"
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response

        # Setup the async context manager
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_verify_jwt.return_value = {"sub": "test_user", "email": "test@example.com"}

        result = await retrieve_user_info(token, mock_oauth2_client)

        assert result == {"sub": "test_user", "email": "test@example.com"}

    @pytest.mark.asyncio
    @patch("app.endpoints.proconnect.get_oauth2_client")
    @patch("app.endpoints.proconnect.token.verify_jwt_signature")
    async def test_retrieve_user_info_fallback_to_id_token(self, mock_verify_jwt, mock_get_oauth2_client, mock_oauth2_client):
        """Test user info retrieval fallback to ID token"""
        token = {"access_token": "access_token", "id_token": "id_token"}

        mock_oauth2_client.server_metadata = {"userinfo_endpoint": "https://provider.com/userinfo"}
        mock_get_oauth2_client.return_value = mock_oauth2_client

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("Userinfo endpoint error")

            # Setup the async context manager
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_verify_jwt.return_value = {"sub": "test_user", "email": "test@example.com"}

            result = await retrieve_user_info(token, mock_oauth2_client)

            assert result == {"sub": "test_user", "email": "test@example.com"}

    @pytest.mark.asyncio
    @patch("app.endpoints.proconnect.token.configuration")
    @patch("app.endpoints.proconnect.token.IdentityAccessManager")
    async def test_create_user_success(self, mock_iam_class, mock_config, mock_session):
        """Test successful user creation"""
        mock_config.dependencies.proconnect.default_role = "Freemium"

        # Mock role query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 1  # Role ID
        mock_session.execute.return_value = mock_result

        # Mock user creation
        mock_iam = MagicMock()
        mock_iam.create_user = AsyncMock(return_value=123)  # User ID
        mock_iam_class.return_value = mock_iam

        # Mock user retrieval
        mock_user = MagicMock()
        mock_session.get.return_value = mock_user

        result = await create_user(mock_session, mock_iam, "John", "Doe", "john@example.com", "sub123")

        assert result == mock_user
        mock_iam.create_user.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.endpoints.proconnect.token.configuration")
    async def test_create_user_no_default_role(self, mock_config, mock_session):
        """Test user creation failure when default role doesn't exist"""
        mock_config.dependencies.proconnect.default_role = "NonExistentRole"

        # Mock role query returning None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        mock_iam = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            await create_user(mock_session, mock_iam, "John", "Doe", "john@example.com", "sub123")

        assert exc_info.value.status_code == 500
        assert "Default role for OAuth user not found" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("app.endpoints.proconnect.get_oauth2_client")
    @patch("app.endpoints.proconnect.global_context")
    @patch("app.endpoints.proconnect.request_context")
    async def test_logout_success(
        self, mock_request_context, mock_global_context, mock_get_oauth2_client, mock_session, mock_user, mock_oauth2_client
    ):
        """Test successful logout"""
        mock_request = MagicMock()
        mock_get_oauth2_client.return_value = mock_oauth2_client

        # Mock request context
        mock_context = MagicMock()
        mock_context.token_id = "token123"
        mock_request_context.get.return_value = mock_context

        # Mock IAM
        mock_iam = MagicMock()
        mock_iam.invalidate_token = AsyncMock()
        mock_global_context.identity_access_manager = mock_iam

        logout_request = OAuth2LogoutRequest(proconnect_token=None)

        result = await logout(mock_request, logout_request, mock_user, mock_session, mock_oauth2_client)

        assert result["status"] == "success"
        assert "Token expired successfully" in result["message"]
        mock_iam.invalidate_token.assert_called_once_with(session=mock_session, token_id="token123", user_id=mock_user.id)

    @pytest.mark.asyncio
    @patch("app.endpoints.proconnect.perform_proconnect_logout")
    @patch("app.endpoints.proconnect.get_oauth2_client")
    @patch("app.endpoints.proconnect.global_context")
    @patch("app.endpoints.proconnect.request_context")
    async def test_logout_with_proconnect_success(
        self, mock_request_context, mock_global_context, mock_get_oauth2_client, mock_perform_logout, mock_session, mock_user, mock_oauth2_client
    ):
        """Test successful logout with ProConnect"""
        mock_request = MagicMock()
        mock_get_oauth2_client.return_value = mock_oauth2_client

        # Mock request context
        mock_context = MagicMock()
        mock_context.token_id = "token123"
        mock_request_context.get.return_value = mock_context

        # Mock IAM
        mock_iam = MagicMock()
        mock_iam.invalidate_token = AsyncMock()
        mock_global_context.identity_access_manager = mock_iam

        # Mock ProConnect logout success
        mock_perform_logout.return_value = True

        logout_request = OAuth2LogoutRequest(proconnect_token="proconnect_token")

        result = await logout(mock_request, logout_request, mock_user, mock_session, mock_oauth2_client)

        assert result["status"] == "success"
        assert "Successfully logged out from ProConnect" in result["message"]
        mock_perform_logout.assert_called_once_with("proconnect_token", mock_oauth2_client)

    @pytest.mark.asyncio
    @patch("app.endpoints.proconnect.token.perform_proconnect_logout")
    @patch("app.endpoints.proconnect.get_oauth2_client")
    @patch("app.endpoints.proconnect.global_context")
    @patch("app.endpoints.proconnect.request_context")
    async def test_logout_with_proconnect_failure(
        self, mock_request_context, mock_global_context, mock_get_oauth2_client, mock_perform_logout, mock_session, mock_user, mock_oauth2_client
    ):
        """Test logout with ProConnect failure"""
        mock_request = MagicMock()
        mock_get_oauth2_client.return_value = mock_oauth2_client

        # Mock request context
        mock_context = MagicMock()
        mock_context.token_id = "token123"
        mock_request_context.get.return_value = mock_context

        # Mock IAM
        mock_iam = MagicMock()
        mock_iam.invalidate_token = AsyncMock()
        mock_global_context.identity_access_manager = mock_iam

        # Mock ProConnect logout failure
        mock_perform_logout.return_value = False

        logout_request = OAuth2LogoutRequest(proconnect_token="proconnect_token")

        result = await logout(mock_request, logout_request, mock_user, mock_session, mock_oauth2_client)

        assert result["status"] == "warning"
        assert "ProConnect logout may have failed" in result["message"]

    @pytest.mark.asyncio
    @patch("app.endpoints.proconnect.get_oauth2_client")
    @patch("app.endpoints.proconnect.token.configuration")
    @patch("httpx.AsyncClient")
    async def test_perform_proconnect_logout_success(self, mock_client_class, mock_config, mock_get_oauth2_client, mock_oauth2_client):
        """Test successful ProConnect logout"""
        mock_config.dependencies.proconnect.client_id = "test_client"
        mock_get_oauth2_client.return_value = mock_oauth2_client

        mock_oauth2_client.server_metadata = {"end_session_endpoint": "https://provider.com/logout"}

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.post.return_value = mock_response

        # Setup the async context manager
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await perform_proconnect_logout("proconnect_token", mock_oauth2_client)

        assert result is True
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.endpoints.proconnect.get_oauth2_client")
    async def test_perform_proconnect_logout_no_endpoint(self, mock_get_oauth2_client, mock_oauth2_client):
        """Test ProConnect logout with no end session endpoint"""
        mock_get_oauth2_client.return_value = mock_oauth2_client
        mock_oauth2_client.server_metadata = {}

        result = await perform_proconnect_logout("proconnect_token", mock_oauth2_client)

        assert result is False

    @pytest.mark.asyncio
    @patch("app.endpoints.proconnect.get_oauth2_client")
    @patch("httpx.AsyncClient")
    async def test_perform_proconnect_logout_failure(self, mock_client_class, mock_get_oauth2_client, mock_oauth2_client):
        """Test ProConnect logout failure"""
        mock_get_oauth2_client.return_value = mock_oauth2_client
        mock_oauth2_client.server_metadata = {"end_session_endpoint": "https://provider.com/logout"}

        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("Network error")

        # Setup the async context manager
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await perform_proconnect_logout("proconnect_token", mock_oauth2_client)

        assert result is False

    def test_generate_redirect_url_subdomain_allowed(self):
        """Test redirect URL generation with allowed subdomain"""
        with patch("app.endpoints.proconnect.configuration") as mock_config:
            mock_config.dependencies.proconnect.allowed_domains = "gouv.fr"

            mock_request = MagicMock()
            state_data = {"original_url": "https://api.gouv.fr/app"}
            state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()

            with patch("app.endpoints.proconnect.encrypt_redirect_data") as mock_encrypt:
                mock_encrypt.return_value = "encrypted_token"

                result = generate_redirect_url(mock_request, "app_token", "token_id", "proconnect_token", state)

                assert result == "https://api.gouv.fr?encrypted_token=encrypted_token"

    def test_generate_redirect_url_list_domains(self):
        """Test redirect URL generation with domain list configuration"""
        with patch("app.endpoints.proconnect.configuration") as mock_config:
            mock_config.dependencies.proconnect.allowed_domains = ["test-domain.com", "localhost"]

            mock_request = MagicMock()
            state_data = {"original_url": "https://test-domain.com/app"}
            state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()

            with patch("app.endpoints.proconnect.encrypt_redirect_data") as mock_encrypt:
                mock_encrypt.return_value = "encrypted_token"

                result = generate_redirect_url(mock_request, "app_token", "token_id", "proconnect_token", state)

                assert result == "https://test-domain.com?encrypted_token=encrypted_token"

    def test_generate_redirect_url_malformed_state(self):
        """Test redirect URL generation with malformed state"""
        with patch("app.endpoints.proconnect.configuration") as mock_config:
            mock_config.dependencies.proconnect.allowed_domains = "test-domain.com"

            mock_request = MagicMock()
            malformed_state = "invalid_base64_state"

            with pytest.raises(HTTPException) as exc_info:
                generate_redirect_url(mock_request, "app_token", "token_id", "proconnect_token", malformed_state)

            assert exc_info.value.status_code == 400
            assert "No original URL found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_create_user_with_minimal_info(self, mock_session):
        """Test user creation with minimal information"""
        with patch("app.endpoints.proconnect.configuration") as mock_config:
            mock_config.dependencies.proconnect.default_role = "Freemium"

            # Mock role query result
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = 1
            mock_session.execute.return_value = mock_result

            # Mock IAM
            mock_iam = MagicMock()
            mock_iam.create_user = AsyncMock(return_value=123)

            # Mock user retrieval
            mock_user = MagicMock()
            mock_session.get.return_value = mock_user

            result = await create_user(mock_session, mock_iam, "", "", "", "sub123")

            assert result == mock_user
            # Verify that a default display name was generated
            call_args = mock_iam.create_user.call_args
            assert "User-sub123" in call_args.kwargs["name"]
