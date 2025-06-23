import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError

from app.helpers._identityaccessmanager import IdentityAccessManager
from app.utils.exceptions import TokenNotFoundException, UserNotFoundException


class TestIdentityAccessManagerTokens:
    """Token management tests for IdentityAccessManager."""

    @pytest.fixture
    def iam(self):
        return IdentityAccessManager()

    @pytest.fixture
    def mock_session(self):
        return AsyncMock(spec=AsyncSession)

    # ----------------------------- Create ---------------------------------
    @pytest.mark.asyncio
    async def test_create_token_success(self, iam, mock_session):
        mock_user_result = MagicMock()
        mock_user = MagicMock(id=123)
        mock_user_result.scalar_one.return_value = mock_user
        mock_token_result = MagicMock()
        mock_token_result.scalar_one.return_value = 456

        mock_session.execute.side_effect = [mock_user_result, mock_token_result, MagicMock()]

        with patch.object(iam, "_encode_token", return_value="sk-mock_token_12345678") as mock_encode:
            token_id, token = await iam.create_token(session=mock_session, user_id=123, name="test_token", expires_at=1735689600)

        assert token_id == 456
        assert token == "sk-mock_token_12345678"
        mock_encode.assert_called_once_with(user_id=123, token_id=456, expires_at=1735689600)
        assert mock_session.commit.call_count == 2

    @pytest.mark.asyncio
    async def test_create_token_user_not_found(self, iam, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one.side_effect = NoResultFound()
        mock_session.execute.return_value = mock_result

        with pytest.raises(UserNotFoundException):
            await iam.create_token(session=mock_session, user_id=999, name="token")

    @pytest.mark.asyncio
    async def test_create_token_without_expiration(self, iam, mock_session):
        mock_user_result = MagicMock()
        mock_user = MagicMock(id=123)
        mock_user_result.scalar_one.return_value = mock_user
        mock_token_result = MagicMock()
        mock_token_result.scalar_one.return_value = 789

        mock_session.execute.side_effect = [mock_user_result, mock_token_result, MagicMock()]

        with patch.object(iam, "_encode_token", return_value="sk-permanent_token") as mock_encode:
            token_id, token = await iam.create_token(session=mock_session, user_id=123, name="permanent_token")

        assert token_id == 789
        mock_encode.assert_called_once_with(user_id=123, token_id=789, expires_at=None)

    # New edge case: creating token for expired user -----------------------
    @pytest.mark.asyncio
    async def test_create_token_for_expired_user(self, iam, mock_session):
        """Token creation should not be blocked for a user whose account is expired (business rule may allow reactivation)."""
        mock_user_result = MagicMock()
        mock_user = MagicMock(id=321, expires_at=1640995200)  # date in the past
        mock_user_result.scalar_one.return_value = mock_user
        mock_token_result = MagicMock()
        mock_token_result.scalar_one.return_value = 654

        mock_session.execute.side_effect = [mock_user_result, mock_token_result, MagicMock()]

        with patch.object(iam, "_encode_token", return_value="sk-expired_user_token"):
            token_id, token = await iam.create_token(session=mock_session, user_id=321, name="token_expired_user")

        assert token_id == 654
        assert token.startswith("sk-")

    # ----------------------------- Delete --------------------------------
    @pytest.mark.asyncio
    async def test_delete_token_success(self, iam, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = MagicMock()
        mock_session.execute.return_value = mock_result

        await iam.delete_token(session=mock_session, user_id=123, token_id=456)

        assert mock_session.execute.call_count == 2
        assert mock_session.commit.call_count == 1

    @pytest.mark.asyncio
    async def test_delete_token_not_found(self, iam, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one.side_effect = NoResultFound()
        mock_session.execute.return_value = mock_result

        with pytest.raises(TokenNotFoundException):
            await iam.delete_token(session=mock_session, user_id=123, token_id=999)

    # ----------------------------- Get -----------------------------------
    @pytest.mark.asyncio
    async def test_get_tokens_success(self, iam, mock_session):
        mock_result = MagicMock()
        mock_token1 = MagicMock()
        mock_token1._mapping = {"id": 1, "name": "token1", "token": "sk-token1...12345678", "user": 123, "expires_at": None, "created_at": 1000}
        mock_token2 = MagicMock()
        mock_token2._mapping = {"id": 2, "name": "token2", "token": "sk-token2...87654321", "user": 123, "expires_at": 1735689600, "created_at": 2000}
        mock_result.all.return_value = [mock_token1, mock_token2]
        mock_session.execute.return_value = mock_result

        tokens = await iam.get_tokens(session=mock_session, user_id=123, offset=0, limit=10, order_by="name", order_direction="asc")

        assert len(tokens) == 2
        assert tokens[0].name == "token1"
        assert tokens[1].expires_at == 1735689600

    @pytest.mark.asyncio
    async def test_get_token_by_id_not_found(self, iam, mock_session):
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        with pytest.raises(TokenNotFoundException):
            await iam.get_tokens(session=mock_session, user_id=123, token_id=999)

    @pytest.mark.asyncio
    async def test_get_tokens_exclude_expired(self, iam, mock_session):
        mock_result = MagicMock()
        mock_token = MagicMock()
        mock_token._mapping = {"id": 1, "name": "active_token", "token": "sk-active...12345678", "user": 123, "expires_at": None, "created_at": 1000}
        mock_result.all.return_value = [mock_token]
        mock_session.execute.return_value = mock_result

        tokens = await iam.get_tokens(session=mock_session, user_id=123, exclude_expired=True)
        assert len(tokens) == 1

    # ----------------------------- Check ----------------------------------
    @pytest.mark.asyncio
    async def test_check_token_success(self, iam, mock_session):
        mock_token = "sk-valid_token_12345678"
        mock_claims = {"user_id": 123, "token_id": 456}
        mock_token_result = MagicMock()
        mock_token_obj = MagicMock()
        mock_token_obj._mapping = {"id": 456, "name": "valid", "token": "sk-valid...12345678", "user": 123, "expires_at": None, "created_at": 1000}
        mock_token_result.all.return_value = [mock_token_obj]
        mock_session.execute.return_value = mock_token_result

        with patch.object(iam, "_decode_token", return_value=mock_claims):
            user_id, token_id = await iam.check_token(session=mock_session, token=mock_token)

        assert (user_id, token_id) == (123, 456)

    @pytest.mark.asyncio
    async def test_check_token_invalid_jwt(self, iam, mock_session):
        with patch.object(iam, "_decode_token", side_effect=JWTError("invalid")):
            user_id, token_id = await iam.check_token(session=mock_session, token="invalid")
        assert user_id is None and token_id is None

    @pytest.mark.asyncio
    async def test_check_token_malformed(self, iam, mock_session):
        with patch.object(iam, "_decode_token", side_effect=IndexError("no prefix")):
            user_id, token_id = await iam.check_token(session=mock_session, token="no_prefix")
        assert (user_id, token_id) == (None, None)

    @pytest.mark.asyncio
    async def test_check_token_not_found_in_database(self, iam, mock_session):
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result
        mock_claims = {"user_id": 123, "token_id": 999}

        with patch.object(iam, "_decode_token", return_value=mock_claims):
            user_id, token_id = await iam.check_token(session=mock_session, token="sk-missing")
        assert (user_id, token_id) == (None, None)

    @pytest.mark.asyncio
    async def test_check_token_expired(self, iam, mock_session):
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result
        mock_claims = {"user_id": 123, "token_id": 456}

        with patch.object(iam, "_decode_token", return_value=mock_claims):
            user_id, token_id = await iam.check_token(session=mock_session, token="sk-expired")
        assert (user_id, token_id) == (None, None)
