from datetime import datetime, timedelta
import time
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from redis import Redis

from app.helpers._usagetokenizer import UsageTokenizer

from app.schemas.auth import LimitType
from app.utils.settings import settings
from app.utils.variables import (
    ENDPOINT__CHAT_COMPLETIONS,
    ENDPOINT__COLLECTIONS,
    ENDPOINT__MODELS,
    ENDPOINT__ROLES,
    ENDPOINT__ROLES_ME,
    ENDPOINT__TOKENS,
    ENDPOINT__USERS,
    ENDPOINT__USERS_ME,
)


@pytest.fixture(scope="module")
def clean_redis() -> None:
    """Delete all redis keys for rate limiting conflicts."""
    r = Redis(**settings.databases.redis.args)
    assert r.ping(), "Redis database is not reachable."

    for key in r.keys():
        r.delete(key)


@pytest.fixture(scope="module")
def tokenizer():
    tokenizer = UsageTokenizer(settings.general.tokenizer)
    tokenizer = tokenizer.tokenizer

    yield tokenizer


@pytest.fixture(scope="module")
def text_generation_model(client: TestClient):
    response = client.get(url=f"/v1{ENDPOINT__MODELS}")
    assert response.status_code == 200, response.text
    model = [model["id"] for model in response.json()["data"] if model["type"] == "text-generation"][0]

    yield model


@pytest.mark.usefixtures("client", "clean_redis", "tokenizer", "roles", "text_generation_model")
class TestAuth:
    def test_user_account_expiration_format(self, client: TestClient, roles: tuple[dict, dict]):
        role_with_permissions, role_without_permissions = roles

        # Create a test user with no expiration
        response = client.post_with_permissions(
            url=ENDPOINT__USERS,
            json={"name": f"test_user_{str(uuid4())}", "role": role_without_permissions["id"]},
        )
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
            json={"name": f"test_user_{str(uuid4())}", "role": role_without_permissions["id"], "expires_at": past_expiration},
        )
        assert response.status_code == 422, response.text

        # Create user with expiration set to 5 minutes in the future
        future_expiration = int((time.time()) + 5 * 60)
        response = client.post_with_permissions(
            url=f"{ENDPOINT__USERS}",
            json={"name": f"test_user_{str(uuid4())}", "role": role_without_permissions["id"], "expires_at": future_expiration},
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

    def test_user_account_expiration_access(self, client: TestClient, roles: tuple[dict, dict]):
        role_with_permissions, role_without_permissions = roles

        # Create user with expiration set to 2 seconds in the future
        future_expiration = int((time.time()) + 2)

        # Create user
        response = client.post_with_permissions(
            url=f"{ENDPOINT__USERS}",
            json={"name": f"test_user_{str(uuid4())}", "role": role_without_permissions["id"], "expires_at": future_expiration},
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
        response = client.get(url=ENDPOINT__USERS_ME, headers=headers)
        assert response.status_code == 200, response.text

        response = client.get(url=ENDPOINT__ROLES_ME, headers=headers)
        assert response.status_code == 200, response.text

    def test_create_token_after_max_token_expiration_days(self, client: TestClient, roles: tuple[dict, dict]):
        role_with_permissions, role_without_permissions = roles

        # Create a user with no expiration
        response = client.post_with_permissions(
            url=ENDPOINT__USERS,
            json={"name": f"test_user_{str(uuid4())}", "role": role_without_permissions["id"]},
        )
        assert response.status_code == 201, response.text
        user_id = response.json()["id"]

        # Create a token for this user
        response = client.post_with_permissions(
            url=ENDPOINT__TOKENS,
            json={
                "name": f"test_token_{str(uuid4())}",
                "user": user_id,
                "expires_at": int((time.time()) + (settings.auth.max_token_expiration_days + 10) * 86400 + 1),
            },
        )
        assert response.status_code == 422, response.text

    def test_token_rate_limits(self, client: TestClient, tokenizer, text_generation_model):
        # Create a role with token limits
        response = client.post_with_permissions(
            url=ENDPOINT__ROLES,
            json={
                "name": f"test_role_{str(uuid4())}",
                "limits": [
                    {"model": text_generation_model, "type": LimitType.RPM.value, "value": None},
                    {"model": text_generation_model, "type": LimitType.RPD.value, "value": None},
                    {"model": text_generation_model, "type": LimitType.TPM.value, "value": None},
                    {"model": text_generation_model, "type": LimitType.TPD.value, "value": 10},  # 10 tokens per days
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
            json={"model": text_generation_model, "messages": [{"role": "user", "content": content_len_5}], "max_tokens": 1},
        )
        assert response.status_code == 200, response.text

        response = client.post(
            url=f"/v1{ENDPOINT__CHAT_COMPLETIONS}",
            headers=headers,
            json={"model": text_generation_model, "messages": [{"role": "user", "content": content_len_10}], "max_tokens": 1},
        )

        assert response.status_code == 429, response.text

        # Increase the limit
        response = client.patch_with_permissions(
            url=f"{ENDPOINT__ROLES}/{role_id}",
            json={
                "name": f"test_role_{str(uuid4())}",
                "limits": [
                    {"model": text_generation_model, "type": "rpm", "value": None},
                    {"model": text_generation_model, "type": "rpd", "value": None},
                    {"model": text_generation_model, "type": "tpm", "value": None},
                    {"model": text_generation_model, "type": "tpd", "value": 50},  # 50 tokens per days
                ],
            },
        )
        assert response.status_code == 204, response.text

        response = client.post(
            url=f"/v1{ENDPOINT__CHAT_COMPLETIONS}",
            headers=headers,
            json={"model": text_generation_model, "messages": [{"role": "user", "content": content_len_10}], "max_tokens": 1},
        )
        assert response.status_code == 200, response.text

        # Test the limit in multiple messages (fail because of the cost is 50 and the window remaining is 40)
        response = client.post(
            url=f"/v1{ENDPOINT__CHAT_COMPLETIONS}",
            headers=headers,
            json={
                "model": text_generation_model,
                "messages": [{"role": "assistant", "content": content_len_10}, {"role": "user", "content": content_len_40}],
                "max_tokens": 1,
            },
        )
        assert response.status_code == 429, response.text

    def test_user_budget(self, client: TestClient, tokenizer, text_generation_model):
        # Create a user
        initial_budget = 10
        response = client.post_with_permissions(
            url=ENDPOINT__USERS,
            json={"name": f"test_user_{str(uuid4())}", "role": 1, "budget": initial_budget},
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

        # Test the budget
        prompt = "Hello, how are you?"
        prompt_tokens = len(tokenizer.encode(prompt))

        response = client.post(
            url=f"/v1{ENDPOINT__CHAT_COMPLETIONS}",
            headers={"Authorization": f"Bearer {token}"},
            json={"model": text_generation_model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 100},
        )
        assert response.status_code == 200, response.text

        completion_tokens = len(tokenizer.encode(response.json()["choices"][0]["message"]["content"]))
        cost = round(prompt_tokens / 1000000 * 1 + completion_tokens / 1000000 * 3, ndigits=6)

        assert response.json()["usage"]["cost"] == cost, response.text

        # Check that the budget is updated
        response = client.get_with_permissions(url=f"{ENDPOINT__USERS}/{user_id}")
        assert response.json()["budget"] < initial_budget, response.text

        # Update the budget
        response = client.patch_with_permissions(url=f"{ENDPOINT__USERS}/{user_id}", json={"budget": 0})
        assert response.status_code == 204, response.text

        # Check that the budget is updated
        response = client.get_with_permissions(url=f"{ENDPOINT__USERS}/{user_id}")
        assert response.json()["budget"] == 0, response.text

        # Test the budget
        prompt = "Hello, how are you?"
        prompt_tokens = len(tokenizer.encode(prompt))

        response = client.post(
            url=f"/v1{ENDPOINT__CHAT_COMPLETIONS}",
            headers={"Authorization": f"Bearer {token}"},
            json={"model": text_generation_model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 100},
        )
        assert response.status_code == 400, response.text

    def test_token_name_collision(self, client: TestClient, roles: tuple[dict, dict]):
        """Test that tokens with same name across different users don't interfere with each other"""
        role_with_permissions, role_without_permissions = roles
        token_name = f"shared_token_name_{str(uuid4())}"

        # Create first user
        response = client.post_with_permissions(
            url=ENDPOINT__USERS,
            json={"name": f"user1_{str(uuid4())}", "role": role_without_permissions["id"]},
        )
        assert response.status_code == 201, response.text
        user1_id = response.json()["id"]

        # Create token for first user using admin credentials
        response = client.post_with_permissions(
            url=ENDPOINT__TOKENS,
            json={"name": token_name, "user": user1_id},
        )
        assert response.status_code == 201, response.text
        user1_token_id = response.json()["id"]
        user1_token = response.json()["token"]

        # Get first user's token
        headers1 = {"Authorization": f"Bearer {user1_token}"}
        response = client.get(
            url=f"{ENDPOINT__TOKENS}/{user1_token_id}",
            headers=headers1,
        )
        assert response.status_code == 200, response.text
        user1_token_data = response.json()

        # Create a collection using first user's token
        response = client.post(
            url=f"/v1{ENDPOINT__COLLECTIONS}",
            headers=headers1,
            json={"name": f"collection_user1_{str(uuid4())}", "visibility": "private"},
        )
        assert response.status_code == 201, response.text
        collection_id = response.json()["id"]

        # Create second user
        response = client.post_with_permissions(
            url=ENDPOINT__USERS,
            json={"name": f"user2_{str(uuid4())}", "role": role_without_permissions["id"]},
        )
        assert response.status_code == 201, response.text
        user2_id = response.json()["id"]

        # Create token for second user with the same name using admin credentials
        response = client.post_with_permissions(
            url=ENDPOINT__TOKENS,
            json={"name": token_name, "user": user2_id, "expires_at": int((time.time()) + 300)},
        )
        assert response.status_code == 201, response.text
        user2_token_id = response.json()["id"]
        user2_token = response.json()["token"]

        # Get second user's token
        headers2 = {"Authorization": f"Bearer {user2_token}"}
        response = client.get(
            url=f"{ENDPOINT__TOKENS}/{user2_token_id}",
            headers=headers2,
        )
        assert response.status_code == 200, response.text
        user2_token_data = response.json()

        # Check that tokens are different for both users
        assert user1_token_data["token"] != user2_token_data["token"], "Tokens across users should be unique"

        # Do it again to expose collision when creating a token with the same name
        # Get first user's token again to check it was not affected
        headers1 = {"Authorization": f"Bearer {user1_token}"}
        response = client.get(
            url=f"{ENDPOINT__TOKENS}/{user1_token_id}",
            headers=headers1,
        )
        assert response.status_code == 200, response.text
        user1_token_data = response.json()

        # Try to access collection created by first user with first user's token
        response = client.get(
            url=f"/v1{ENDPOINT__COLLECTIONS}/{collection_id}",
            headers=headers1,
        )
        assert response.status_code == 200, "Second user should not have access to first user's private collection"
        # Try to access collection created by first user with second user's token
        response = client.get(
            url=f"/v1{ENDPOINT__COLLECTIONS}/{collection_id}",
            headers=headers2,
        )
        assert response.status_code == 404, "Second user should not have access to first user's private collection"

        # Verify first user can still access their collection
        response = client.get(
            url=f"/v1{ENDPOINT__COLLECTIONS}/{collection_id}",
            headers=headers1,
        )
        assert response.status_code == 200, "First user should still have access to their collection"

        # Check that tokens are different for both users
        assert user1_token_data["token"] != user2_token_data["token"], "Tokens with same name across users should not be modified by each other"
