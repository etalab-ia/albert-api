import logging
import os
import uuid

from fastapi.testclient import TestClient
import pytest

from app.schemas.models import ModelType
from app.schemas.search import Search, Searches
from app.utils.logging import logger
from app.utils.variables import COLLECTION_DISPLAY_ID__INTERNET


@pytest.fixture(scope="module")
def setup(client: TestClient):
    COLLECTION_ID = "pytest"

    # Get a embedding model
    response = client.get_user(url="/v1/models")
    response = response.json()["data"]
    EMBEDDINGS_MODEL_ID = [model["id"] for model in response if model["type"] == ModelType.TEXT_EMBEDDINGS_INFERENCE][0]
    logging.info(f"test model ID: {EMBEDDINGS_MODEL_ID}")

    # Create a collection
    response = client.post_user(url="/v1/collections", json={"name": "test-collection-private", "model": EMBEDDINGS_MODEL_ID})
    COLLECTION_ID = response.json()["id"]

    # Upload the file to the collection
    file_path = "app/tests/assets/json.json"
    files = {"file": (os.path.basename(file_path), open(file_path, "rb"), "application/json")}
    data = {"request": '{"collection": "%s", "chunker": {"args": {"chunk_size": 1000}}}' % COLLECTION_ID}
    response = client.post_user(url="/v1/files", data=data, files=files)

    # Get document IDS
    response = client.get_user(url=f"/v1/documents/{COLLECTION_ID}")
    DOCUMENT_IDS = [response.json()["data"][0]["id"], response.json()["data"][1]["id"]]

    yield DOCUMENT_IDS, COLLECTION_ID


@pytest.mark.usefixtures("client", "setup", "cleanup")
class TestSearch:
    def test_search(self, client: TestClient, setup):
        """Test the POST /search response status code."""
        DOCUMENT_IDS, COLLECTION_ID = setup

        data = {"prompt": "Qui est Albert ?", "collections": [COLLECTION_ID], "k": 3}
        response = client.post_user(url="/v1/search", json=data)
        assert response.status_code == 200, response.text

        searches = Searches(**response.json())  # test output format

        search = searches.data[0]
        assert search.chunk.metadata["document_id"] in DOCUMENT_IDS

    def test_search_with_score_threshold(self, client: TestClient, setup):
        """Test search with a score threshold."""
        _, COLLECTION_ID = setup
        data = {"prompt": "Erasmus", "collections": [COLLECTION_ID], "k": 3, "score_threshold": 0.5}
        response = client.post_user(url="/v1/search", json=data)
        assert response.status_code == 200, response.text

    def test_search_invalid_collection(self, client: TestClient, setup):
        """Test search with an invalid collection."""
        _, _ = setup
        data = {"prompt": "Erasmus", "collections": [str(uuid.uuid4())], "k": 3}
        response = client.post_user(url="/v1/search", json=data)
        assert response.status_code == 404, response.text

    def test_search_invalid_k(self, client: TestClient, setup):
        """Test search with an invalid k value."""
        _, COLLECTION_ID = setup
        data = {"prompt": "Erasmus", "collections": [COLLECTION_ID], "k": 0}
        response = client.post_user(url="/v1/search", json=data)
        assert response.status_code == 422, response.text

    def test_search_empty_prompt(self, client: TestClient, setup):
        """Test search with an empty prompt."""
        _, COLLECTION_ID = setup
        data = {"prompt": "", "collections": [COLLECTION_ID], "k": 3}
        response = client.post_user(url="/v1/search", json=data)
        assert response.status_code == 422, response.text

    def test_search_internet_collection(self, client: TestClient, setup):
        """Test search with the internet collection."""
        _, _ = setup
        data = {"prompt": "What is the largest planet in our solar system?", "collections": [COLLECTION_DISPLAY_ID__INTERNET], "k": 3}
        response = client.post_user(url="/v1/search", json=data)
        assert response.status_code == 200, response.text

        searches = Searches(**response.json())
        assert isinstance(searches, Searches)
        assert all(isinstance(search, Search) for search in searches.data)

        if len(searches.data) > 0:
            search = searches.data[0]
            assert search.chunk.metadata["document_name"].startswith("http")
        else:
            logger.info("No internet search results, the DuckDuckGo rate limit may have been exceeded.")

    # @TODO: Add test after elasticsearch migration
    # def test_lexical_search(self, client, setup):
    #     """Test lexical search."""

    #     _, COLLECTION_ID = setup
    #     data = {"prompt": "Qui est Albert ?", "collections": [COLLECTION_ID], "k": 3, "method": "lexical"}
    #     response = test_client.post("/v1/search", json=data)
    #     result = response.json()

    #     if settings.databases.type == DATABASE_TYPE__ELASTIC:
    #         assert response.status_code == 200
    #         assert "Albert" in result["data"][0]["chunk"]["content"]
    #     else:
    #         assert response.status_code == 400

    def test_semantic_search(self, client: TestClient, setup):
        """Test semantic search."""
        _, COLLECTION_ID = setup
        data = {"prompt": "Qui sont les érudits ? ", "collections": [COLLECTION_ID], "k": 3, "method": "semantic"}
        response = client.post_user(url="/v1/search", json=data)
        assert response.status_code == 200, response.text

        result = response.json()
        assert "Erasmus" in result["data"][0]["chunk"]["content"] or "Erasmus" in result["data"][1]["chunk"]["content"]
        assert "Albert" in result["data"][0]["chunk"]["content"] or "Albert" in result["data"][1]["chunk"]["content"]

    # @TODO: Add test after elasticsearch migration
    # def test_hybrid_search(self, args, test_client, setup):
    #     """Test hybrid search."""

    #     _, COLLECTION_ID = setup
    #     data = {"prompt": "Erasmus", "collections": [COLLECTION_ID], "k": 3, "method": "hybrid"}
    #     response = test_client.post("/v1/search", json=data)
    #     result = response.json()
    #     if settings.clients.search.type == DATABASE_TYPE__ELASTIC:
    #         assert response.status_code == 200
    #         assert "Erasmus" in result["data"][0]["chunk"]["content"]
    #     else:
    #         assert response.status_code == 400
