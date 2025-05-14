import time
from datetime import datetime, timedelta
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient

from app.utils.variables import ENDPOINT__ROLES, ENDPOINT__USERS


@pytest.mark.usefixtures("client")
class TestAuth:
    def test_user_account_expiration_format(self, client: TestClient):
        # Create a test user with no expiration
        response = client.post_with_permissions(url=ENDPOINT__USERS, json={"name": f"test_user_{str(uuid4())}", "role": 1})
        assert response.status_code == 201, response.text
        user_no_expiration_id = response.json()["id"]

        # Get user with no expiration
        response = client.get_with_permissions(url=f"{ENDPOINT__USERS}/{user_no_expiration_id}")
        assert response.status_code == 200, response.text
        user_data = response.json()
        assert user_data["expires_at"] is None, response.text

        # Try to create user with expiration set to 5 minutes in the past (should fail)
        past_expiration = int((datetime.now() - timedelta(minutes=5)).timestamp())
        response = client.post_with_permissions(
            url=f"{ENDPOINT__USERS}",
            json={"name": f"test_user_{str(uuid4())}", "role": 1, "expires_at": past_expiration},
        )
        assert response.status_code == 422, response.text

        # Create user with expiration set to 5 minutes in the future
        future_expiration = int((time.time()) + 5 * 60)
        response = client.post_with_permissions(
            url=f"{ENDPOINT__USERS}",
            json={"name": f"test_user_{str(uuid4())}", "role": 1, "expires_at": future_expiration},
        )
        assert response.status_code == 201, response.text
        user_with_expiration_id = response.json()["id"]

        # Get user and check expiration
        response = client.get_with_permissions(url=f"{ENDPOINT__USERS}/{user_with_expiration_id}")
        assert response.status_code == 200, response.text
        user_data = response.json()
        assert user_data["expires_at"] == future_expiration, "User should have correct expiration time"

        # Update expiration to now
        future_current = int((datetime.now() + timedelta(seconds=10)).timestamp())
        response = client.patch_with_permissions(url=f"{ENDPOINT__USERS}/{user_with_expiration_id}", json={"expires_at": future_current})
        assert response.status_code == 204, response.text

        # Check updated expiration
        response = client.get_with_permissions(url=f"{ENDPOINT__USERS}/{user_with_expiration_id}")
        assert response.status_code == 200, response.text
        user_data = response.json()
        assert user_data["expires_at"] == future_current, "User should have updated expiration time"

        # Try to update expiration to past time (should fail)
        past_expiration = int((datetime.now() - timedelta(minutes=5)).timestamp())
        response = client.patch_with_permissions(url=f"{ENDPOINT__USERS}/{user_with_expiration_id}", json={"expires_at": past_expiration})
        assert response.status_code == 422, "Should reject update with past expiration time"

    def test_user_account_expiration_access(self, client: TestClient):
        # Create user with expiration set to 5 seconds in the future
        future_expiration = int((time.time()) + 2)  # + timedelta(seconds=5)).timestamp())
        response = client.post_with_permissions(
            url=f"{ENDPOINT__USERS}",
            json={"name": f"test_user_{str(uuid4())}", "role": 1, "expires_at": future_expiration},
        )
        assert response.status_code == 201, response.text
        user_id = response.json()["id"]

        # Create token for this user
        response = client.post_with_permissions(
            url="/tokens",
            json={"name": f"test_token_{str(uuid4())}", "user": user_id, "expires_at": future_expiration + 60},
        )
        assert response.status_code == 201, response.text
        token = response.json()["token"]

        # Test API access with token before expiration
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get(url="/health", headers=headers)
        assert response.status_code == 200, "User should have access before expiration"

        # Wait for user to expire
        time.sleep(2)

        # Test API access after expiration
        response = client.get(url="/health", headers=headers)
        assert response.status_code == 403, response.text

        # Verify user info endpoints still work with admin token
        response = client.get_with_permissions(url=f"{ENDPOINT__USERS}/{user_id}")
        assert response.status_code == 200, response.text

        # Check that /users/me and /roles/me endpoints return 200 for expired user
        response = client.get(url=f"{ENDPOINT__USERS}/me", headers=headers)
        assert response.status_code == 200, response.text

        response = client.get(url=f"{ENDPOINT__ROLES}/me", headers=headers)
        assert response.status_code == 200, response.text
