import json
import os
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from app.schemas.collections import CollectionVisibility
from app.schemas.documents import Document, Documents


@pytest.fixture(scope="module")
def setup(client):
    response = client.post_without_permissions(
        url="/v1/collections",
        json={"name": f"test_collection_{str(uuid4())}", "visibility": CollectionVisibility.PRIVATE},
    )
    assert response.status_code == 201, response.text
    COLLECTION_ID = response.json()["id"]

    file_path = "app/tests/assets/json.json"
    files = {"file": (os.path.basename(file_path), open(file_path, "rb"), "application/json")}
    data = {"request": '{"collection": "%s"}' % COLLECTION_ID}
    response = client.post_without_permissions(url="/v1/files", data=data, files=files)
    assert response.status_code == 201, response.text

    DOCUMENT_ID = response.json()["id"]

    yield COLLECTION_ID, DOCUMENT_ID


@pytest.mark.usefixtures("client", "setup")
class TestDocuments:
    def test_get_document(self, client: TestClient, setup):
        COLLECTION_ID, DOCUMENT_ID = setup
        response = client.get_without_permissions(url="/v1/documents", params={"collection": COLLECTION_ID})
        assert response.status_code == 200, response.text

        documents = [document for document in response.json()["data"] if document["id"] == DOCUMENT_ID]
        assert len(documents) == 1

    def test_format_document(self, client: TestClient, setup):
        COLLECTION_ID, DOCUMENT_ID = setup

        response = client.get_without_permissions(url="/v1/documents")
        assert response.status_code == 200, response.text

        documents = response.json()
        Documents(**documents)  # test output format

        response = client.get_without_permissions(url="/v1/documents", params={"collection": COLLECTION_ID})
        assert response.status_code == 200, response.text

        documents = response.json()
        Documents(**documents)  # test output format

        response = client.get_without_permissions(url=f"/v1/documents/{DOCUMENT_ID}")
        assert response.status_code == 200, response.text

        document = response.json()
        Document(**document)  # test output format

    def test_collection_document_count(self, client: TestClient, setup):
        COLLECTION_ID, DOCUMENT_ID = setup

        with open("app/tests/assets/json.json", "r") as f:
            data = json.load(f)
            document_count = len(data)

        response = client.get_without_permissions(url="/v1/collections")
        collection = [collection for collection in response.json()["data"] if collection["id"] == COLLECTION_ID][0]
        assert collection["documents"] == document_count

    def test_delete_document(self, client: TestClient, setup):
        COLLECTION_ID, DOCUMENT_ID = setup

        response = client.delete_without_permissions(url=f"/v1/documents/{DOCUMENT_ID}")
        assert response.status_code == 204, response.text

        response = client.get_without_permissions(url="/v1/documents")
        documents = response.json()["data"]
        assert DOCUMENT_ID not in [document["id"] for document in documents]
