import logging
import os

import pytest

from app.utils.variables import EMBEDDINGS_MODEL_TYPE
from app.schemas.search import Search, Searches


@pytest.fixture(scope="function")
def setup(args, session):
    COLLECTION = "pytest"
    FILE_PATH = "app/tests/pytest.pdf"

    # Delete the collection if it exists
    response = session.delete(f"{args['base_url']}/collections/{COLLECTION}")
    assert response.status_code == 204 or response.status_code == 404, f"error: delete collection ({response.status_code} - {response.text})"

    # Get a embedding model
    response = session.get(f"{args['base_url']}/models")
    response = response.json()["data"]
    EMBEDDINGS_MODEL = [model["id"] for model in response if model["type"] == EMBEDDINGS_MODEL_TYPE][0]
    logging.debug(f"model: {EMBEDDINGS_MODEL}")

    # Upload the file to the collection
    params = {"embeddings_model": EMBEDDINGS_MODEL, "collection": COLLECTION}
    files = {"files": (os.path.basename(FILE_PATH), open(FILE_PATH, "rb"), "application/pdf")}
    response = session.post(f"{args['base_url']}/files", params=params, files=files, timeout=30)
    assert response.status_code == 200, f"error: upload file ({response.status_code} - {response.text})"
    assert response.json()["data"][0]["status"] == "success"

    # Check if the file is uploaded
    response = session.get(f"{args['base_url']}/files/{COLLECTION}", timeout=10)
    assert response.status_code == 200, f"error: retrieve files ({response.status_code} - {response.text})"
    files = response.json()
    assert len(files["data"]) == 1
    assert files["data"][0]["file_name"] == os.path.basename(FILE_PATH)
    FILE_ID = files["data"][0]["id"]

    CHUNK_IDS = files["data"][0]["chunks"]

    # Get chunks of the file
    data = {"chunks": CHUNK_IDS}
    response = session.post(f"{args['base_url']}/chunks/{COLLECTION}", json=data, timeout=10)
    assert response.status_code == 200, f"error: retrieve chunks ({response.status_code} - {response.text})"
    chunks = response.json()
    MAX_K = len(chunks["data"])

    yield EMBEDDINGS_MODEL, FILE_ID, MAX_K, COLLECTION


@pytest.mark.usefixtures("args", "session")
class TestSearch:
    def test_search_response_status_code(self, args, session, setup):
        """Test the POST /search response status code."""

        EMBEDDINGS_MODEL, _, MAX_K, COLLECTION = setup
        data = {"prompt": "test query", "model": EMBEDDINGS_MODEL, "collections": [COLLECTION], "k": MAX_K}
        response = session.post(f"{args['base_url']}/search", json=data)
        assert response.status_code == 200, f"error: search request ({response.status_code} - {response.text})"

        searches = Searches(**response.json())
        assert isinstance(searches, Searches)
        assert all(isinstance(search, Search) for search in searches.data)

    def test_search_with_score_threshold(self, args, session, setup):
        """Test search with a score threshold."""

        EMBEDDINGS_MODEL, _, MAX_K, COLLECTION = setup
        data = {"prompt": "test query", "model": EMBEDDINGS_MODEL, "collections": [COLLECTION], "k": MAX_K, "score_threshold": 0.5}
        response = session.post(f"{args['base_url']}/search", json=data)
        assert response.status_code == 200

    def test_search_invalid_collection(self, args, session, setup):
        """Test search with an invalid collection."""

        EMBEDDINGS_MODEL, _, MAX_K, _ = setup
        data = {"prompt": "test query", "model": EMBEDDINGS_MODEL, "collections": ["non_existent_collection"], "k": MAX_K}
        response = session.post(f"{args['base_url']}/search", json=data)
        assert response.status_code == 404

    def test_search_invalid_k(self, args, session, setup):
        """Test search with an invalid k value."""

        EMBEDDINGS_MODEL, _, _, COLLECTION = setup
        data = {"prompt": "test query", "model": EMBEDDINGS_MODEL, "collections": [COLLECTION], "k": 0}
        response = session.post(f"{args['base_url']}/search", json=data)
        assert response.status_code == 422

    def test_search_empty_prompt(self, args, session, setup):
        """Test search with an empty prompt."""

        EMBEDDINGS_MODEL, _, MAX_K, COLLECTION = setup
        data = {"prompt": "", "model": EMBEDDINGS_MODEL, "collections": [COLLECTION], "k": MAX_K}
        response = session.post(f"{args['base_url']}/search", json=data)
        assert response.status_code == 422

    def test_search_invalid_model(self, args, session, setup):
        """Test search with an invalid model."""

        _, _, MAX_K, COLLECTION = setup
        data = {"prompt": "test query", "model": "non_existent_model", "collections": [COLLECTION], "k": MAX_K}
        response = session.post(f"{args['base_url']}/search", json=data)
        assert response.status_code == 404
