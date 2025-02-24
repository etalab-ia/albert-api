import logging

import pytest

from app.schemas.rerank import Reranks
from app.utils.variables import MODEL_TYPE__EMBEDDINGS, MODEL_TYPE__LANGUAGE, MODEL_TYPE__RERANK


@pytest.fixture(scope="module")
def setup(args, test_client):
    test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}
    response = test_client.get(f"{args['base_url']}/models")
    assert response.status_code == 200, f"error: retrieve models ({response.status_code})"
    response_json = response.json()

    LANGUAGE_MODEL_ID = [model["id"] for model in response_json["data"] if model["type"] == MODEL_TYPE__LANGUAGE][0]
    logging.info(f"test model ID: {LANGUAGE_MODEL_ID}")

    RERANK_MODEL_ID = [model["id"] for model in response_json["data"] if model["type"] == MODEL_TYPE__RERANK][0]
    logging.info(f"test model ID: {RERANK_MODEL_ID}")

    EMBEDDINGS_MODEL_ID = [model["id"] for model in response_json["data"] if model["type"] == MODEL_TYPE__EMBEDDINGS][0]
    logging.info(f"test model ID: {EMBEDDINGS_MODEL_ID}")

    yield LANGUAGE_MODEL_ID, RERANK_MODEL_ID, EMBEDDINGS_MODEL_ID


@pytest.mark.usefixtures("args", "setup", "test_client")
class TestRerank:
    def test_rerank_with_language_model(self, args, test_client, setup):
        """Test the POST /rerank with a language model."""
        LANGUAGE_MODEL_ID, _, _ = setup
        test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}
        params = {"model": LANGUAGE_MODEL_ID, "prompt": "Sort these sentences by relevance.", "input": ["Sentence 1", "Sentence 2", "Sentence 3"]}
        response = test_client.post(f"{args['base_url']}/rerank", json=params)
        assert response.status_code == 200, f"error: rerank with language model ({response.status_code})"

        response_json = response.json()
        reranks = Reranks(**response_json)
        assert isinstance(reranks, Reranks)

    def test_rerank_with_rerank_model(self, args, test_client, setup):
        """Test the POST /rerank with a rerank model."""
        _, RERANK_MODEL_ID, _ = setup
        test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}
        params = {"model": RERANK_MODEL_ID, "prompt": "Sort these sentences by relevance.", "input": ["Sentence 1", "Sentence 2", "Sentence 3"]}
        response = test_client.post(f"{args['base_url']}/rerank", json=params)
        assert response.status_code == 200, f"error: rerank with rerank model ({response.status_code})"

        response_json = response.json()
        reranks = Reranks(**response_json)
        assert isinstance(reranks, Reranks)

    def test_rerank_with_wrong_model_type(self, args, test_client, setup):
        """Test the POST /rerank with a wrong model type."""
        _, _, EMBEDDINGS_MODEL_ID = setup
        test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}
        params = {"model": EMBEDDINGS_MODEL_ID, "prompt": "Sort these sentences by relevance.", "input": ["Sentence 1", "Sentence 2", "Sentence 3"]}
        response = test_client.post(f"{args['base_url']}/rerank", json=params)
        assert response.status_code == 422, f"error: rerank with wrong model type ({response.status_code})"

    def test_rerank_with_unknown_model(self, args, test_client, setup):
        """Test the POST /rerank with an unknown model."""
        _, _, _ = setup
        test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}
        params = {"model": "unknown", "prompt": "Sort these sentences by relevance.", "input": ["Sentence 1", "Sentence 2", "Sentence 3"]}
        response = test_client.post(f"{args['base_url']}/rerank", json=params)
        assert response.status_code == 404, f"error: rerank with unknown model ({response.status_code})"
