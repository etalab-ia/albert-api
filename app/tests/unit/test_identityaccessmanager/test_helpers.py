import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.helpers._identityaccessmanager import IdentityAccessManager
from app.utils.exceptions import TagNotFoundException


class TestIdentityAccessManagerHelpers:
    """Tests for the internal helper utilities of IdentityAccessManager."""

    @pytest.fixture
    def iam(self):
        return IdentityAccessManager()

    @pytest.fixture
    def mock_session(self):
        return AsyncMock(spec=AsyncSession)

    # -------------------- _check_if_tags_exist ----------------------------
    @pytest.mark.asyncio
    async def test_check_if_tags_exist_success(self, iam, mock_session):
        mock_result = MagicMock()
        mock_result.all.return_value = [MagicMock(id=1), MagicMock(id=2)]
        mock_session.execute.return_value = mock_result

        await iam._check_if_tags_exist(session=mock_session, tag_ids=[1, 2])

    @pytest.mark.asyncio
    async def test_check_if_tags_exist_missing(self, iam, mock_session):
        mock_result = MagicMock()
        mock_result.all.return_value = [MagicMock(id=1)]
        mock_session.execute.return_value = mock_result

        with pytest.raises(TagNotFoundException):
            await iam._check_if_tags_exist(session=mock_session, tag_ids=[1, 2])

    # -------------------- Token encode/decode ----------------------------
    def test_encode_token(self, iam):
        with patch("app.helpers._identityaccessmanager.jwt.encode", return_value="encoded_jwt"):
            token = iam._encode_token(user_id=1, token_id=2, expires_at=3)
        assert token == "sk-encoded_jwt"

    def test_decode_token(self, iam):
        mock_token = "sk-encoded"
        mock_claims = {"user_id": 1, "token_id": 2}
        with patch("app.helpers._identityaccessmanager.jwt.decode", return_value=mock_claims):
            claims = iam._decode_token(token=mock_token)
        assert claims == mock_claims

    def test_decode_token_invalid_prefix(self, iam):
        with pytest.raises(IndexError):
            iam._decode_token(token="invalid_prefix_token")
