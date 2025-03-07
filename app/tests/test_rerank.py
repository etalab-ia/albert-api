import logging

import pytest

from app.schemas.rerank import Reranks
from app.utils.variables import MODEL_TYPE__EMBEDDINGS, MODEL_TYPE__RERANK

from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def setup(client: TestClient):
    response = client.get_user(url="/v1/models")
    assert response.status_code == 200, f"error: retrieve models ({response.status_code})"
    response_json = response.json()

    RERANK_MODEL_ID = [model["id"] for model in response_json["data"] if model["type"] == MODEL_TYPE__RERANK][0]
    logging.info(f"test model ID: {RERANK_MODEL_ID}")

    EMBEDDINGS_MODEL_ID = [model["id"] for model in response_json["data"] if model["type"] == MODEL_TYPE__EMBEDDINGS][0]
    logging.info(f"test model ID: {EMBEDDINGS_MODEL_ID}")

    yield RERANK_MODEL_ID, EMBEDDINGS_MODEL_ID


@pytest.mark.usefixtures("client", "setup", "cleanup")
class TestRerank:
    def test_rerank_with_rerank_model(self, client: TestClient, setup):
        """Test the POST /rerank with a rerank model."""
        RERANK_MODEL_ID, _ = setup

        params = {"model": RERANK_MODEL_ID, "prompt": "Sort these sentences by relevance.", "input": ["Sentence 1", "Sentence 2", "Sentence 3"]}
        response = client.post_user(url="/v1/rerank", json=params)
        assert response.status_code == 200, response.text

        Reranks(**response.json())  # test output format

    def test_rerank_with_wrong_model_type(self, client: TestClient, setup):
        """Test the POST /rerank with a wrong model type."""
        _, EMBEDDINGS_MODEL_ID = setup

        params = {"model": EMBEDDINGS_MODEL_ID, "prompt": "Sort these sentences by relevance.", "input": ["Sentence 1", "Sentence 2", "Sentence 3"]}
        response = client.post_user(url="/v1/rerank", json=params)
        assert response.status_code == 422, response.text

    def test_rerank_with_unknown_model(self, client: TestClient, setup):
        """Test the POST /rerank with an unknown model."""
        _, _ = setup

        params = {"model": "unknown", "prompt": "Sort these sentences by relevance.", "input": ["Sentence 1", "Sentence 2", "Sentence 3"]}
        response = client.post_user(url="/v1/rerank", json=params)
        assert response.status_code == 404, response.text
