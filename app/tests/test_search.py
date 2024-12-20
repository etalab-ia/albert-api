import logging
import os
import uuid

import pytest

from app.schemas.search import Search, Searches
from app.utils.logging import logger
from app.utils.settings import settings
from app.utils.variables import EMBEDDINGS_MODEL_TYPE, INTERNET_COLLECTION_DISPLAY_ID, SEARCH_CLIENT_ELASTIC_TYPE


@pytest.fixture(scope="module")
def setup(args, session_user, session_admin):
    COLLECTION_ID = "pytest"

    # Get a embedding model
    response = session_admin.get(f"{args["base_url"]}/models")
    response = response.json()["data"]
    EMBEDDINGS_MODEL_ID = [model["id"] for model in response if model["type"] == EMBEDDINGS_MODEL_TYPE][0]
    logging.info(f"test model ID: {EMBEDDINGS_MODEL_ID}")

    # Create a collection
    response = session_user.post(f"{args["base_url"]}/collections", json={"name": "pytest-private", "model": EMBEDDINGS_MODEL_ID})
    COLLECTION_ID = response.json()["id"]

    # Upload the file to the collection
    file_path = "app/tests/assets/json.json"
    files = {"file": (os.path.basename(file_path), open(file_path, "rb"), "application/json")}
    data = {"request": '{"collection": "%s", "chunker": {"args": {"chunk_size": 1000}}}' % COLLECTION_ID}
    response = session_user.post(f"{args["base_url"]}/files", data=data, files=files)

    # Get document IDS
    response = session_user.get(f"{args["base_url"]}/documents/{COLLECTION_ID}")
    DOCUMENT_IDS = [response.json()["data"][0]["id"], response.json()["data"][1]["id"]]

    yield DOCUMENT_IDS, COLLECTION_ID


@pytest.mark.usefixtures("args", "session_user", "cleanup_collections", "setup")
class TestSearch:
    def test_search(self, args, session_user, setup):
        """Test the POST /search response status code."""

        DOCUMENT_IDS, COLLECTION_ID = setup
        data = {"prompt": "Qui est Albert ?", "collections": [COLLECTION_ID], "k": 3}
        response = session_user.post(f"{args["base_url"]}/search", json=data)
        assert response.status_code == 200, f"error: search request ({response.status_code} - {response.text})"

        searches = Searches(**response.json())
        assert isinstance(searches, Searches)
        assert all(isinstance(search, Search) for search in searches.data)

        search = searches.data[0]
        assert search.chunk.metadata.document_id in DOCUMENT_IDS

    def test_search_with_score_threshold(self, args, session_user, setup):
        """Test search with a score threshold."""

        _, COLLECTION_ID = setup
        data = {"prompt": "Erasmus", "collections": [COLLECTION_ID], "k": 3, "score_threshold": 0.5}
        response = session_user.post(f"{args["base_url"]}/search", json=data)
        assert response.status_code == 200

    def test_search_invalid_collection(self, args, session_user, setup):
        """Test search with an invalid collection."""

        _, _ = setup
        data = {"prompt": "Erasmus", "collections": [str(uuid.uuid4())], "k": 3}
        response = session_user.post(f"{args["base_url"]}/search", json=data)
        assert response.status_code == 404

    def test_search_invalid_k(self, args, session_user, setup):
        """Test search with an invalid k value."""

        _, COLLECTION_ID = setup
        data = {"prompt": "Erasmus", "collections": [COLLECTION_ID], "k": 0}
        response = session_user.post(f"{args["base_url"]}/search", json=data)
        assert response.status_code == 422

    def test_search_empty_prompt(self, args, session_user, setup):
        """Test search with an empty prompt."""

        _, COLLECTION_ID = setup
        data = {"prompt": "", "collections": [COLLECTION_ID], "k": 3}
        response = session_user.post(f"{args["base_url"]}/search", json=data)
        assert response.status_code == 422

    def test_search_internet_collection(self, args, session_user, setup):
        """Test search with the internet collection."""

        _, _ = setup
        data = {"prompt": "What is the largest planet in our solar system?", "collections": [INTERNET_COLLECTION_DISPLAY_ID], "k": 3}
        response = session_user.post(f"{args["base_url"]}/search", json=data)
        assert response.status_code == 200

        searches = Searches(**response.json())
        assert isinstance(searches, Searches)
        assert all(isinstance(search, Search) for search in searches.data)

        if len(searches.data) > 0:
            search = searches.data[0]
            assert search.chunk.metadata.document_name.startswith("http")
        else:
            logger.info("No internet search results, the DuckDuckGo rate limit may have been exceeded.")

    def test_lexical_search(self, args, session_user, setup):
        """Test lexical search."""

        _, COLLECTION_ID = setup
        data = {"prompt": "Qui est Albert ?", "collections": [COLLECTION_ID], "k": 3, "method": "lexical"}
        response = session_user.post(f"{args["base_url"]}/search", json=data)
        result = response.json()

        if settings.clients.search.type == SEARCH_CLIENT_ELASTIC_TYPE:
            assert response.status_code == 200
            assert "Albert" in result["data"][0]["chunk"]["content"]
        else:
            assert response.status_code == 400

    def test_semantic_search(self, args, session_user, setup):
        """Test semantic search."""

        _, COLLECTION_ID = setup
        data = {"prompt": "Qui sont les érudits ? ", "collections": [COLLECTION_ID], "k": 3, "method": "semantic"}
        response = session_user.post(f"{args["base_url"]}/search", json=data)
        result = response.json()
        assert response.status_code == 200
        assert "Erasmus" in result["data"][0]["chunk"]["content"] or "Erasmus" in result["data"][1]["chunk"]["content"]
        assert "Albert" in result["data"][0]["chunk"]["content"] or "Albert" in result["data"][1]["chunk"]["content"]

    def test_hybrid_search(self, args, session_user, setup):
        """Test hybrid search."""

        _, COLLECTION_ID = setup
        data = {"prompt": "Erasmus", "collections": [COLLECTION_ID], "k": 3, "method": "hybrid"}
        response = session_user.post(f"{args["base_url"]}/search", json=data)
        result = response.json()
        if settings.clients.search.type == SEARCH_CLIENT_ELASTIC_TYPE:
            assert response.status_code == 200
            assert "Erasmus" in result["data"][0]["chunk"]["content"]
        else:
            assert response.status_code == 400
