import logging
import os
from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database
from sqlalchemy.orm import sessionmaker

from fastapi.testclient import TestClient
import pytest
import vcr

from app.clients import AuthenticationClient
from app.utils.variables import COLLECTION_TYPE__PRIVATE
from app.sql.models import Base

# Define global VCR instance and cassette
VCR_INSTANCE = None
VCR_GLOBAL_CASSETTE = None


def pytest_configure(config):
    """Called after command line options have been parsed and all plugins and initial conftest files loaded.
    This is the earliest pytest hook we can use to set up VCR globally.
    """
    global VCR_INSTANCE, VCR_GLOBAL_CASSETTE

    cassette_library_dir = Path(__file__).parent / "cassettes"
    os.makedirs(cassette_library_dir, exist_ok=True)

    VCR_INSTANCE = vcr.VCR(
        cassette_library_dir=str(cassette_library_dir),
        record_mode="once",
        match_on=["method", "scheme", "host", "port", "path", "query"],
        filter_headers=[("Authorization", "Bearer dummy_token_for_test")],
        before_record_request=lambda request: None if request.host == "testserver" else request,
        decode_compressed_response=True,
    )

    # Store the cassette object so we can properly close it later
    VCR_GLOBAL_CASSETTE = VCR_INSTANCE.use_cassette("global_setup_cassette.yaml")
    VCR_GLOBAL_CASSETTE.__enter__()


def pytest_unconfigure(config):
    """Called before test process is exited."""
    global VCR_GLOBAL_CASSETTE

    # Close the global cassette to ensure all recordings are saved
    if VCR_GLOBAL_CASSETTE is not None:
        VCR_GLOBAL_CASSETTE.__exit__(None, None, None)


def pytest_addoption(parser):
    parser.addoption("--api-key-user", action="store", default="EMPTY")
    parser.addoption("--api-key-admin", action="store", default="EMPTY")


@pytest.fixture(scope="session")
def args(request):
    args = {"api_key_user": request.config.getoption("--api-key-user"), "api_key_admin": request.config.getoption("--api-key-admin")}
    assert args["api_key_user"] != "EMPTY", "--api-key-user argument is required."
    assert args["api_key_admin"] != "EMPTY", "--api-key-admin argument is required."

    return args


def get_test_db_url(worker_id):
    """Get database URL for specific worker"""
    from app.utils.settings import settings

    if worker_id == "master":
        # Single worker mode
        return settings.databases.sql.args.get("url")
    else:
        # Multiple workers mode - append worker id to db name
        base_url = settings.databases.sql.args.get("url")
        return f"{base_url}_{worker_id}"


@pytest.fixture(scope="session")
def engine(worker_id):
    """Create database engine for tests"""
    db_url = get_test_db_url(worker_id)

    # Create database if it doesn't exist
    if not database_exists(db_url):
        create_database(db_url)

    _engine = create_engine(db_url)

    Base.metadata.drop_all(_engine)  # Clean state
    Base.metadata.create_all(_engine)

    yield _engine

    # Cleanup after all tests
    Base.metadata.drop_all(_engine)


@pytest.fixture(scope="session")
def db_session(engine):
    """Create a database session for tests"""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="session")
def app_with_test_db(engine, db_session):
    """Create FastAPI app with test database"""
    from app.main import create_app

    def get_test_db():
        yield db_session

    # Create app with test config
    app = create_app(db_func=get_test_db, disabled_middleware=False)

    return app


@pytest.fixture(scope="session")
def test_client(app_with_test_db) -> Generator[TestClient, None, None]:
    with TestClient(app=app_with_test_db) as client:
        yield client


@pytest.fixture(scope="session")
def cleanup_collections(args, test_client):
    USER = AuthenticationClient.api_key_to_user_id(input=args["api_key_user"])
    ADMIN = AuthenticationClient.api_key_to_user_id(input=args["api_key_admin"])

    yield USER, ADMIN

    # Skip cleanup if running in GitHub Actions
    if os.environ.get("GITHUB_ACTIONS") == "true":
        logging.info("Skipping collections cleanup in GitHub Actions environment")
        return

    logging.info("cleanup collections")

    # delete private collections
    response = test_client.get("/v1/collections", headers={"Authorization": f"Bearer {args["api_key_user"]}"})
    response.raise_for_status()
    collections = response.json()["data"]
    collection_ids = [collection["id"] for collection in collections if collection["type"] == COLLECTION_TYPE__PRIVATE and collection["user"] == USER]

    for collection_id in collection_ids:
        test_client.delete(f"/v1/collections/{collection_id}", headers={"Authorization": f"Bearer {args["api_key_user"]}"})

    # delete public collections
    test_client.headers = {"Authorization": f"Bearer {args["api_key_admin"]}"}
    response = test_client.get("/v1/collections", headers={"Authorization": f"Bearer {args["api_key_admin"]}"})
    response.raise_for_status()
    collections = response.json()["data"]
    collection_ids = [collection["id"] for collection in collections if collection["user"] == ADMIN]

    for collection_id in collection_ids:
        test_client.delete(f"/v1/collections/{collection_id}", headers={"Authorization": f"Bearer {args["api_key_admin"]}"})


@pytest.fixture(autouse=True)
def vcr_cassette(request):
    """Use VCR for specific tests, with per-test cassettes"""
    global VCR_GLOBAL_CASSETTE, VCR_INSTANCE

    # Skip VCR for tests that does not support it
    def module_to_skip(request):
        for module in ["test_audio", "test_documents", "test_files"]:
            if request.module.__name__.endswith(module):
                return True

    if module_to_skip(request):
        yield
        return

    # Temporarily exit the global cassette
    if VCR_GLOBAL_CASSETTE is not None:
        VCR_GLOBAL_CASSETTE.__exit__(None, None, None)

    # Use a test-specific cassette
    test_name = request.node.name.replace("[", "_").replace("]", "_")
    cassette_path = f"{request.module.__name__}.{test_name}"

    with VCR_INSTANCE.use_cassette(cassette_path + ".yaml"):
        yield

    # Re-enter the global cassette after the test is done
    if VCR_GLOBAL_CASSETTE is not None:
        VCR_GLOBAL_CASSETTE.__enter__()
