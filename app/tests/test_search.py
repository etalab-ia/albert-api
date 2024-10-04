import logging
import os
import uuid

import pytest

from app.schemas.search import Search, Searches
from app.utils.variables import EMBEDDINGS_MODEL_TYPE, INTERNET_COLLECTION_ID


@pytest.fixture(scope="module")
def setup(args, session_user):
    COLLECTION_ID = "pytest"

    # Get a embedding model
    response = session_user.get(f"{args["base_url"]}/models")
    response = response.json()["data"]
    EMBEDDINGS_MODEL_ID = [model["id"] for model in response if model["type"] == EMBEDDINGS_MODEL_TYPE][0]
    logging.info(f"test model ID: {EMBEDDINGS_MODEL_ID}")

    # Create a collection
    response = session_user.post(f"{args["base_url"]}/collections", json={"name": "pytest-private", "model": EMBEDDINGS_MODEL_ID})
    COLLECTION_ID = response.json()["id"]

    # Upload the file to the collection
    file_path = "app/tests/assets/pdf.pdf"
    files = {"file": (os.path.basename(file_path), open(file_path, "rb"), "application/pdf")}
    data = {"request": '{"collection": "%s", "chunker": {"args": {"chunk_size": 1000}}}' % COLLECTION_ID}
    response = session_user.post(f"{args["base_url"]}/files", data=data, files=files)

    # Get document ID
    response = session_user.get(f"{args["base_url"]}/documents/{COLLECTION_ID}")
    DOCUMENT_ID = response.json()["data"][0]["id"]

    yield DOCUMENT_ID, COLLECTION_ID


@pytest.mark.usefixtures("args", "session_user", "cleanup_collections", "setup")
class TestSearch:
    def test_search(self, args, session_user, setup):
        """Test the POST /search response status code."""

        DOCUMENT_ID, COLLECTION_ID = setup
        data = {"prompt": "test query", "collections": [COLLECTION_ID], "k": 3}
        response = session_user.post(f"{args["base_url"]}/search", json=data)
        assert response.status_code == 200, f"error: search request ({response.status_code} - {response.text})"

        searches = Searches(**response.json())
        assert isinstance(searches, Searches)
        assert all(isinstance(search, Search) for search in searches.data)

        search = searches.data[0]
        assert search.chunk.metadata.document_id == DOCUMENT_ID

    def test_search_with_score_threshold(self, args, session_user, setup):
        """Test search with a score threshold."""

        _, COLLECTION_ID = setup
        data = {"prompt": "test query", "collections": [COLLECTION_ID], "k": 3, "score_threshold": 0.5}
        response = session_user.post(f"{args["base_url"]}/search", json=data)
        assert response.status_code == 200

    def test_search_invalid_collection(self, args, session_user, setup):
        """Test search with an invalid collection."""

        _, _ = setup
        data = {"prompt": "test query", "collections": [str(uuid.uuid4())], "k": 3}
        response = session_user.post(f"{args["base_url"]}/search", json=data)
        assert response.status_code == 400

    def test_search_invalid_k(self, args, session_user, setup):
        """Test search with an invalid k value."""

        _, COLLECTION_ID = setup
        data = {"prompt": "test query", "collections": [COLLECTION_ID], "k": 0}
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
        data = {"prompt": "Quelle est la capitale de la France ?", "collections": [INTERNET_COLLECTION_ID], "k": 3}
        response = session_user.post(f"{args["base_url"]}/search", json=data)
        assert response.status_code == 200

        searches = Searches(**response.json())
        assert isinstance(searches, Searches)
        assert all(isinstance(search, Search) for search in searches.data)

        search = searches.data[0]
        assert search.chunk.metadata.document_name.startswith("http")
