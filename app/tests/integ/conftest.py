from functools import partial
import logging
import os
from pathlib import Path
import time
from typing import Generator

from fastapi.testclient import TestClient
import pytest
from qdrant_client import QdrantClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import create_database, database_exists
import vcr
import vcr.stubs.httpx_stubs
from vcr.request import Request as VcrRequest

from app.main import create_app
from app.schemas.auth import LimitType, PermissionType
from app.sql.models import Base
from app.utils.settings import settings
from app.utils.variables import ENDPOINT__MODELS, ENDPOINT__ROLES, ENDPOINT__TOKENS, ENDPOINT__USERS


# Define global VCR instance
VCR_INSTANCE = None
VCR_ENABLED = os.environ.get("VCR_ENABLED", "").lower() in ("true", "1", "yes")


def pytest_configure(config):
    """Called after command line options have been parsed and all plugins and initial conftest files loaded.
    This is the earliest pytest hook we can use to set up VCR globally.
    """
    global VCR_INSTANCE

    # Skip VCR setup if disabled
    if not VCR_ENABLED:
        logging.info("VCR is disabled via VCR_ENABLED environment variable")
        return

    cassette_library_dir = Path(__file__).parent / "cassettes"
    os.makedirs(cassette_library_dir, exist_ok=True)

    # Patch VCR to handle binary requests
    def _make_vcr_request(httpx_request, **kwargs):
        body_bytes = httpx_request.read()
        try:
            body = body_bytes.decode("utf-8")
        except UnicodeDecodeError:
            body = body_bytes
        uri = str(httpx_request.url)
        headers = dict(httpx_request.headers)
        return VcrRequest(httpx_request.method, uri, body, headers)

    vcr.stubs.httpx_stubs._make_vcr_request = _make_vcr_request
    ignore_hosts = ["testserver", os.environ.get("MCP_BRIDGE_HOST"), os.environ.get("QDRANT_HOST")]

    VCR_INSTANCE = vcr.VCR(
        cassette_library_dir=str(cassette_library_dir),
        record_mode="once",
        match_on=["method", "scheme", "host", "port", "path", "query"],
        filter_headers=[("Authorization", "Bearer dummy_token_for_test")],
        before_record_request=lambda request: None if request.host in ignore_hosts else request,
        decode_compressed_response=True,
    )


@pytest.fixture(scope="session")
def engine(worker_id):
    """Create database engine for tests"""

    db_url = settings.databases.sql.args.get("url").replace("+asyncpg", "")
    db_url = f"{db_url}_{worker_id}" if worker_id != "master" else db_url

    # Create database if it doesn't exist
    if not database_exists(url=db_url):
        create_database(url=db_url)

    engine = create_engine(url=db_url)

    Base.metadata.drop_all(engine)  # Clean state
    Base.metadata.create_all(engine)

    qdrant_client = QdrantClient(**settings.databases.qdrant.args)
    collections = qdrant_client.get_collections().collections
    for collection in collections:
        qdrant_client.delete_collection(collection_name=collection.name)

    yield engine


@pytest.fixture(scope="session")
def async_engine(worker_id):
    """Create asynchronous database engine for tests"""
    db_url = settings.databases.sql.args.get("url").replace("+asyncpg", "")
    db_url = f"{db_url}_{worker_id}" if worker_id != "master" else db_url

    # Ensure the URL uses the asyncpg driver
    async_db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

    # Create database if it doesn't exist
    if not database_exists(url=db_url):
        create_database(url=db_url)
        Base.metadata.create_all(bind=create_engine(url=db_url))

    async_engine = create_async_engine(url=async_db_url)

    yield async_engine


@pytest.fixture(scope="session")
def db_session(engine):
    """Create a database session for tests"""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="session")
async def async_db_session(async_engine):
    """Create an asynchronous database session for tests"""
    AsyncSessionMaker = sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)
    async with AsyncSessionMaker() as session:
        yield session


@pytest.fixture(scope="session")
def app_with_test_db(engine, db_session):
    """Create FastAPI app with test database"""

    def get_test_db():
        yield db_session

    # Create app with test config
    app = create_app(db_func=get_test_db)
    return app


@pytest.fixture(scope="session")
def test_client(app_with_test_db) -> Generator[TestClient, None, None]:
    # Lifespan requests API to get models and initialize the app
    if VCR_ENABLED:
        with VCR_INSTANCE.use_cassette("lifespan_init.yaml"):
            with TestClient(app=app_with_test_db) as client:
                client.headers = {"Authorization": f"Bearer {settings.auth.master_key}"}
                yield client
    else:
        with TestClient(app=app_with_test_db) as client:
            client.headers = {"Authorization": f"Bearer {settings.auth.master_key}"}
            yield client


@pytest.fixture(scope="module")
def record_with_vcr(request):
    """Use VCR for module-level fixtures"""
    if not VCR_ENABLED:
        yield
        return

    module_name = request.module.__name__
    cassette_path = f"{module_name}_module_setup"

    with VCR_INSTANCE.use_cassette(cassette_path + ".yaml"):
        yield


# Keep the existing per-test fixture
@pytest.fixture(autouse=True)
def vcr_cassette(request):
    """Use VCR for specific tests, with per-test cassettes"""
    # Skip if VCR is disabled via environment variable
    if not VCR_ENABLED:
        yield
        return

    test_name = request.node.name.replace("[", "_").replace("]", "_")
    cassette_path = f"{request.module.__name__}.{test_name}"

    with VCR_INSTANCE.use_cassette(cassette_path + ".yaml"):
        yield


@pytest.fixture(scope="session")
def roles(test_client: TestClient) -> tuple[dict, dict]:
    """Create roles for tests, one with permissions and one without permissions."""

    # get limits
    response = test_client.get(url=f"/v1{ENDPOINT__MODELS}")
    logging.debug(msg=f"get models: {response.text}")
    response.raise_for_status()
    models = response.json()["data"]
    models = [model["id"] for model in models]

    limits = []
    for model in models:
        limits.append({"model": model, "type": LimitType.RPM.value, "value": None})
        limits.append({"model": model, "type": LimitType.RPD.value, "value": None})
        limits.append({"model": model, "type": LimitType.TPM.value, "value": None})
        limits.append({"model": model, "type": LimitType.TPD.value, "value": None})

    limits.append({"model": "web-search", "type": LimitType.RPM.value, "value": None})
    limits.append({"model": "web-search", "type": LimitType.RPD.value, "value": None})
    limits.append({"model": "web-search", "type": LimitType.TPM.value, "value": None})
    limits.append({"model": "web-search", "type": LimitType.TPD.value, "value": None})

    # create role admin
    response = test_client.post(
        url=ENDPOINT__ROLES,
        json={"name": "test-role-admin", "default": False, "permissions": [permission.value for permission in PermissionType], "limits": limits},
    )
    logging.debug(msg=f"create role test-role-admin: {response.text}")
    response.raise_for_status()

    role_id_with_permissions = response.json()["id"]
    # create role user
    response = test_client.post(url=ENDPOINT__ROLES, json={"name": "test-role-user", "default": False, "permissions": [], "limits": limits})
    logging.debug(msg=f"create role test-role-user: {response.text}")
    response.raise_for_status()
    role_id_without_permissions = response.json()["id"]

    response = test_client.get(url=f"{ENDPOINT__ROLES}/{role_id_with_permissions}")
    logging.debug(msg=f"get role test-role-with-permissions: {response.text}")
    response.raise_for_status()
    role_with_permissions = response.json()

    response = test_client.get(url=f"{ENDPOINT__ROLES}/{role_id_without_permissions}")
    logging.debug(msg=f"get role test-role-without-permissions: {response.text}")
    response.raise_for_status()
    role_without_permissions = response.json()

    return role_with_permissions, role_without_permissions


@pytest.fixture(scope="session")
def users(test_client: TestClient, roles: tuple[dict, dict]) -> tuple[dict, dict]:
    """Create users for tests, one with admin role and one with user role."""

    role_with_permissions, role_without_permissions = roles

    # create user admin
    response = test_client.post(
        url=ENDPOINT__USERS, json={"name": "test-user-admin", "password": "test-password", "role": role_with_permissions["id"]}
    )
    response.raise_for_status()
    user_id_with_permissions = response.json()["id"]

    response = test_client.get(url=f"{ENDPOINT__USERS}/{user_id_with_permissions}")
    logging.debug(msg=f"get user test-user-with-permissions: {response.text}")
    response.raise_for_status()
    user_with_permissions = response.json()

    # create user user
    response = test_client.post(
        url=ENDPOINT__USERS, json={"name": "test-user-user", "password": "test-password", "role": role_without_permissions["id"]}
    )
    response.raise_for_status()
    user_id_user = response.json()["id"]

    response = test_client.get(url=f"{ENDPOINT__USERS}/{user_id_user}")
    logging.debug(msg=f"get user test-user-without-permissions: {response.text}")
    response.raise_for_status()
    user_without_permissions = response.json()

    return user_with_permissions, user_without_permissions


@pytest.fixture(scope="session")
def tokens(test_client: TestClient, users: tuple[dict, dict]) -> tuple[dict, dict]:
    user_with_permissions, user_without_permissions = users

    # create token admin
    response = test_client.post(
        url=ENDPOINT__TOKENS, json={"user": user_with_permissions["id"], "name": "test-token-admin", "expires_at": int(time.time()) + 300}
    )
    response.raise_for_status()
    token_with_permissions = response.json()

    # create token user
    response = test_client.post(
        url=ENDPOINT__TOKENS, json={"user": user_without_permissions["id"], "name": "test-token-user", "expires_at": int(time.time()) + 300}
    )
    response.raise_for_status()
    token_without_permissions = response.json()

    return token_with_permissions, token_without_permissions


@pytest.fixture(scope="session")
def client(test_client: TestClient, tokens: tuple[dict, dict]) -> Generator[TestClient, None, None]:
    token_with_permissions, token_without_permissions = tokens

    client = test_client

    # user
    client.get_without_permissions = partial(client.get, headers={"Authorization": f"Bearer {token_without_permissions["token"]}"})
    client.post_without_permissions = partial(client.post, headers={"Authorization": f"Bearer {token_without_permissions["token"]}"})
    client.delete_without_permissions = partial(client.delete, headers={"Authorization": f"Bearer {token_without_permissions["token"]}"})
    client.patch_without_permissions = partial(client.patch, headers={"Authorization": f"Bearer {token_without_permissions["token"]}"})

    # admin
    client.get_with_permissions = partial(client.get, headers={"Authorization": f"Bearer {token_with_permissions["token"]}"})
    client.post_with_permissions = partial(client.post, headers={"Authorization": f"Bearer {token_with_permissions["token"]}"})
    client.delete_with_permissions = partial(client.delete, headers={"Authorization": f"Bearer {token_with_permissions["token"]}"})
    client.patch_with_permissions = partial(client.patch, headers={"Authorization": f"Bearer {token_with_permissions["token"]}"})

    # root
    client.get_master = partial(client.get, headers={"Authorization": f"Bearer {settings.auth.master_key}"})
    client.post_master = partial(client.post, headers={"Authorization": f"Bearer {settings.auth.master_key}"})
    client.delete_master = partial(client.delete, headers={"Authorization": f"Bearer {settings.auth.master_key}"})
    client.patch_master = partial(client.patch, headers={"Authorization": f"Bearer {settings.auth.master_key}"})

    yield client
