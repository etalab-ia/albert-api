import logging
import os

from fastapi.testclient import TestClient
import pytest

from app.schemas.chunks import Chunks
from app.schemas.collections import CollectionVisibility
from app.utils.variables import MODEL_TYPE__EMBEDDINGS


@pytest.fixture(scope="module")
def setup(client: TestClient):
    # Get embedding model
    response = client.get_user(url="/v1/models", timeout=10)
    models = response.json()
    EMBEDDINGS_MODEL_ID = [model for model in models["data"] if model["type"] == MODEL_TYPE__EMBEDDINGS][0]["id"]
    logging.info(f"test embeddings model ID: {EMBEDDINGS_MODEL_ID}")

    # Create a collection
    response = client.post_user(
        url="/v1/collections", json={"name": "pytest", "model": EMBEDDINGS_MODEL_ID, "visibility": CollectionVisibility.PRIVATE}
    )
    assert response.status_code == 201
    COLLECTION_ID = response.json()["id"]

    # Upload a file
    file_path = "app/tests/assets/json.json"
    files = {"file": (os.path.basename(file_path), open(file_path, "rb"), "application/json")}
    data = {"request": '{"collection": "%s"}' % COLLECTION_ID}
    response = client.post_user(url="/v1/files", data=data, files=files)
    assert response.status_code == 201, response.text

    # Retrieve the document ID
    response = client.get_user(url=f"/v1/documents/{COLLECTION_ID}")
    assert response.status_code == 200, response.text
    DOCUMENT_ID = response.json()["data"][0]["id"]

    yield COLLECTION_ID, DOCUMENT_ID


@pytest.mark.usefixtures("client", "setup", "cleanup")
class TestChunks:
    def test_get_chunks(self, client: TestClient, setup):
        COLLECTION_ID, DOCUMENT_ID = setup
        response = client.get_user(url=f"/v1/chunks/{COLLECTION_ID}/{DOCUMENT_ID}")
        assert response.status_code == 200, response.text

        chunks = Chunks(**response.json())  # test output format

        assert len(chunks.data) > 0
        assert chunks.data[0].metadata.document_id == DOCUMENT_ID

    def test_delete_chunks(self, client: TestClient, setup):
        COLLECTION_ID, DOCUMENT_ID = setup
        response = client.delete_user(url=f"/v1/documents/{COLLECTION_ID}/{DOCUMENT_ID}")
        assert response.status_code == 204, response.text

        response = client.get_user(url=f"/v1/chunks/{COLLECTION_ID}/{DOCUMENT_ID}")
        data = response.json()["data"]

        assert len(data) == 0
