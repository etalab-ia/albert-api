import json
import os
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from app.schemas.collections import CollectionVisibility
from app.schemas.documents import Document, Documents
from app.utils.variables import ENDPOINT__COLLECTIONS, ENDPOINT__DOCUMENTS, ENDPOINT__FILES


@pytest.fixture(scope="module")
def setup(client, record_with_vcr):
    response = client.post_without_permissions(
        url=f"/v1{ENDPOINT__COLLECTIONS}",
        json={"name": f"test_collection_{str(uuid4())}", "visibility": CollectionVisibility.PRIVATE},
    )
    assert response.status_code == 201, response.text
    COLLECTION_ID = response.json()["id"]

    file_path = "app/tests/integ/assets/json.json"
    with open(file_path, "rb") as file:
        files = {"file": (os.path.basename(file_path), file, "application/json")}
        data = {"request": '{"collection": "%s"}' % COLLECTION_ID}
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__FILES}", data=data, files=files)
        file.close()
    assert response.status_code == 201, response.text

    DOCUMENT_ID = response.json()["id"]

    yield COLLECTION_ID, DOCUMENT_ID


@pytest.mark.usefixtures("client", "setup")
class TestDocuments:
    def test_get_document(self, client: TestClient, setup):
        COLLECTION_ID, DOCUMENT_ID = setup
        response = client.get_without_permissions(url=f"/v1{ENDPOINT__DOCUMENTS}", params={"collection": COLLECTION_ID})
        assert response.status_code == 200, response.text

        documents = [document for document in response.json()["data"] if document["id"] == DOCUMENT_ID]
        assert len(documents) == 1

    def test_format_document(self, client: TestClient, setup):
        COLLECTION_ID, DOCUMENT_ID = setup

        response = client.get_without_permissions(url=f"/v1{ENDPOINT__DOCUMENTS}")
        assert response.status_code == 200, response.text

        documents = response.json()
        Documents(**documents)  # test output format

        response = client.get_without_permissions(url=f"/v1{ENDPOINT__DOCUMENTS}", params={"collection": COLLECTION_ID})
        assert response.status_code == 200, response.text

        documents = response.json()
        Documents(**documents)  # test output format

        response = client.get_without_permissions(url=f"/v1{ENDPOINT__DOCUMENTS}/{DOCUMENT_ID}")
        assert response.status_code == 200, response.text

        document = response.json()
        Document(**document)  # test output format

    def test_collection_document_count(self, client: TestClient, setup):
        COLLECTION_ID, DOCUMENT_ID = setup

        with open("app/tests/integ/assets/json.json", "r") as f:
            data = json.load(f)
            document_count = len(data)

        response = client.get_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}/{COLLECTION_ID}")
        collection = response.json()
        assert collection["documents"] == document_count

    def test_delete_document(self, client: TestClient, setup):
        COLLECTION_ID, DOCUMENT_ID = setup

        response = client.delete_without_permissions(url=f"/v1{ENDPOINT__DOCUMENTS}/{DOCUMENT_ID}")
        assert response.status_code == 204, response.text

        response = client.get_without_permissions(url=f"/v1{ENDPOINT__DOCUMENTS}")
        documents = response.json()["data"]
        assert DOCUMENT_ID not in [document["id"] for document in documents]

    def test_create_document_simple(self, client: TestClient, setup):
        """Simple test for creating a document directly via the documents endpoint - should expose a bug."""
        COLLECTION_ID, _ = setup

        # Try to create a document directly using the documents endpoint
        file_path = "app/tests/integ/assets/pdf.pdf"
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/pdf")}
            data = {"collection": COLLECTION_ID}

            response = client.post_without_permissions(url=f"/v1{ENDPOINT__DOCUMENTS}", data=data, files=files)

        # This should work but will likely fail due to the bug
        assert response.status_code == 201, f"Expected 201 but got {response.status_code}: {response.text}"

        # Verify the response contains the document ID
        response_data = response.json()
        assert "id" in response_data, f"Response missing 'id' field: {response_data}"
        assert isinstance(response_data["id"], int), f"Document ID should be integer, got: {type(response_data['id'])}"
