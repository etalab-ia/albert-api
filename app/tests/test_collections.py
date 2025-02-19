import logging

import pytest

from app.schemas.collections import Collection, Collections
from app.clients._authenticationclient import AuthenticationClient
from app.utils.variables import (
    MODEL_TYPE__EMBEDDINGS,
    MODEL_TYPE__LANGUAGE,
    COLLECTION_TYPE__PRIVATE,
    COLLECTION_TYPE__PUBLIC,
)


@pytest.fixture(scope="module")
def setup(args, session_user):
    USER = AuthenticationClient.api_key_to_user_id(input=args["api_key_user"])
    ADMIN = AuthenticationClient.api_key_to_user_id(input=args["api_key_admin"])
    logging.info(f"test user ID: {USER}")
    logging.info(f"test admin ID: {ADMIN}")

    response = session_user.get(f"{args["base_url"]}/models", timeout=10)
    models = response.json()
    EMBEDDINGS_MODEL_ID = [model for model in models["data"] if model["type"] == MODEL_TYPE__EMBEDDINGS][0]["id"]
    LANGUAGE_MODEL_ID = [model for model in models["data"] if model["type"] == MODEL_TYPE__LANGUAGE][0]["id"]
    logging.info(f"test embedings model ID: {EMBEDDINGS_MODEL_ID}")
    logging.info(f"test language model ID: {LANGUAGE_MODEL_ID}")

    PUBLIC_COLLECTION_NAME = "pytest-public"
    PRIVATE_COLLECTION_NAME = "pytest-private"

    yield PUBLIC_COLLECTION_NAME, PRIVATE_COLLECTION_NAME, ADMIN, USER, EMBEDDINGS_MODEL_ID, LANGUAGE_MODEL_ID


@pytest.mark.usefixtures("args", "session_user", "session_admin", "setup", "cleanup_collections")
class TestCollections:
    def test_create_private_collection_with_user(self, args, session_user, setup):
        _, PRIVATE_COLLECTION_NAME, _, _, EMBEDDINGS_MODEL_ID, _ = setup

        params = {"name": PRIVATE_COLLECTION_NAME, "model": EMBEDDINGS_MODEL_ID, "type": COLLECTION_TYPE__PRIVATE}
        response = session_user.post(f"{args["base_url"]}/collections", json=params)
        assert response.status_code == 201
        assert "id" in response.json().keys()

    def test_create_public_collection_with_user(self, args, session_user, setup):
        PUBLIC_COLLECTION_NAME, _, _, _, EMBEDDINGS_MODEL_ID, _ = setup

        params = {"name": PUBLIC_COLLECTION_NAME, "model": EMBEDDINGS_MODEL_ID, "type": COLLECTION_TYPE__PUBLIC}
        response = session_user.post(f"{args["base_url"]}/collections", json=params)
        assert response.status_code == 403

    def test_create_public_collection_with_admin(self, args, session_admin, setup):
        PUBLIC_COLLECTION_NAME, _, _, _, EMBEDDINGS_MODEL_ID, _ = setup

        params = {"name": PUBLIC_COLLECTION_NAME, "model": EMBEDDINGS_MODEL_ID, "type": COLLECTION_TYPE__PUBLIC}
        response = session_admin.post(f"{args["base_url"]}/collections", json=params)
        assert response.status_code == 201
        assert "id" in response.json().keys()

    def test_create_private_collection_with_language_model_with_user(self, args, session_user, setup):
        _, PRIVATE_COLLECTION_NAME, _, _, _, LANGUAGE_MODEL_ID = setup

        params = {"name": PRIVATE_COLLECTION_NAME, "model": LANGUAGE_MODEL_ID, "type": COLLECTION_TYPE__PRIVATE}
        response = session_user.post(f"{args["base_url"]}/collections", json=params)
        assert response.status_code == 422

    def test_create_private_collection_with_unknown_model_with_user(self, args, session_user, setup):
        _, PRIVATE_COLLECTION_NAME, _, _, _, _ = setup

        params = {"name": PRIVATE_COLLECTION_NAME, "model": "unknown-model", "type": COLLECTION_TYPE__PRIVATE}
        response = session_user.post(f"{args["base_url"]}/collections", json=params)
        assert response.status_code == 404

    def test_get_collections(self, args, session_user, setup):
        PUBLIC_COLLECTION_NAME, PRIVATE_COLLECTION_NAME, ADMIN, USER, _, _ = setup

        response = session_user.get(f"{args["base_url"]}/collections")
        assert response.status_code == 200

        collections = response.json()
        collections["data"] = [Collection(**collection) for collection in collections["data"]]
        collections = Collections(**collections)

        assert isinstance(collections, Collections)
        assert all(isinstance(collection, Collection) for collection in collections.data)

        assert "collections" not in [collection.id for collection in collections.data]
        assert "documents" not in [collection.id for collection in collections.data]

        assert PRIVATE_COLLECTION_NAME in [collection.name for collection in collections.data]
        assert PUBLIC_COLLECTION_NAME in [collection.name for collection in collections.data]

        assert [collection.user for collection in collections.data if collection.name == PRIVATE_COLLECTION_NAME][0] == USER
        assert [collection.user for collection in collections.data if collection.name == PUBLIC_COLLECTION_NAME][0] == ADMIN

    def test_get_collection_of_other_user(self, args, session_admin, setup):
        _, PRIVATE_COLLECTION_NAME, _, _, _, _ = setup

        response = session_admin.get(f"{args["base_url"]}/collections")
        collections = response.json()
        collections = [collection["name"] for collection in collections["data"]]

        assert PRIVATE_COLLECTION_NAME not in collections

    def test_delete_private_collection_with_user(self, args, session_user, setup):
        _, PRIVATE_COLLECTION_NAME, _, _, _, _ = setup

        response = session_user.get(f"{args["base_url"]}/collections")
        collection_id = [collection["id"] for collection in response.json()["data"] if collection["name"] == PRIVATE_COLLECTION_NAME][0]
        response = session_user.delete(f"{args["base_url"]}/collections/{collection_id}")
        assert response.status_code == 204

    def test_delete_public_collection_with_user(self, args, session_user, setup):
        PUBLIC_COLLECTION_NAME, _, _, _, _, _ = setup

        response = session_user.get(f"{args["base_url"]}/collections")
        collection_id = [collection["id"] for collection in response.json()["data"] if collection["name"] == PUBLIC_COLLECTION_NAME][0]
        response = session_user.delete(f"{args["base_url"]}/collections/{collection_id}")
        assert response.status_code == 403

    def test_delete_public_collection_with_admin(self, args, session_admin, setup):
        PUBLIC_COLLECTION_NAME, _, _, _, _, _ = setup

        response = session_admin.get(f"{args["base_url"]}/collections")
        collection_id = [collection["id"] for collection in response.json()["data"] if collection["name"] == PUBLIC_COLLECTION_NAME][0]
        response = session_admin.delete(f"{args["base_url"]}/collections/{collection_id}")
        assert response.status_code == 204

    def test_create_collection_with_empty_name(self, args, session_user, setup):
        _, _, _, _, EMBEDDINGS_MODEL_ID, _ = setup

        params = {"name": " ", "model": EMBEDDINGS_MODEL_ID, "type": COLLECTION_TYPE__PRIVATE}
        response = session_user.post(f"{args["base_url"]}/collections", json=params)
        assert response.status_code == 422

    def test_create_collection_with_description(self, args, session_user, setup):
        _, _, _, _, EMBEDDINGS_MODEL_ID, _ = setup

        params = {"name": "pytest-description", "model": EMBEDDINGS_MODEL_ID, "type": COLLECTION_TYPE__PRIVATE, "description": "pytest-description"}
        response = session_user.post(f"{args["base_url"]}/collections", json=params)
        assert response.status_code == 201

        # retrieve collection
        response = session_user.get(f"{args["base_url"]}/collections")
        assert response.status_code == 200
        description = [collection["description"] for collection in response.json()["data"] if collection["name"] == "pytest-description"][0]
        assert description == "pytest-description"
