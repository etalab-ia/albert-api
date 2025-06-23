from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from app.helpers._identityaccessmanager import IdentityAccessManager
from app.schemas.auth import Limit, LimitType, PermissionType
from app.utils.exceptions import (
    DeleteRoleWithUsersException,
    RoleAlreadyExistsException,
    RoleNotFoundException,
)


class TestIdentityAccessManagerRoles:
    """Role management tests for IdentityAccessManager."""

    @pytest.fixture
    def iam(self):
        """Return a fresh IdentityAccessManager instance for each test."""
        return IdentityAccessManager()

    @pytest.fixture
    def mock_session(self):
        """Return an AsyncSession mock."""
        return AsyncMock(spec=AsyncSession)

    # ----------------------------- Create ---------------------------------
    @pytest.mark.asyncio
    async def test_create_role_success(self, iam, mock_session):
        """Ensure a role is created with limits & permissions."""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 123
        mock_session.execute.return_value = mock_result

        name = "test_role"
        permissions = [PermissionType.CREATE_USER, PermissionType.READ_USER]
        limits = [Limit(model="gpt-4", type=LimitType.TPM, value=1000)]

        role_id = await iam.create_role(session=mock_session, name=name, permissions=permissions, limits=limits)

        assert role_id == 123
        # 1 role + 1 limit + 2 permissions = 4 execute calls
        assert mock_session.execute.call_count == 4
        assert mock_session.commit.call_count == 2

    @pytest.mark.asyncio
    async def test_create_role_already_exists(self, iam, mock_session):
        """Unique constraint violation should raise custom exception."""
        mock_session.execute.side_effect = IntegrityError(statement="INSERT INTO role", params={}, orig=Exception("unique constraint"))

        with pytest.raises(RoleAlreadyExistsException):
            await iam.create_role(session=mock_session, name="existing_role")

    @pytest.mark.asyncio
    async def test_create_role_with_empty_permissions_and_limits(self, iam, mock_session):
        """Creating a role without permissions/limits is allowed."""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 456
        mock_session.execute.return_value = mock_result

        role_id = await iam.create_role(session=mock_session, name="minimal_role", permissions=[], limits=[])

        assert role_id == 456
        assert mock_session.execute.call_count == 1  # Only role creation
        assert mock_session.commit.call_count == 2

    # ----------------------------- Delete --------------------------------
    @pytest.mark.asyncio
    async def test_delete_role_success(self, iam, mock_session):
        """Happy path deletion."""
        mock_role_result = MagicMock()
        mock_role_result.scalar_one.return_value = MagicMock()
        mock_session.execute.return_value = mock_role_result

        await iam.delete_role(session=mock_session, role_id=123)

        assert mock_session.execute.call_count == 2  # existence check + delete
        assert mock_session.commit.call_count == 1

    @pytest.mark.asyncio
    async def test_delete_role_not_found(self, iam, mock_session):
        """Deleting a non-existent role triggers RoleNotFoundException."""
        mock_result = MagicMock()
        mock_result.scalar_one.side_effect = NoResultFound()
        mock_session.execute.return_value = mock_result

        with pytest.raises(RoleNotFoundException):
            await iam.delete_role(session=mock_session, role_id=999)

    @pytest.mark.asyncio
    async def test_delete_role_with_users(self, iam, mock_session):
        """Deletion should fail when users reference the role (FK constraint)."""
        mock_role_result = MagicMock()
        mock_role_result.scalar_one.return_value = MagicMock()

        call_count = {"n": 0}

        def side_effect(*_args, **_kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return mock_role_result  # select role
            raise IntegrityError(statement="DELETE FROM role", params={}, orig=Exception("fk"))

        mock_session.execute.side_effect = side_effect

        with pytest.raises(DeleteRoleWithUsersException):
            await iam.delete_role(session=mock_session, role_id=123)

    # ----------------------------- Update --------------------------------
    @pytest.mark.asyncio
    async def test_update_role_success_all_fields(self, iam, mock_session):
        """Full update including name, limits & permissions."""
        mock_role_result = MagicMock()
        mock_role = MagicMock()
        mock_role.id = 123
        mock_role_result.scalar_one.return_value = mock_role
        mock_session.execute.return_value = mock_role_result

        new_name = "updated_role"
        new_permissions = [PermissionType.CREATE_TAG]
        new_limits = [Limit(model="gpt-3.5", type=LimitType.RPM, value=500)]

        await iam.update_role(session=mock_session, role_id=123, name=new_name, permissions=new_permissions, limits=new_limits)

        # At minimum: existence check + update branches
        assert mock_session.execute.call_count >= 5
        assert mock_session.commit.call_count == 1

    @pytest.mark.asyncio
    async def test_update_role_not_found(self, iam, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one.side_effect = NoResultFound()
        mock_session.execute.return_value = mock_result

        with pytest.raises(RoleNotFoundException):
            await iam.update_role(session=mock_session, role_id=999, name="new_name")

    @pytest.mark.asyncio
    async def test_update_role_partial_update(self, iam, mock_session):
        """Update only name leaves limits/permissions untouched."""
        mock_role_result = MagicMock()
        mock_role = MagicMock()
        mock_role.id = 123
        mock_role_result.scalar_one.return_value = mock_role
        mock_session.execute.return_value = mock_role_result

        await iam.update_role(session=mock_session, role_id=123, name="new_name_only")

        assert mock_session.commit.call_count == 1

    # ----------------------------- Get -----------------------------------
    @pytest.mark.asyncio
    async def test_get_roles_all_success(self, iam, mock_session):
        """Retrieve paginated roles list with user counts."""
        mock_ids_result = MagicMock()
        mock_ids_result.all.return_value = [(1,), (2,)]

        mock_details_result = MagicMock()
        mock_row1 = MagicMock()
        mock_row1._asdict.return_value = {"id": 1, "name": "role1", "created_at": 1000, "updated_at": 1100, "users": 2}
        mock_row2 = MagicMock()
        mock_row2._asdict.return_value = {"id": 2, "name": "role2", "created_at": 2000, "updated_at": 2100, "users": 0}
        mock_details_result.all.return_value = [mock_row1, mock_row2]

        mock_empty_result = MagicMock()
        mock_empty_result.all.return_value = []
        mock_empty_result.__iter__.return_value = iter([])

        call_count = {"n": 0}

        def side_effect(*_args, **_kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return mock_ids_result
            if call_count["n"] == 2:
                return mock_details_result
            return mock_empty_result  # for limits/permissions

        mock_session.execute.side_effect = side_effect

        roles = await iam.get_roles(session=mock_session, offset=0, limit=10, order_by="name", order_direction="asc")

        assert [r.id for r in roles] == [1, 2]
        assert roles[0].users == 2
        assert roles[1].users == 0

    @pytest.mark.asyncio
    async def test_get_role_by_id_success(self, iam, mock_session):
        mock_details_result = MagicMock()
        mock_row = MagicMock()
        mock_row._asdict.return_value = {"id": 123, "name": "specific_role", "created_at": 3000, "updated_at": 3100, "users": 1}
        mock_details_result.all.return_value = [mock_row]

        mock_limits_result = MagicMock()
        mock_limit_row = MagicMock(role_id=123, model="gpt-4", type=LimitType.TPM, value=1000)
        mock_limits_result.all.return_value = [mock_limit_row]
        mock_limits_result.__iter__.return_value = iter([mock_limit_row])

        mock_perms_result = MagicMock()
        mock_perm_row = MagicMock(role_id=123, permission=PermissionType.CREATE_USER)
        mock_perms_result.all.return_value = [mock_perm_row]
        mock_perms_result.__iter__.return_value = iter([mock_perm_row])

        call_count = {"n": 0}

        def side_effect(*_args, **_kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return mock_details_result
            if call_count["n"] == 2:
                return mock_limits_result
            return mock_perms_result

        mock_session.execute.side_effect = side_effect

        roles = await iam.get_roles(session=mock_session, role_id=123)
        role = roles[0]

        assert role.id == 123
        assert role.name == "specific_role"
        assert role.limits[0].model == "gpt-4"
        assert role.permissions == [PermissionType.CREATE_USER]

    @pytest.mark.asyncio
    async def test_get_role_by_id_not_found(self, iam, mock_session):
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        with pytest.raises(RoleNotFoundException):
            await iam.get_roles(session=mock_session, role_id=999)
