import logging
import os

import pytest

from app.schemas.collections import CollectionVisibility
from app.schemas.documents import Documents
from app.utils.variables import MODEL_TYPE__EMBEDDINGS


@pytest.fixture(scope="module")
def setup(client):
    response = client.get_user(url="/v1/models", timeout=10)
    models = response.json()
    EMBEDDINGS_MODEL_ID = [model for model in models["data"] if model["type"] == MODEL_TYPE__EMBEDDINGS][0]["id"]
    logging.info(f"test embedings model ID: {EMBEDDINGS_MODEL_ID}")

    response = client.post_user(
        url="/v1/collections",
        json={"name": "test-collection-private", "model": EMBEDDINGS_MODEL_ID, "visibility": CollectionVisibility.PRIVATE},
    )
    assert response.status_code == 201
    PRIVATE_COLLECTION_ID = response.json()["id"]

    file_path = "app/tests/assets/json.json"
    files = {"file": (os.path.basename(file_path), open(file_path, "rb"), "application/json")}
    data = {"request": '{"collection": "%s"}' % PRIVATE_COLLECTION_ID}
    response = client.post_user(url="/v1/files", data=data, files=files)
    assert response.status_code == 201

    yield PRIVATE_COLLECTION_ID


@pytest.mark.usefixtures("client", "setup", "cleanup")
class TestDocuments:
    def test_get_documents(self, client, setup):
        PRIVATE_COLLECTION_ID = setup

        response = client.get_user(url=f"/v1/documents/{PRIVATE_COLLECTION_ID}")
        assert response.status_code == 200, response.text

        Documents(**response.json())  # test output format

    def test_collection_document_count(self, client, setup):
        PRIVATE_COLLECTION_ID = setup

        response = client.get_user(url="/v1/collections")
        collection = [collection for collection in response.json()["data"] if collection["id"] == PRIVATE_COLLECTION_ID][0]
        assert collection["documents"] == 2

    def test_delete_document(self, client, setup):
        PRIVATE_COLLECTION_ID = setup

        response = client.get_user(url=f"/v1/documents/{PRIVATE_COLLECTION_ID}")
        document_id = response.json()["data"][0]["id"]

        response = client.delete_user(url=f"/v1/documents/{PRIVATE_COLLECTION_ID}/{document_id}")
        assert response.status_code == 204, response.text

        response = client.get_user(url=f"/v1/documents/{PRIVATE_COLLECTION_ID}")
        documents = response.json()["data"]
        assert document_id not in [document["id"] for document in documents]
