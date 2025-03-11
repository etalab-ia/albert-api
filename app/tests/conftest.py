import logging
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from app.clients import AuthenticationClient
from app.main import app
from app.utils.variables import COLLECTION_TYPE__PRIVATE
from app.utils.settings import settings


def pytest_addoption(parser):
    parser.addoption("--api-key-user", action="store", default="EMPTY")
    parser.addoption("--api-key-admin", action="store", default="EMPTY")


@pytest.fixture(scope="session")
def args(request):
    if settings.databases.grist:
        api_key_user = request.config.getoption("--api-key-user")
        api_key_admin = request.config.getoption("--api-key-admin")

        assert api_key_user != "EMPTY", "--api-key-user argument is required."
        assert api_key_admin != "EMPTY", "--api-key-admin argument is required."

        return {"api_key_user": api_key_user, "api_key_admin": api_key_admin}
    return None  # No authentication needed


@pytest.fixture(scope="session")
def test_client() -> Generator[TestClient, None, None]:
    with TestClient(app=app) as client:
        yield client


@pytest.fixture(scope="session")
def cleanup_collections(args, test_client):
    if not settings.databases.grist:
        pytest.skip("Skipping authentication-dependent tests because authentication is disabled.")

    USER = AuthenticationClient.api_key_to_user_id(input=args["api_key_user"])
    ADMIN = AuthenticationClient.api_key_to_user_id(input=args["api_key_admin"])

    yield USER, ADMIN

    logging.info("cleanup collections")

    # delete private collections
    response = test_client.get("/v1/collections", headers={"Authorization": f"Bearer {args['api_key_user']}"})
    response.raise_for_status()
    collections = response.json()["data"]
    collection_ids = [collection["id"] for collection in collections if collection["type"] == COLLECTION_TYPE__PRIVATE and collection["user"] == USER]

    for collection_id in collection_ids:
        test_client.delete(f"/v1/collections/{collection_id}", headers={"Authorization": f"Bearer {args['api_key_user']}"})

    # delete public collections
    test_client.headers = {"Authorization": f"Bearer {args['api_key_admin']}"}
    response = test_client.get("/v1/collections", headers={"Authorization": f"Bearer {args['api_key_admin']}"})
    response.raise_for_status()
    collections = response.json()["data"]
    collection_ids = [collection["id"] for collection in collections if collection["user"] == ADMIN]

    for collection_id in collection_ids:
        test_client.delete(f"/v1/collections/{collection_id}", headers={"Authorization": f"Bearer {args['api_key_admin']}"})
