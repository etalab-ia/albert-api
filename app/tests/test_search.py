import logging
import os
import uuid

import pytest

from app.schemas.search import Search, Searches
from app.utils.logging import logger
from app.utils.variables import MODEL_TYPE__EMBEDDINGS, COLLECTION_DISPLAY_ID__INTERNET


@pytest.fixture(scope="module")
def setup(args, test_client):
    COLLECTION_ID = "pytest"
    test_client.headers = {"Authorization": f"Bearer {args['api_key_admin']}"}

    # Get a embedding model
    response = test_client.get(f"{args['base_url']}/models")
    response = response.json()["data"]
    EMBEDDINGS_MODEL_ID = [model["id"] for model in response if model["type"] == MODEL_TYPE__EMBEDDINGS][0]
    logging.info(f"test model ID: {EMBEDDINGS_MODEL_ID}")

    test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}
    # Create a collection
    response = test_client.post(f"{args['base_url']}/collections", json={"name": "pytest-private", "model": EMBEDDINGS_MODEL_ID})
    COLLECTION_ID = response.json()["id"]

    # Upload the file to the collection
    file_path = "app/tests/assets/json.json"
    files = {"file": (os.path.basename(file_path), open(file_path, "rb"), "application/json")}
    data = {"request": '{"collection": "%s", "chunker": {"args": {"chunk_size": 1000}}}' % COLLECTION_ID}
    response = test_client.post(f"{args['base_url']}/files", data=data, files=files)

    # Get document IDS
    response = test_client.get(f"{args['base_url']}/documents/{COLLECTION_ID}")
    DOCUMENT_IDS = [response.json()["data"][0]["id"], response.json()["data"][1]["id"]]

    yield DOCUMENT_IDS, COLLECTION_ID


@pytest.mark.usefixtures("args", "cleanup_collections", "setup", "test_client")
class TestSearch:
    def test_search(self, args, test_client, setup):
        """Test the POST /search response status code."""
        DOCUMENT_IDS, COLLECTION_ID = setup
        test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}
        data = {"prompt": "Qui est Albert ?", "collections": [COLLECTION_ID], "k": 3}
        response = test_client.post(f"{args['base_url']}/search", json=data)
        assert response.status_code == 200, f"error: search request ({response.status_code} - {response.text})"

        searches = Searches(**response.json())
        assert isinstance(searches, Searches)
        assert all(isinstance(search, Search) for search in searches.data)

        search = searches.data[0]
        assert search.chunk.metadata.document_id in DOCUMENT_IDS

    def test_search_with_score_threshold(self, args, test_client, setup):
        """Test search with a score threshold."""
        _, COLLECTION_ID = setup
        test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}
        data = {"prompt": "Erasmus", "collections": [COLLECTION_ID], "k": 3, "score_threshold": 0.5}
        response = test_client.post(f"{args['base_url']}/search", json=data)
        assert response.status_code == 200

    def test_search_invalid_collection(self, args, test_client, setup):
        """Test search with an invalid collection."""
        _, _ = setup
        test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}
        data = {"prompt": "Erasmus", "collections": [str(uuid.uuid4())], "k": 3}
        response = test_client.post(f"{args['base_url']}/search", json=data)
        assert response.status_code == 404

    def test_search_invalid_k(self, args, test_client, setup):
        """Test search with an invalid k value."""
        _, COLLECTION_ID = setup
        test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}
        data = {"prompt": "Erasmus", "collections": [COLLECTION_ID], "k": 0}
        response = test_client.post(f"{args['base_url']}/search", json=data)
        assert response.status_code == 422

    def test_search_empty_prompt(self, args, test_client, setup):
        """Test search with an empty prompt."""
        _, COLLECTION_ID = setup
        test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}
        data = {"prompt": "", "collections": [COLLECTION_ID], "k": 3}
        response = test_client.post(f"{args['base_url']}/search", json=data)
        assert response.status_code == 422

    def test_search_internet_collection(self, args, test_client, setup):
        """Test search with the internet collection."""
        _, _ = setup
        test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}
        data = {"prompt": "What is the largest planet in our solar system?", "collections": [COLLECTION_DISPLAY_ID__INTERNET], "k": 3}
        response = test_client.post(f"{args['base_url']}/search", json=data)
        assert response.status_code == 200

        searches = Searches(**response.json())
        assert isinstance(searches, Searches)
        assert all(isinstance(search, Search) for search in searches.data)

        if len(searches.data) > 0:
            search = searches.data[0]
            assert search.chunk.metadata.document_name.startswith("http")
        else:
            logger.info("No internet search results, the DuckDuckGo rate limit may have been exceeded.")

    # @TODO: Add test after elasticsearch migration
    # def test_lexical_search(self, args, test_client, setup):
    #     """Test lexical search."""

    #     _, COLLECTION_ID = setup
    #     data = {"prompt": "Qui est Albert ?", "collections": [COLLECTION_ID], "k": 3, "method": "lexical"}
    #     response = test_client.post(f"{args['base_url']}/search", json=data)
    #     result = response.json()

    #     if settings.databases.type == DATABASE_TYPE__ELASTIC:
    #         assert response.status_code == 200
    #         assert "Albert" in result["data"][0]["chunk"]["content"]
    #     else:
    #         assert response.status_code == 400

    def test_semantic_search(self, args, test_client, setup):
        """Test semantic search."""
        _, COLLECTION_ID = setup
        test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}
        data = {"prompt": "Qui sont les érudits ? ", "collections": [COLLECTION_ID], "k": 3, "method": "semantic"}
        response = test_client.post(f"{args['base_url']}/search", json=data)
        result = response.json()
        assert response.status_code == 200
        assert "Erasmus" in result["data"][0]["chunk"]["content"] or "Erasmus" in result["data"][1]["chunk"]["content"]
        assert "Albert" in result["data"][0]["chunk"]["content"] or "Albert" in result["data"][1]["chunk"]["content"]

    # @TODO: Add test after elasticsearch migration
    # def test_hybrid_search(self, args, test_client, setup):
    #     """Test hybrid search."""

    #     _, COLLECTION_ID = setup
    #     data = {"prompt": "Erasmus", "collections": [COLLECTION_ID], "k": 3, "method": "hybrid"}
    #     response = test_client.post(f"{args['base_url']}/search", json=data)
    #     result = response.json()
    #     if settings.clients.search.type == DATABASE_TYPE__ELASTIC:
    #         assert response.status_code == 200
    #         assert "Erasmus" in result["data"][0]["chunk"]["content"]
    #     else:
    #         assert response.status_code == 400
