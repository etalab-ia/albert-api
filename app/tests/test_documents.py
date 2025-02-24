import logging
import os

import pytest


from app.schemas.documents import Documents
from app.utils.variables import MODEL_TYPE__EMBEDDINGS, COLLECTION_TYPE__PRIVATE


@pytest.fixture(scope="module")
def setup(args, session_user):
    response = session_user.get(f"{args["base_url"]}/models", timeout=10)
    models = response.json()
    EMBEDDINGS_MODEL_ID = [model for model in models["data"] if model["type"] == MODEL_TYPE__EMBEDDINGS][0]["id"]
    logging.info(f"test embedings model ID: {EMBEDDINGS_MODEL_ID}")

    response = session_user.post(
        f"{args["base_url"]}/collections", json={"name": "pytest-private", "model": EMBEDDINGS_MODEL_ID, "type": COLLECTION_TYPE__PRIVATE}
    )
    assert response.status_code == 201
    PRIVATE_COLLECTION_ID = response.json()["id"]

    file_path = "app/tests/assets/json.json"
    files = {"file": (os.path.basename(file_path), open(file_path, "rb"), "application/json")}
    data = {"request": '{"collection": "%s"}' % PRIVATE_COLLECTION_ID}
    session_user.post(f"{args["base_url"]}/files", data=data, files=files)

    yield PRIVATE_COLLECTION_ID


@pytest.mark.usefixtures("args", "session_user", "setup", "cleanup_collections")
class TestDocuments:
    def test_get_documents(self, args, session_user, setup):
        PRIVATE_COLLECTION_ID = setup

        response = session_user.get(f"{args["base_url"]}/documents/{PRIVATE_COLLECTION_ID}")
        assert response.status_code == 200, f"error: upload file ({response.status_code} - {response.text})"

        response_json = response.json()
        documents = Documents(**response_json)
        assert isinstance(documents, Documents)

    def test_collection_document_count(self, args, session_user, setup):
        PRIVATE_COLLECTION_ID = setup

        response = session_user.get(f"{args["base_url"]}/collections")
        collection = [collection for collection in response.json()["data"] if collection["id"] == PRIVATE_COLLECTION_ID][0]
        assert collection["documents"] == 2

    def test_delete_document(self, args, session_user, setup):
        PRIVATE_COLLECTION_ID = setup

        response = session_user.get(f"{args["base_url"]}/documents/{PRIVATE_COLLECTION_ID}")
        document_id = response.json()["data"][0]["id"]

        response = session_user.delete(f"{args["base_url"]}/documents/{PRIVATE_COLLECTION_ID}/{document_id}")
        assert response.status_code == 204, f"error: delete file ({response.status_code} - {response.text})"

        response = session_user.get(f"{args["base_url"]}/documents/{PRIVATE_COLLECTION_ID}")
        documents = response.json()["data"]
        assert document_id not in [document["id"] for document in documents]
