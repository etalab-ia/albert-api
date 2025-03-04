from functools import partial
import logging
import os
from pathlib import Path
import time
from typing import Generator

from fastapi.testclient import TestClient
import pytest
import vcr


from app.main import app
from app.utils.settings import settings
from app.schemas.collections import CollectionVisibility
from app.schemas.auth import LimitType, PermissionType

# def get_test_db_url(worker_id):
#     """Get database URL for specific worker"""
#     from app.utils.settings import settings

#     if worker_id == "master":
#         # Single worker mode
#         return settings.databases.sql.args.get("url")
#     else:
#         # Multiple workers mode - append worker id to db name
#         base_url = settings.databases.sql.args.get("url")
#         return f"{base_url}_{worker_id}"


# @pytest.fixture(scope="session")
# def engine(worker_id):
#     """Create database engine for tests"""
#     db_url = get_test_db_url(worker_id)

#     # Create database if it doesn't exist
#     if not database_exists(db_url):
#         create_database(db_url)

#     _engine = create_engine(db_url)

#     Base.metadata.drop_all(_engine)  # Clean state
#     Base.metadata.create_all(_engine)

#     yield _engine

#     # Cleanup after all tests
#     Base.metadata.drop_all(_engine)
#     drop_database(db_url)


# @pytest.fixture(scope="session")
# def db_session(engine):
#     """Create a database session for tests"""
#     Session = sessionmaker(bind=engine)
#     session = Session()
#     yield session
#     session.close()


# @pytest.fixture(scope="session")
# def app_with_test_db(engine, db_session):
#     """Create FastAPI app with test database"""
#     from app.main import create_app

#     def get_test_db():
#         yield db_session

#     # Create app with test config
#     app = create_app(db_func=get_test_db, disabled_middleware=False)

#     return app


# @pytest.fixture(scope="session")
# def test_client(app_with_test_db) -> Generator[TestClient, None, None]:
#     with TestClient(app=app_with_test_db) as client:
def test_client() -> Generator[TestClient, None, None]:
    with TestClient(app=app) as client:
        client.headers = {"Authorization": f"Bearer {settings.auth.master_key}"}
        yield client


@pytest.fixture(scope="session")
def test_roles(test_client: TestClient) -> tuple[str, str]:
    # get models
    response = test_client.get(url="/v1/models")
    logging.debug(msg=f"get models: {response.text}")
    response.raise_for_status()
    models = response.json()["data"]
    models = [model["id"] for model in models]

    # get permissions
    admin_permissions = [permission.value for permission in PermissionType]
    user_permissions = []

    # get limits
    limits = []
    for model in models:
        limits.append({"model": model, "type": LimitType.RPM.value, "value": None})
        limits.append({"model": model, "type": LimitType.RPD.value, "value": None})
        limits.append({"model": model, "type": LimitType.TPM.value, "value": None})

    # create role admin
    response = test_client.post(url="/roles", json={"name": "test-role-admin", "default": False, "permissions": admin_permissions, "limits": limits})
    logging.debug(msg=f"create role test-role-admin: {response.text}")
    response.raise_for_status()

    role_id_admin = response.json()["id"]
    # create role user
    response = test_client.post(url="/roles", json={"name": "test-role-user", "default": False, "permissions": user_permissions, "limits": limits})
    logging.debug(msg=f"create role test-role-user: {response.text}")
    response.raise_for_status()
    role_id_user = response.json()["id"]

    return role_id_admin, role_id_user


@pytest.fixture(scope="session")
def test_users(test_client: TestClient, test_roles: tuple[int, int]) -> tuple[int, int]:
    role_id_admin, role_id_user = test_roles

    # create user admin
    response = test_client.post(url="/users", json={"name": "test-user-admin", "password": "test-password", "role": role_id_admin})
    response.raise_for_status()
    user_id_admin = response.json()["id"]

    # create user user
    response = test_client.post(url="/users", json={"name": "test-user-user", "password": "test-password", "role": role_id_user})
    response.raise_for_status()
    user_id_user = response.json()["id"]

    return user_id_admin, user_id_user


@pytest.fixture(scope="session")
def test_tokens(test_client: TestClient, test_users: tuple[int, int]) -> tuple[int, int]:
    user_id_admin, user_id_user = test_users

    # create token admin
    response = test_client.post(url="/tokens", json={"user": user_id_admin, "name": "test-token-admin", "expires_at": int(time.time()) + 300})
    response.raise_for_status()
    token_admin = response.json()["token"]

    # create token user
    response = test_client.post(url="/tokens", json={"user": user_id_user, "name": "test-token-user", "expires_at": int(time.time()) + 300})
    response.raise_for_status()
    token_user = response.json()["token"]

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
    client.get_master = partial(client.get, headers={"Authorization": f"Bearer {settings.auth.master_key}"})
    client.post_master = partial(client.post, headers={"Authorization": f"Bearer {settings.auth.master_key}"})
    client.delete_master = partial(client.delete, headers={"Authorization": f"Bearer {settings.auth.master_key}"})
    client.patch_master = partial(client.patch, headers={"Authorization": f"Bearer {settings.auth.master_key}"})

    yield client


@pytest.fixture(scope="session")
def cleanup(client: TestClient, test_roles: tuple[int, int], test_users: tuple[int, int]):
    user_id_admin, user_id_user = test_users
    role_id_admin, role_id_user = test_roles

    yield role_id_admin, role_id_user, user_id_admin, user_id_user

    logging.info(msg="cleanup collections")

    # delete private collections
    response = client.get_user(url="/v1/collections")
    response.raise_for_status()
    collections = response.json()["data"]
    collection_ids = [collection["id"] for collection in collections if collection["visibility"] == CollectionVisibility.PRIVATE]
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


@pytest.fixture(autouse=True)
def vcr_config():
    """Global VCR configuration"""
    cassette_library_dir = Path(__file__).parent / "cassettes"
    os.makedirs(cassette_library_dir, exist_ok=True)

    custom_vcr = vcr.VCR(
        cassette_library_dir=str(cassette_library_dir),
        record_mode="once",
        match_on=["method", "scheme", "host", "port", "path", "query"],
        filter_headers=["authorization"],
        before_record_request=lambda request: None if request.host == "testserver" else request,
        decode_compressed_response=True,
    )

    return custom_vcr


@pytest.fixture(autouse=True)
def vcr_cassette(request, vcr_config):
    """Automatically use VCR for each test"""

    # Skip VCR for tests that does not support it
    def module_to_skip(request):
        for module in ["test_audio", "test_documents", "test_files"]:
            if request.module.__name__.endswith(module):
                return True

    if module_to_skip(request):
        yield
        return

    test_name = request.node.name.replace("[", "_").replace("]", "_")
    cassette_path = f"{request.module.__name__}.{test_name}"

    with vcr_config.use_cassette(cassette_path + ".yaml"):
        yield
