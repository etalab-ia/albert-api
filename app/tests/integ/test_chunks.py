import os
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from app.schemas.chunks import Chunks
from app.schemas.collections import CollectionVisibility
from app.utils.variables import ENDPOINT__CHUNKS, ENDPOINT__COLLECTIONS, ENDPOINT__DOCUMENTS, ENDPOINT__FILES


@pytest.fixture(scope="module")
def setup(client: TestClient, record_with_vcr):
    # Create a collection
    response = client.post_without_permissions(
        url=f"/v1{ENDPOINT__COLLECTIONS}",
        json={"name": f"test_collection_{uuid4()}", "visibility": CollectionVisibility.PRIVATE},
    )
    assert response.status_code == 201
    COLLECTION_ID = response.json()["id"]

    # Upload a file
    file_path = "app/tests/integ/assets/json.json"
    with open(file_path, "rb") as file:
        files = {"file": (os.path.basename(file_path), file, "application/json")}
        data = {"request": '{"collection": "%s"}' % COLLECTION_ID}
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__FILES}", data=data, files=files)
        file.close()
    assert response.status_code == 201, response.text

    # Retrieve the document ID
    response = client.get_without_permissions(url=f"/v1{ENDPOINT__DOCUMENTS}", params={"collection": COLLECTION_ID})
    assert response.status_code == 200, response.text
    DOCUMENT_ID = response.json()["data"][0]["id"]

    yield COLLECTION_ID, DOCUMENT_ID


@pytest.mark.usefixtures("client", "setup")
class TestChunks:
    def test_get_chunks(self, client: TestClient, setup):
        COLLECTION_ID, DOCUMENT_ID = setup
        response = client.get_without_permissions(url=f"/v1{ENDPOINT__CHUNKS}/{DOCUMENT_ID}")
        assert response.status_code == 200, response.text

        chunks = Chunks(**response.json())  # test output format

        assert len(chunks.data) > 0
        assert chunks.data[0].metadata["document_id"] == DOCUMENT_ID

    def test_delete_chunks(self, client: TestClient, setup):
        COLLECTION_ID, DOCUMENT_ID = setup
        response = client.delete_without_permissions(url=f"/v1{ENDPOINT__DOCUMENTS}/{DOCUMENT_ID}")
        assert response.status_code == 204, response.text

        response = client.get_without_permissions(url=f"/v1{ENDPOINT__CHUNKS}/{DOCUMENT_ID}")
        assert response.status_code == 404, response.text

    def test_chunk_not_found(self, client: TestClient, setup):
        COLLECTION_ID, DOCUMENT_ID = setup
        document_id = 1000
        response = client.get_without_permissions(url=f"/v1{ENDPOINT__CHUNKS}/{document_id}")
        assert response.status_code == 404, response.text
