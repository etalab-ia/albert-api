from functools import partial
import logging
import time
from typing import Generator

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.utils.settings import settings
from app.utils.variables import COLLECTION_TYPE__PRIVATE
from app.schemas.auth import LimitType, PermissionType

ROLE_ADMIN = "test-role-admin"
ROLE_USER = "test-role-user"
USER_ADMIN = "test-user-admin"
USER_USER = "test-user-user"
TOKEN_ADMIN = "test-token-admin"
TOKEN_USER = "test-token-user"


@pytest.fixture(scope="session")
def test_client() -> Generator[TestClient, None, None]:
    with TestClient(app=app) as client:
        client.headers = {"Authorization": f"Bearer {settings.auth.root_key}"}
        yield client


@pytest.fixture(scope="session")
def test_roles(test_client: TestClient) -> tuple[str, str]:
    # delete tests users
    response = test_client.delete(url=f"/users/{USER_USER}")
    logging.debug(msg=f"delete user {USER_USER}: {response.text}")
    response = test_client.delete(url=f"/users/{USER_ADMIN}")
    logging.debug(msg=f"delete user {USER_ADMIN}: {response.text}")

    # delete tests roles
    response = test_client.delete(url=f"/roles/{ROLE_ADMIN}")
    logging.debug(msg=f"delete role {ROLE_ADMIN}: {response.text}")

    response = test_client.delete(url=f"/roles/{ROLE_USER}")
    logging.debug(msg=f"delete role {ROLE_USER}: {response.text}")

    # get models
    response = test_client.get(url="/v1/models")
    logging.debug(msg=f"get models: {response.text}")
    response.raise_for_status()
    models = response.json()["data"]
    models = [model["id"] for model in models]

    # get permissions
    admin_permissions = [permission.value for permission in PermissionType]
    user_permissions = [
        PermissionType.CREATE_PRIVATE_COLLECTION.value,
        PermissionType.READ_PRIVATE_COLLECTION.value,
        PermissionType.UPDATE_PRIVATE_COLLECTION.value,
        PermissionType.DELETE_PRIVATE_COLLECTION.value,
        PermissionType.READ_PUBLIC_COLLECTION.value,
    ]

    # get limits
    limits = []
    for model in models:
        limits.append({"model": model, "type": LimitType.RPM.value, "value": None})
        limits.append({"model": model, "type": LimitType.RPD.value, "value": None})
        limits.append({"model": model, "type": LimitType.TPM.value, "value": None})

    # create role admin
    response = test_client.post(url="/roles", json={"role": ROLE_ADMIN, "default": False, "permissions": admin_permissions, "limits": limits})
    logging.debug(msg=f"create role {ROLE_ADMIN}: {response.text}")
    response.raise_for_status()

    # create role user
    response = test_client.post(url="/roles", json={"role": ROLE_USER, "default": False, "permissions": user_permissions, "limits": limits})
    logging.debug(msg=f"create role {ROLE_USER}: {response.text}")
    response.raise_for_status()

    return ROLE_ADMIN, ROLE_USER


@pytest.fixture(scope="session")
def test_users(test_client: TestClient, test_roles: tuple[str, str]) -> tuple[str, str]:
    role_id_admin, role_id_user = test_roles

    # create user admin
    response = test_client.post(url="/users", json={"user": USER_ADMIN, "password": "test-password", "role": role_id_admin})
    response.raise_for_status()

    # create user user
    response = test_client.post(url="/users", json={"user": USER_USER, "password": "test-password", "role": role_id_user})
    response.raise_for_status()

    return USER_ADMIN, USER_USER


@pytest.fixture(scope="session")
def test_tokens(test_client: TestClient, test_users: tuple[str, str]) -> tuple[str, str]:
    user_id_admin, user_id_user = test_users

    # create token admin
    response = test_client.post(url="/tokens", json={"user": user_id_admin, "token": TOKEN_ADMIN, "expires_at": int(time.time()) + 300})
    response.raise_for_status()
    token_admin = response.json()["id"]
    # create token user
    response = test_client.post(url="/tokens", json={"user": user_id_user, "token": TOKEN_USER, "expires_at": int(time.time()) + 300})
    response.raise_for_status()
    token_user = response.json()["id"]

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

    # root
    client.get_root = partial(client.get, headers={"Authorization": f"Bearer {settings.auth.root_key}"})
    client.post_root = partial(client.post, headers={"Authorization": f"Bearer {settings.auth.root_key}"})
    client.delete_root = partial(client.delete, headers={"Authorization": f"Bearer {settings.auth.root_key}"})
    client.patch_root = partial(client.patch, headers={"Authorization": f"Bearer {settings.auth.root_key}"})

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

    # # delete user admin
    # response = client.delete_root(url=f"/users/{user_id_admin}")
    # response.raise_for_status()

    # # delete user user
    # response = client.delete_root(url=f"/users/{user_id_user}")
    # response.raise_for_status()

    # # delete role admin
    # response = client.delete_root(url=f"/roles/{role_id_admin}")
    # response.raise_for_status()

    # # delete role user
    # response = client.delete_root(url=f"/roles/{role_id_user}")
    # response.raise_for_status()
