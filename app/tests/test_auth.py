from datetime import datetime, timedelta
import time
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from redis import Redis

from app.helpers import UsageTokenizer
from app.schemas.auth import LimitType
from app.utils.settings import settings
from app.utils.variables import ENDPOINT__CHAT_COMPLETIONS, ENDPOINT__MODELS, ENDPOINT__ROLES, ENDPOINT__TOKENS, ENDPOINT__USERS


@pytest.fixture(scope="module")
def clean_redis() -> None:
    """Delete all redis keys for rate limiting conflicts."""
    r = Redis(**settings.databases.redis.args)
    assert r.ping(), "Redis database is not reachable."

    for key in r.keys():
        r.delete(key)


@pytest.fixture(scope="module")
def tokenizer():
    tokenizer = UsageTokenizer(settings.usages.tokenizer)
    tokenizer = tokenizer.tokenizer

    yield tokenizer


@pytest.mark.usefixtures("client", "clean_redis", "tokenizer")
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
        # Create user with expiration set to 2 seconds in the future
        future_expiration = int((time.time()) + 2)
        response = client.post_with_permissions(
            url=f"{ENDPOINT__USERS}",
            json={"name": f"test_user_{str(uuid4())}", "role": 1, "expires_at": future_expiration},
        )
        assert response.status_code == 201, response.text
        user_id = response.json()["id"]

        # Create token for this user
        response = client.post_with_permissions(
            url=f"{ENDPOINT__TOKENS}",
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

    def test_token_rate_limits(self, client: TestClient, tokenizer):
        tokenizer = tokenizer

        # Get a text-generation model
        response = client.get(url=f"/v1{ENDPOINT__MODELS}")
        assert response.status_code == 200, response.text
        model = [model["id"] for model in response.json()["data"] if model["type"] == "text-generation"][0]

        # Create a role with token limits
        response = client.post_with_permissions(
            url=ENDPOINT__ROLES,
            json={
                "name": f"test_role_{str(uuid4())}",
                "limits": [
                    {"model": model, "type": LimitType.RPM.value, "value": None},
                    {"model": model, "type": LimitType.RPD.value, "value": None},
                    {"model": model, "type": LimitType.TPM.value, "value": None},
                    {"model": model, "type": LimitType.TPD.value, "value": 10},  # 10 tokens per days
                ],
            },
        )
        assert response.status_code == 201, response.text
        role_id = response.json()["id"]

        # Create a user for this role
        response = client.post_with_permissions(
            url=ENDPOINT__USERS,
            json={"name": f"test_user_{str(uuid4())}", "role": role_id},
        )
        assert response.status_code == 201, response.text
        user_id = response.json()["id"]

        # Create a token for this user
        response = client.post_with_permissions(
            url=ENDPOINT__TOKENS,
            json={"name": f"test_token_{str(uuid4())}", "user": user_id, "expires_at": int((time.time()) + 60 * 10)},
        )
        assert response.status_code == 201, response.text
        token = response.json()["token"]

        # Test token limits
        def get_content_len(n: int) -> str:
            nonlocal tokenizer
            content = ("test " * n).strip()
            assert len(tokenizer.encode(content)) == n, "Cost should be equal to the number of tokens, please check the tokenizer for this test."  # fmt: off

            return content

        content_len_5 = get_content_len(5)
        content_len_10 = get_content_len(10)
        content_len_40 = get_content_len(40)

        headers = {"Authorization": f"Bearer {token}"}
        response = client.post(
            url=f"/v1{ENDPOINT__CHAT_COMPLETIONS}",
            headers=headers,
            json={"model": model, "messages": [{"role": "user", "content": content_len_5}], "max_tokens": 1},
        )
        assert response.status_code == 200, response.text

        response = client.post(
            url=f"/v1{ENDPOINT__CHAT_COMPLETIONS}",
            headers=headers,
            json={"model": model, "messages": [{"role": "user", "content": content_len_10}], "max_tokens": 1},
        )

        assert response.status_code == 429, response.text

        # Increase the limit
        response = client.patch_with_permissions(
            url=f"{ENDPOINT__ROLES}/{role_id}",
            json={
                "name": f"test_role_{str(uuid4())}",
                "limits": [
                    {"model": model, "type": "rpm", "value": None},
                    {"model": model, "type": "rpd", "value": None},
                    {"model": model, "type": "tpm", "value": None},
                    {"model": model, "type": "tpd", "value": 50},  # 50 tokens per days
                ],
            },
        )
        assert response.status_code == 204, response.text

        response = client.post(
            url=f"/v1{ENDPOINT__CHAT_COMPLETIONS}",
            headers=headers,
            json={"model": model, "messages": [{"role": "user", "content": content_len_10}], "max_tokens": 1},
        )
        assert response.status_code == 200, response.text

        # Test the limit in multiple messages (fail because of the cost is 50 and the window remaining is 40)
        response = client.post(
            url=f"/v1{ENDPOINT__CHAT_COMPLETIONS}",
            headers=headers,
            json={
                "model": model,
                "messages": [{"role": "assistant", "content": content_len_10}, {"role": "user", "content": content_len_40}],
                "max_tokens": 1,
            },
        )
        assert response.status_code == 429, response.text
