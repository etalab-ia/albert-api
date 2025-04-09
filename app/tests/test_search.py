import os
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from app.schemas.search import Search, Searches
from app.utils.logging import logger
from app.utils.variables import ENDPOINT__COLLECTIONS, ENDPOINT__DOCUMENTS, ENDPOINT__FILES, ENDPOINT__SEARCH


@pytest.fixture(scope="module")
def setup(client: TestClient):
    # Create a collection
    response = client.post_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}", json={"name": f"test_collection_{uuid4()}"})
    assert response.status_code == 201, response.text
    COLLECTION_ID = response.json()["id"]

    # Upload the file to the collection
    file_path = "app/tests/assets/json.json"
    with open(file_path, "rb") as file:
        files = {"file": (os.path.basename(file_path), file, "application/json")}
        data = {"request": '{"collection": "%s", "chunker": {"args": {"chunk_size": 1000}}}' % COLLECTION_ID}
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__FILES}", data=data, files=files)
        file.close()
    assert response.status_code == 201, response.text

    # Get document IDS
    response = client.get_without_permissions(url=f"/v1{ENDPOINT__DOCUMENTS}", params={"collection": COLLECTION_ID})
    assert response.status_code == 200, response.text
    DOCUMENT_IDS = [document["id"] for document in response.json()["data"]]

    yield COLLECTION_ID, DOCUMENT_IDS


@pytest.mark.usefixtures("client", "setup")
class TestSearch:
    def test_search(self, client: TestClient, setup):
        """Test the POST /search response status code."""
        COLLECTION_ID, DOCUMENT_IDS = setup

        data = {"prompt": "Qui est Albert ?", "collections": [COLLECTION_ID], "k": 3}
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__SEARCH}", json=data)
        assert response.status_code == 200, response.text

        searches = Searches(**response.json())  # test output format

        search = searches.data[0]
        assert search.chunk.metadata["document_id"] in DOCUMENT_IDS

    def test_search_with_score_threshold(self, client: TestClient, setup):
        """Test search with a score threshold."""
        COLLECTION_ID, DOCUMENT_IDS = setup
        data = {"prompt": "Erasmus", "collections": [COLLECTION_ID], "k": 3, "score_threshold": 0.5}
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__SEARCH}", json=data)
        assert response.status_code == 200, response.text

    def test_search_invalid_collection(self, client: TestClient, setup):
        """Test search with an invalid collection."""
        COLLECTION_ID, DOCUMENT_IDS = setup
        data = {"prompt": "Erasmus", "collections": [100], "k": 3}
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__SEARCH}", json=data)
        assert response.status_code == 404, response.text

    def test_search_invalid_k(self, client: TestClient, setup):
        """Test search with an invalid k value."""
        COLLECTION_ID, DOCUMENT_IDS = setup
        data = {"prompt": "Erasmus", "collections": [COLLECTION_ID], "k": 0}
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__SEARCH}", json=data)
        assert response.status_code == 422, response.text

    def test_search_empty_prompt(self, client: TestClient, setup):
        """Test search with an empty prompt."""
        COLLECTION_ID, DOCUMENT_IDS = setup
        data = {"prompt": "", "collections": [COLLECTION_ID], "k": 3}
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__SEARCH}", json=data)
        assert response.status_code == 422, response.text

    def test_web_search(self, client: TestClient, setup):
        """Test search with the web search."""
        COLLECTION_ID, DOCUMENT_IDS = setup

        data = {"prompt": "What is the largest planet in our solar system?", "web_search": True, "k": 3}
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__SEARCH}", json=data)
        assert response.status_code == 200, response.text

        searches = Searches(**response.json())
        assert isinstance(searches, Searches)
        assert all(isinstance(search, Search) for search in searches.data)

        if len(searches.data) > 0:
            search = searches.data[0]
            assert search.chunk.metadata["document_name"].startswith("http")
        else:
            logger.info("No web search results.")
