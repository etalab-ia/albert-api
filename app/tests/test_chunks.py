import logging
import os

import pytest

from app.utils.variables import EMBEDDINGS_MODEL_TYPE, PRIVATE_COLLECTION_TYPE
from app.schemas.chunks import Chunks, Chunk


@pytest.fixture(scope="module")
def setup(args, session_user):
    # Get embedding model
    response = session_user.get(f"{args['base_url']}/models", timeout=10)
    models = response.json()
    EMBEDDINGS_MODEL_ID = [model for model in models["data"] if model["type"] == EMBEDDINGS_MODEL_TYPE][0]["id"]
    logging.info(f"test embeddings model ID: {EMBEDDINGS_MODEL_ID}")

    # Create a collection
    response = session_user.post(
        f"{args['base_url']}/collections", json={"name": "pytest", "model": EMBEDDINGS_MODEL_ID, "type": PRIVATE_COLLECTION_TYPE}
    )
    assert response.status_code == 201
    COLLECTION_ID = response.json()["id"]

    # Upload a file
    file_path = "app/tests/assets/json.json"
    files = {"file": (os.path.basename(file_path), open(file_path, "rb"), "application/json")}
    data = {"request": '{"collection": "%s"}' % COLLECTION_ID}
    response = session_user.post(f"{args['base_url']}/files", data=data, files=files)
    assert response.status_code == 201

    # Retrieve the document ID
    response = session_user.get(f"{args['base_url']}/documents/{COLLECTION_ID}")
    assert response.status_code == 200
    DOCUMENT_ID = response.json()["data"][0]["id"]

    yield COLLECTION_ID, DOCUMENT_ID


@pytest.mark.usefixtures("args", "session_user", "setup", "cleanup_collections")
class TestChunks:
    def test_get_chunks(self, args, session_user, setup):
        COLLECTION_ID, DOCUMENT_ID = setup
        response = session_user.get(f"{args['base_url']}/chunks/{COLLECTION_ID}/{DOCUMENT_ID}")
        assert response.status_code == 200

        chunks = Chunks(**response.json())
        assert isinstance(chunks, Chunks)
        assert all(isinstance(chunk, Chunk) for chunk in chunks.data)

        assert len(chunks.data) > 0
        assert chunks.data[0].metadata.document_id == DOCUMENT_ID

    def test_delete_chunks(self, args, session_user, setup):
        COLLECTION_ID, DOCUMENT_ID = setup

        response = session_user.delete(f"{args['base_url']}/documents/{COLLECTION_ID}/{DOCUMENT_ID}")
        assert response.status_code == 204
        response = session_user.get(f"{args['base_url']}/chunks/{COLLECTION_ID}/{DOCUMENT_ID}")
        data = response.json()["data"]
        assert len(data) == 0
