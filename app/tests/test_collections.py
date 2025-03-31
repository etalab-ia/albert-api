import logging

from fastapi.testclient import TestClient
import pytest

from app.schemas.collections import Collection, Collections, CollectionVisibility
from app.schemas.models import ModelType


@pytest.fixture(scope="module")
def setup(client: TestClient):
    response = client.get_user(url="/v1/models", timeout=10)
    models = response.json()
    EMBEDDINGS_MODEL_ID = [model for model in models["data"] if model["type"] == ModelType.TEXT_EMBEDDINGS_INFERENCE][0]["id"]
    LANGUAGE_MODEL_ID = [model for model in models["data"] if model["type"] == ModelType.TEXT_GENERATION][0]["id"]
    logging.info(f"test embedings model ID: {EMBEDDINGS_MODEL_ID}")
    logging.info(f"test language model ID: {LANGUAGE_MODEL_ID}")

    yield EMBEDDINGS_MODEL_ID, LANGUAGE_MODEL_ID


@pytest.mark.usefixtures("client", "setup", "cleanup")
class TestCollections:
    def test_create_private_collection_with_user(self, client: TestClient, setup):
        EMBEDDINGS_MODEL_ID, _ = setup

        params = {"name": "test-collection-private", "model": EMBEDDINGS_MODEL_ID, "visibility": CollectionVisibility.PRIVATE}
        response = client.post_user(url="/v1/collections", json=params)
        assert response.status_code == 201, response.text
        assert "id" in response.json().keys()

    def test_create_public_collection_with_user(self, client: TestClient, setup):
        EMBEDDINGS_MODEL_ID, _ = setup

        params = {"name": "test-collection-public", "model": EMBEDDINGS_MODEL_ID, "visibility": CollectionVisibility.PUBLIC}
        response = client.post_user(url="/v1/collections", json=params)
        assert response.status_code == 403, response.text

    def test_create_public_collection_with_admin(self, client: TestClient, setup):
        EMBEDDINGS_MODEL_ID, _ = setup

        params = {"name": "test-collection-public", "model": EMBEDDINGS_MODEL_ID, "visibility": CollectionVisibility.PUBLIC}
        response = client.post_admin(url="/v1/collections", json=params)
        assert response.status_code == 201, response.text
        assert "id" in response.json().keys()

    def test_create_private_collection_with_language_model_with_user(self, client: TestClient, setup):
        _, LANGUAGE_MODEL_ID = setup

        params = {"name": "test-collection-private", "model": LANGUAGE_MODEL_ID, "visibility": CollectionVisibility.PRIVATE}
        response = client.post_user(url="/v1/collections", json=params)
        assert response.status_code == 422, response.text

    def test_create_private_collection_with_unknown_model_with_user(self, client: TestClient, setup):
        _, _ = setup

        params = {"name": "test-collection-private", "model": "unknown-model", "visibility": CollectionVisibility.PRIVATE}
        response = client.post_user(url="/v1/collections", json=params)
        assert response.status_code == 404, response.text

    def test_get_collections(self, client: TestClient, setup):
        _, _ = setup

        response = client.get_user(url="/v1/collections")
        assert response.status_code == 200, response.text

        collections = response.json()
        collections["data"] = [Collection(**collection) for collection in collections["data"]]  # test output format
        collections = Collections(**collections)  # test output format

        assert "collections" not in [collection.id for collection in collections.data]
        assert "documents" not in [collection.id for collection in collections.data]

        assert "test-collection-private" in [collection.name for collection in collections.data]
        assert "test-collection-public" in [collection.name for collection in collections.data]

        assert [collection.user for collection in collections.data if collection.name == "test-collection-private"][0] == "test-user-user"
        assert [collection.user for collection in collections.data if collection.name == "test-collection-public"][0] == "test-user-admin"

    def test_get_collection_of_other_user(self, client: TestClient, setup):
        EMBEDDINGS_MODEL_ID, _ = setup

        params = {"name": "test-collection-private-admin", "model": EMBEDDINGS_MODEL_ID, "visibility": CollectionVisibility.PRIVATE}
        response = client.post_admin(url="/v1/collections", json=params)
        assert response.status_code == 201, response.text

        response = client.get_user(url="/v1/collections")
        collections = response.json()
        collections = [collection["name"] for collection in collections["data"]]

        assert "test-collection-private-admin" not in collections

    def test_delete_private_collection_with_user(self, client: TestClient, setup):
        _, _ = setup

        response = client.get_user(url="/v1/collections")
        collection_id = [collection["id"] for collection in response.json()["data"] if collection["name"] == "test-collection-private"][0]
        response = client.delete_user(url=f"/v1/collections/{collection_id}")
        assert response.status_code == 204

    def test_delete_public_collection_with_user(self, client: TestClient, setup):
        _, _ = setup

        response = client.get_user(url="/v1/collections")
        collection_id = [collection["id"] for collection in response.json()["data"] if collection["name"] == "test-collection-public"][0]
        response = client.delete_user(url=f"/v1/collections/{collection_id}")
        assert response.status_code == 403, response.text

    def test_delete_public_collection_with_admin(self, client: TestClient, setup):
        _, _ = setup

        response = client.get_user(url="/v1/collections")
        collection_id = [collection["id"] for collection in response.json()["data"] if collection["name"] == "test-collection-public"][0]
        response = client.delete_admin(url=f"/v1/collections/{collection_id}")
        assert response.status_code == 204, response.text

    def test_create_collection_with_empty_name(self, client: TestClient, setup):
        EMBEDDINGS_MODEL_ID, _ = setup

        params = {"name": " ", "model": EMBEDDINGS_MODEL_ID, "visibility": CollectionVisibility.PRIVATE}
        response = client.post_user(url="/v1/collections", json=params)
        assert response.status_code == 422, response.text

    def test_create_collection_with_description(self, client: TestClient, setup):
        EMBEDDINGS_MODEL_ID, _ = setup

        params = {
            "name": "test-description",
            "model": EMBEDDINGS_MODEL_ID,
            "visibility": CollectionVisibility.PRIVATE,
            "description": "test-description",
        }
        response = client.post_user(url="/v1/collections", json=params)
        assert response.status_code == 201, response.text

        # retrieve collection
        response = client.get_user(url="/v1/collections")
        assert response.status_code == 200, response.text
        description = [collection["description"] for collection in response.json()["data"] if collection["name"] == "test-description"][0]
        assert description == "test-description"
