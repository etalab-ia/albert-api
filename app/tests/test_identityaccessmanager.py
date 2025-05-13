import pytest
from app.helpers._identityaccessmanager import IdentityAccessManager
from app.schemas.auth import Limit, PermissionType


@pytest.mark.usefixtures("client", "async_db_session")
class TestIdentityAccessManager:
    @pytest.mark.asyncio
    async def test_update_role(self, async_db_session, client):
        """Test the update_role function of IdentityAccessManager."""
        async for session in async_db_session:
            iam = IdentityAccessManager()

            # Create a role to update
            role_name = "test-role"
            limits = [
                Limit(model="test-model", type="rpm", value=100),
                Limit(model="test-model", type="rpd", value=1000),
            ]
            permissions = [PermissionType.CREATE_ROLE, PermissionType.CREATE_USER]

            role_id = await iam.create_role(
                session=session,
                name=role_name,
                limits=limits,
                permissions=permissions,
            )

            # Update the role
            new_name = "updated-role"
            new_limits = [
                Limit(model="new-model", type="rpm", value=200),
            ]
            new_permissions = [PermissionType.DELETE_ROLE]

            await iam.update_role(
                session=session,
                role_id=role_id,
                name=new_name,
                limits=new_limits,
                permissions=new_permissions,
            )

            # Fetch the updated role
            roles = await iam.get_roles(session=session, role_id=role_id)
            updated_role = roles[0]

            assert updated_role.name == new_name
            assert len(updated_role.limits) == len(new_limits)
            assert updated_role.limits[0].model == "new-model"
            assert updated_role.limits[0].type == "rpm"
            assert updated_role.limits[0].value == 200
            assert len(updated_role.permissions) == len(new_permissions)
            assert updated_role.permissions[0] == PermissionType.DELETE_ROLE
