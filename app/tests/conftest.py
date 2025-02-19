import logging

import pytest
from fastapi.testclient import TestClient

from app.clients import AuthenticationClient
from app.main import create_application
from app.utils.variables import COLLECTION_TYPE__PRIVATE, COLLECTION_TYPE__PUBLIC


def pytest_addoption(parser):
    parser.addoption("--base-url", action="store", default="http://localhost:8080/v1")
    parser.addoption("--api-key-user", action="store", default="EMPTY")
    parser.addoption("--api-key-admin", action="store", default="EMPTY")


@pytest.fixture(scope="session")
def args(request):
    args = {
        "base_url": request.config.getoption("--base-url"),
        "api_key_user": request.config.getoption("--api-key-user"),
        "api_key_admin": request.config.getoption("--api-key-admin"),
    }

    assert args["base_url"] != "EMPTY", "--base-url argument is required."
    assert args["api_key_user"] != "EMPTY", "--api-key-user argument is required."
    assert args["api_key_admin"] != "EMPTY", "--api-key-admin argument is required."

    return args


@pytest.fixture(scope="session")
def test_app():
    app = create_application(middleware=False)
    return app


@pytest.fixture(scope="session")
def test_client(test_app):
    with TestClient(test_app) as client:
        yield client


@pytest.fixture(scope="session")
def session_user(args, test_client):
    test_client.headers = {"Authorization": f"Bearer {args["api_key_user"]}"}
    return test_client


@pytest.fixture(scope="session")
def session_admin(args, test_client):
    test_client.headers = {"Authorization": f"Bearer {args["api_key_admin"]}"}
    return test_client


@pytest.fixture(scope="session")
def cleanup_collections(args, session_user, session_admin):
    USER = AuthenticationClient.api_key_to_user_id(input=args["api_key_user"])
    ADMIN = AuthenticationClient.api_key_to_user_id(input=args["api_key_admin"])

    yield USER, ADMIN

    logging.info("cleanup collections")
    response = session_user.get(f"{args["base_url"]}/collections")
    response.raise_for_status()
    collections = response.json()

    # delete private collections
    collection_ids = [
        collection["id"] for collection in collections["data"] if collection["type"] == COLLECTION_TYPE__PRIVATE and collection["user"] == USER
    ]

    for collection_id in collection_ids:
        session_user.delete(f"{args["base_url"]}/collections/{collection_id}")

    # delete public collections
    collection_ids = [
        collection["id"] for collection in collections["data"] if collection["type"] == COLLECTION_TYPE__PUBLIC and collection["user"] == ADMIN
    ]

    for collection_id in collection_ids:
        session_user.delete(f"{args["base_url"]}/collections/{collection_id}")
