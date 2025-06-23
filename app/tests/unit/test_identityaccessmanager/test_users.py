import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from app.helpers._identityaccessmanager import IdentityAccessManager
from app.schemas.auth import UserTag
from app.utils.exceptions import (
    RoleNotFoundException,
    TagNotFoundException,
    UserAlreadyExistsException,
    UserNotFoundException,
)


class TestIdentityAccessManagerUsers:
    """User management tests for IdentityAccessManager."""

    @pytest.fixture
    def iam(self):
        return IdentityAccessManager()

    @pytest.fixture
    def mock_session(self):
        return AsyncMock(spec=AsyncSession)

    # ----------------------------- Create ---------------------------------
    @pytest.mark.asyncio
    async def test_create_user_success_without_tags(self, iam, mock_session):
        mock_role_result = MagicMock()
        mock_role_result.scalar_one.return_value = MagicMock()
        mock_user_result = MagicMock()
        mock_user_result.scalar_one.return_value = 789

        mock_session.execute.side_effect = [mock_role_result, mock_user_result]

        user_id = await iam.create_user(
            session=mock_session,
            name="test_user",
            role_id=1,
            budget=100.0,
            expires_at=1640995200,
        )

        assert user_id == 789
        assert mock_session.execute.call_count == 2
        assert mock_session.commit.call_count == 1

    @pytest.mark.asyncio
    async def test_create_user_success_with_tags(self, iam, mock_session):
        mock_role_result = MagicMock()
        mock_role_result.scalar_one.return_value = MagicMock()
        mock_user_result = MagicMock()
        mock_user_result.scalar_one.return_value = 456
        mock_tags_result = MagicMock()
        mock_tags_result.all.return_value = [MagicMock(id=1), MagicMock(id=2)]

        mock_session.execute.side_effect = [mock_role_result, mock_user_result, mock_tags_result, MagicMock(), MagicMock()]

        tags = [UserTag(id=1, value="admin"), UserTag(id=2, value="developer")]

        user_id = await iam.create_user(session=mock_session, name="user_with_tags", role_id=1, tags=tags)

        assert user_id == 456
        assert mock_session.execute.call_count == 5  # role + user + tags check + 2 tag inserts
        assert mock_session.commit.call_count == 1

    @pytest.mark.asyncio
    async def test_create_user_role_not_found(self, iam, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one.side_effect = NoResultFound()
        mock_session.execute.return_value = mock_result

        with pytest.raises(RoleNotFoundException):
            await iam.create_user(session=mock_session, name="user", role_id=999)

    @pytest.mark.asyncio
    async def test_create_user_already_exists(self, iam, mock_session):
        mock_role_result = MagicMock()
        mock_role_result.scalar_one.return_value = MagicMock()
        mock_session.execute.side_effect = [mock_role_result, IntegrityError(statement="INSERT INTO user", params={}, orig=Exception())]

        with pytest.raises(UserAlreadyExistsException):
            await iam.create_user(session=mock_session, name="existing_user", role_id=1)

    @pytest.mark.asyncio
    async def test_create_user_tags_not_found(self, iam, mock_session):
        mock_role_result = MagicMock()
        mock_role_result.scalar_one.return_value = MagicMock()
        mock_user_result = MagicMock()
        mock_user_result.scalar_one.return_value = 123
        mock_tags_result = MagicMock()
        mock_tags_result.all.return_value = [MagicMock(id=1)]  # tag 2 missing

        mock_session.execute.side_effect = [mock_role_result, mock_user_result, mock_tags_result]

        tags = [UserTag(id=1, value="admin"), UserTag(id=2, value="missing")]

        with pytest.raises(TagNotFoundException) as exc:
            await iam.create_user(session=mock_session, name="user_with_invalid_tags", role_id=1, tags=tags)

        assert "{2}" in str(exc.value.detail)

    # ----------------------------- Delete --------------------------------
    @pytest.mark.asyncio
    async def test_delete_user_success(self, iam, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = MagicMock()
        mock_session.execute.return_value = mock_result

        await iam.delete_user(session=mock_session, user_id=123)

        assert mock_session.execute.call_count == 2
        assert mock_session.commit.call_count == 1

    @pytest.mark.asyncio
    async def test_delete_user_not_found(self, iam, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one.side_effect = NoResultFound()
        mock_session.execute.return_value = mock_result

        with pytest.raises(UserNotFoundException):
            await iam.delete_user(session=mock_session, user_id=999)

    # ----------------------------- Update --------------------------------
    @pytest.mark.asyncio
    async def test_update_user_success_all_fields(self, iam, mock_session):
        mock_user_result = MagicMock()
        mock_user = MagicMock(id=123, name="old_name", role_id=1, budget=50.0, expires_at=None, role="old_role")
        mock_user_result.all.return_value = [mock_user]
        mock_role_result = MagicMock()
        mock_role_result.scalar_one.return_value = MagicMock()
        mock_tags_result = MagicMock()
        mock_tags_result.all.return_value = [MagicMock(id=3), MagicMock(id=4)]

        # user select, role select, update, tags check, delete, insert1, insert2
        mock_session.execute.side_effect = [
            mock_user_result,  # select user
            mock_role_result,  # select role
            MagicMock(),  # update user row
            mock_tags_result,  # tag existence check
            MagicMock(),  # delete user tags
            MagicMock(),  # insert tag 1
            MagicMock(),  # insert tag 2
        ]

        # Make tag existence result iterable
        mock_tags_result.__iter__.return_value = iter(mock_tags_result.all.return_value)

        new_tags = [UserTag(id=3, value="manager"), UserTag(id=4, value="lead")]

        await iam.update_user(
            session=mock_session,
            user_id=123,
            name="new_name",
            role_id=2,
            tags=new_tags,
            budget=200.0,
            expires_at=1735689600,
        )

        assert mock_session.commit.call_count == 1

    @pytest.mark.asyncio
    async def test_update_user_not_found(self, iam, mock_session):
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        with pytest.raises(UserNotFoundException):
            await iam.update_user(session=mock_session, user_id=999, name="new_name")

    @pytest.mark.asyncio
    async def test_update_user_role_not_found(self, iam, mock_session):
        mock_user_result = MagicMock()
        mock_user = MagicMock(id=123, role_id=1)
        mock_user_result.all.return_value = [mock_user]
        mock_role_result = MagicMock()
        mock_role_result.scalar_one.side_effect = NoResultFound()

        mock_session.execute.side_effect = [mock_user_result, mock_role_result]

        with pytest.raises(RoleNotFoundException):
            await iam.update_user(session=mock_session, user_id=123, role_id=999)

    @pytest.mark.asyncio
    async def test_update_user_clear_tags(self, iam, mock_session):
        mock_user_result = MagicMock()
        mock_user = MagicMock(id=123, name="user", role_id=1)
        mock_user_result.all.return_value = [mock_user]

        empty_tags_result = MagicMock()
        empty_tags_result.all.return_value = []
        empty_tags_result.__iter__.return_value = iter([])

        # Sequence: user select, update row, tag check (empty), delete tags
        mock_session.execute.side_effect = [
            mock_user_result,
            MagicMock(),
            empty_tags_result,
            MagicMock(),
        ]

        await iam.update_user(session=mock_session, user_id=123, tags=[])

        assert mock_session.commit.call_count == 1

    # ----------------------------- Get -----------------------------------
    @pytest.mark.asyncio
    async def test_get_users_success_with_tags(self, iam, mock_session):
        mock_users_result = MagicMock()
        mock_user1 = MagicMock(id=1, name="user1", role=1, budget=100.0, expires_at=None, created_at=1000, updated_at=1100)
        mock_user1._mapping = {"id": 1, "name": "user1", "role": 1, "budget": 100.0, "expires_at": None, "created_at": 1000, "updated_at": 1100}
        mock_user2 = MagicMock(id=2, name="user2", role=2, budget=200.0, expires_at=1735689600, created_at=2000, updated_at=2100)
        mock_user2._mapping = {"id": 2, "name": "user2", "role": 2, "budget": 200.0, "expires_at": 1735689600, "created_at": 2000, "updated_at": 2100}
        mock_users_result.all.return_value = [mock_user1, mock_user2]

        mock_tags_result = MagicMock()
        mock_tag1 = MagicMock(user_id=1, tag_id=10, value="admin")
        mock_tag2 = MagicMock(user_id=2, tag_id=11, value="user")
        mock_tags_result.all.return_value = [mock_tag1, mock_tag2]

        # Ensure tags result is iterable
        mock_tags_result.__iter__.return_value = iter([mock_tag1, mock_tag2])
        mock_session.execute.side_effect = [mock_users_result, mock_tags_result]

        users = await iam.get_users(session=mock_session, offset=0, limit=10, order_by="name", order_direction="asc")

        assert len(users) == 2
        assert users[0].tags[0].value == "admin"
        assert users[1].tags[0].value == "user"

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, iam, mock_session):
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        with pytest.raises(UserNotFoundException):
            await iam.get_users(session=mock_session, user_id=999)

    # additional edge cases ------------------------------------------------
    @pytest.mark.asyncio
    async def test_create_user_budget_zero(self, iam, mock_session):
        """Budget can legitimately be 0.0 and should be accepted."""
        mock_role_result = MagicMock()
        mock_role_result.scalar_one.return_value = MagicMock()
        mock_user_result = MagicMock()
        mock_user_result.scalar_one.return_value = 111

        mock_session.execute.side_effect = [mock_role_result, mock_user_result]

        user_id = await iam.create_user(session=mock_session, name="free_user", role_id=1, budget=0.0)
        assert user_id == 111

    @pytest.mark.asyncio
    async def test_update_user_set_budget_none(self, iam, mock_session):
        """Setting budget to None clears previous value."""
        mock_user_result = MagicMock()
        mock_user = MagicMock(id=123, name="user", role_id=1, budget=10.0, expires_at=None)
        mock_user_result.all.return_value = [mock_user]

        mock_session.execute.side_effect = [mock_user_result, MagicMock()]

        await iam.update_user(session=mock_session, user_id=123, budget=None)
        assert mock_session.commit.call_count == 1
