import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from app.helpers._identityaccessmanager import IdentityAccessManager
from app.schemas.auth import UserTag
from app.utils.exceptions import DeleteRoleWithUsersException, RoleNotFoundException


class TestIdentityAccessManagerInterconnections:
    """Cross-domain scenarios that span roles, users, tags & tokens."""

    @pytest.fixture
    def iam(self):
        return IdentityAccessManager()

    @pytest.fixture
    def mock_session(self):
        return AsyncMock(spec=AsyncSession)

    # ---------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_create_user_with_nonexistent_role_and_tags(self, iam, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one.side_effect = NoResultFound()
        mock_session.execute.return_value = mock_result

        tags = [UserTag(id=1, value="admin")]
        with pytest.raises(RoleNotFoundException):
            await iam.create_user(session=mock_session, name="user", role_id=999, tags=tags)

    @pytest.mark.asyncio
    async def test_update_user_expired_with_new_tags(self, iam, mock_session):
        mock_user_result = MagicMock()
        mock_user = MagicMock(id=123, name="expired_user", role_id=1, expires_at=1640995200, role="basic")
        mock_user_result.all.return_value = [mock_user]
        mock_tags_result = MagicMock()
        mock_tags_result.all.return_value = [MagicMock(id=1)]

        # Sequence: user select, update row, tag check, delete, insert
        mock_tags_result.__iter__.return_value = iter(mock_tags_result.all.return_value)

        mock_session.execute.side_effect = [
            mock_user_result,
            MagicMock(),  # update row
            mock_tags_result,  # tag check
            MagicMock(),  # delete tags
            MagicMock(),  # insert tag
        ]

        new_tags = [UserTag(id=1, value="reactivated")]

        await iam.update_user(session=mock_session, user_id=123, tags=new_tags, expires_at=1735689600)
        assert mock_session.commit.call_count == 1

    @pytest.mark.asyncio
    async def test_delete_role_cascade_effect_on_user_tokens(self, iam, mock_session):
        mock_role_result = MagicMock()
        mock_role_result.scalar_one.return_value = MagicMock()

        def side_effect(*_args, **_kwargs):
            if side_effect.calls == 0:
                side_effect.calls += 1
                return mock_role_result  # select
            raise IntegrityError(statement="DELETE FROM role", params={}, orig=Exception("fk"))

        side_effect.calls = 0
        mock_session.execute.side_effect = side_effect

        with pytest.raises(DeleteRoleWithUsersException):
            await iam.delete_role(session=mock_session, role_id=1)

    @pytest.mark.asyncio
    async def test_token_creation_for_user_with_tags(self, iam, mock_session):
        mock_user_result = MagicMock()
        mock_user = MagicMock(id=123)
        mock_user_result.scalar_one.return_value = mock_user
        mock_token_result = MagicMock()
        mock_token_result.scalar_one.return_value = 789

        mock_session.execute.side_effect = [mock_user_result, mock_token_result, MagicMock()]

        with patch.object(iam, "_encode_token", return_value="sk-tagged_user_token"):
            token_id, token = await iam.create_token(session=mock_session, user_id=123, name="token_for_tagged_user")

        assert token_id == 789
        assert token == "sk-tagged_user_token"
