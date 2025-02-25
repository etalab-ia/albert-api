import logging
import os

import pytest

from app.utils.variables import MODEL_TYPE__EMBEDDINGS, COLLECTION_TYPE__PRIVATE
from app.schemas.chunks import Chunks, Chunk


@pytest.fixture(scope="module")
def setup(args, test_client):
    test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}
    # Get embedding model
    response = test_client.get("/v1/models", timeout=10)
    models = response.json()
    EMBEDDINGS_MODEL_ID = [model for model in models["data"] if model["type"] == MODEL_TYPE__EMBEDDINGS][0]["id"]
    logging.info(f"test embeddings model ID: {EMBEDDINGS_MODEL_ID}")

    # Create a collection
    response = test_client.post("/v1/collections", json={"name": "pytest", "model": EMBEDDINGS_MODEL_ID, "type": COLLECTION_TYPE__PRIVATE})
    assert response.status_code == 201
    COLLECTION_ID = response.json()["id"]

    # Upload a file
    file_path = "app/tests/assets/json.json"
    files = {"file": (os.path.basename(file_path), open(file_path, "rb"), "application/json")}
    data = {"request": '{"collection": "%s"}' % COLLECTION_ID}
    response = test_client.post("/v1/files", data=data, files=files)
    assert response.status_code == 201

    # Retrieve the document ID
    response = test_client.get(f"/v1/documents/{COLLECTION_ID}")
    assert response.status_code == 200
    DOCUMENT_ID = response.json()["data"][0]["id"]

    yield COLLECTION_ID, DOCUMENT_ID


@pytest.mark.usefixtures("args", "setup", "cleanup_collections", "test_client")
class TestChunks:
    def test_get_chunks(self, args, test_client, setup):
        COLLECTION_ID, DOCUMENT_ID = setup
        test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}
        response = test_client.get(f"/v1/chunks/{COLLECTION_ID}/{DOCUMENT_ID}")
        assert response.status_code == 200

        chunks = Chunks(**response.json())
        assert isinstance(chunks, Chunks)
        assert all(isinstance(chunk, Chunk) for chunk in chunks.data)

        assert len(chunks.data) > 0
        assert chunks.data[0].metadata.document_id == DOCUMENT_ID

    def test_delete_chunks(self, args, test_client, setup):
        COLLECTION_ID, DOCUMENT_ID = setup
        test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}
        response = test_client.delete(f"/v1/documents/{COLLECTION_ID}/{DOCUMENT_ID}")
        assert response.status_code == 204
        response = test_client.get(f"/v1/chunks/{COLLECTION_ID}/{DOCUMENT_ID}")
        data = response.json()["data"]
        assert len(data) == 0
