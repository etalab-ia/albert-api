from functools import partial
import logging
import time
from typing import Generator
import uuid

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.utils.settings import settings
from app.utils.variables import COLLECTION_TYPE__PRIVATE


@pytest.fixture(scope="session")
def test_client() -> Generator[TestClient, None, None]:
    with TestClient(app=app) as client:
        client.headers = {"Authorization": f"Bearer {settings.auth.master_key}"}
        yield client


@pytest.fixture(scope="session")
def test_roles(test_client: TestClient) -> tuple[str, str]:
    # delete tests users
    response = test_client.delete(url="/users/test-user-admin")
    response = test_client.delete(url="/users/test-user-user")

    # delete tests roles
    response = test_client.delete(url="/roles/test-role-admin")
    response = test_client.delete(url="/roles/test-role-user")

    # create role admin
    response = test_client.post(url="/roles", json={"role": "test-role-admin", "default": False, "admin": True})
    response.raise_for_status()
    role_id_admin = response.text

    # create role user
    response = test_client.post(url="/roles", json={"role": "test-role-user", "default": False, "admin": False})
    response.raise_for_status()
    role_id_user = response.text

    return role_id_admin, role_id_user


@pytest.fixture(scope="session")
def test_users(test_client: TestClient, test_roles: tuple[str, str]) -> tuple[str, str]:
    role_id_admin, role_id_user = test_roles

    # create user admin
    response = test_client.post(
        url="/users",
        json={"user": "test-user-admin", "password": str(uuid.uuid4()), "role": role_id_admin},
    )
    response.raise_for_status()
    user_id_admin = response.text

    # create user user
    response = test_client.post(
        url="/users",
        json={"user": "test-user-user", "password": str(uuid.uuid4()), "role": role_id_user},
    )
    response.raise_for_status()
    user_id_user = response.text

    return user_id_admin, user_id_user


@pytest.fixture(scope="session")
def test_tokens(test_client: TestClient, test_users: tuple[str, str]) -> tuple[str, str]:
    user_id_admin, user_id_user = test_users

    # create token admin
    response = test_client.post(url="/tokens", json={"user": user_id_admin, "token": "test-token-admin", "expires_at": int(time.time()) + 300})
    response.raise_for_status()

    token_admin = response.text

    # create token user
    response = test_client.post(url="/tokens", json={"user": user_id_user, "token": "test-token-user", "expires_at": int(time.time()) + 300})
    response.raise_for_status()
    token_user = response.text

    return token_admin, token_user


@pytest.fixture(scope="session")
def client(test_client: TestClient, test_tokens: tuple[str, str]) -> Generator[TestClient, None, None]:
    token_admin, token_user = test_tokens

    client = test_client

    # user
    client.get_user = partial(client.get, headers={"Authorization": f"Bearer {token_user}"})
    client.post_user = partial(client.post, headers={"Authorization": f"Bearer {token_user}"})
    client.delete_user = partial(client.delete, headers={"Authorization": f"Bearer {token_user}"})
    client.patch_user = partial(client.patch, headers={"Authorization": f"Bearer {token_user}"})

    # admin
    client.get_admin = partial(client.get, headers={"Authorization": f"Bearer {token_admin}"})
    client.post_admin = partial(client.post, headers={"Authorization": f"Bearer {token_admin}"})
    client.delete_admin = partial(client.delete, headers={"Authorization": f"Bearer {token_admin}"})
    client.patch_admin = partial(client.patch, headers={"Authorization": f"Bearer {token_admin}"})

    # master
    client.get_master = partial(client.get, headers={"Authorization": f"Bearer {settings.auth.master_key}"})
    client.post_master = partial(client.post, headers={"Authorization": f"Bearer {settings.auth.master_key}"})
    client.delete_master = partial(client.delete, headers={"Authorization": f"Bearer {settings.auth.master_key}"})
    client.patch_master = partial(client.patch, headers={"Authorization": f"Bearer {settings.auth.master_key}"})

    yield client


@pytest.fixture(scope="session")
def cleanup(client: TestClient, test_roles: tuple[str, str], test_users: tuple[str, str]):
    user_id_admin, user_id_user = test_users
    role_id_admin, role_id_user = test_roles

    yield role_id_admin, role_id_user, user_id_admin, user_id_user

    logging.info(msg="cleanup collections")

    # delete private collections
    response = client.get_user(url="/v1/collections")
    response.raise_for_status()
    collections = response.json()["data"]
    collection_ids = [collection["id"] for collection in collections if collection["type"] == COLLECTION_TYPE__PRIVATE and collection["user"] == user_id_user]  # fmt: off
    for collection_id in collection_ids:
        client.delete_user(url=f"/v1/collections/{collection_id}")

    # delete public collections
    response = client.get_admin(url="/v1/collections")
    response.raise_for_status()
    collections = response.json()["data"]
    collection_ids = [collection["id"] for collection in collections if collection["user"] == user_id_admin]

    for collection_id in collection_ids:
        client.delete_admin(url=f"/v1/collections/{collection_id}")

    logging.info(msg="cleanup users")

    # delete user admin
    response = client.delete_master(url=f"/users/{user_id_admin}")
    response.raise_for_status()

    # delete user user
    response = client.delete_master(url=f"/users/{user_id_user}")
    response.raise_for_status()

    # delete role admin
    response = client.delete_master(url=f"/roles/{role_id_admin}")
    response.raise_for_status()

    # delete role user
    response = client.delete_master(url=f"/roles/{role_id_user}")
    response.raise_for_status()
