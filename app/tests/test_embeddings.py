import pytest

from app.utils.settings import settings
from app.utils.variables import MODEL_TYPE__EMBEDDINGS
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def setup(client: TestClient):
    # Get an embeddings model
    response = client.get_user(url="/v1/models")
    assert response.status_code == 200, f"error: retrieve models ({response.status_code})"
    response_json = response.json()
    model = [model for model in response_json["data"] if model["type"] == MODEL_TYPE__EMBEDDINGS][0]
    MODEL_ID = model["id"]

    yield MODEL_ID


@pytest.mark.usefixtures("client", "setup", "cleanup")
class TestEmbeddings:
    def test_embeddings_single_input(self, client: TestClient, setup):
        """Test the POST /embeddings endpoint with a single input."""
        MODEL_ID = setup
        params = {"model": MODEL_ID, "input": "Hello, this is a test."}
        response = client.post_user(url="/v1/embeddings", json=params)
        assert response.status_code == 200, response.text

        response_json = response.json()
        assert "data" in response_json
        assert len(response_json["data"]) == 1
        assert "embedding" in response_json["data"][0]
        assert isinstance(response_json["data"][0]["embedding"], list)
        assert all(isinstance(x, float) for x in response_json["data"][0]["embedding"])

    def test_embeddings_token_integers_input(self, client: TestClient, setup):
        """Test the POST /embeddings endpoint with token integers input."""
        MODEL_ID = setup
        params = {"model": MODEL_ID, "input": [1, 2, 3, 4, 5]}
        response = client.post_user(url="/v1/embeddings", json=params)
        assert response.status_code == 200, response.text

    def test_embeddings_token_integers_batch_input(self, client: TestClient, setup):
        """Test the POST /embeddings endpoint with batch of token integers input."""
        MODEL_ID = setup
        params = {"model": MODEL_ID, "input": [[1, 2, 3], [4, 5, 6]]}
        response = client.post_user(url="/v1/embeddings", json=params)
        assert response.status_code == 200, response.text

    def test_embeddings_with_encoding_format(self, client: TestClient, setup):
        """Test the POST /embeddings endpoint with encoding format."""
        MODEL_ID = setup
        params = {"model": MODEL_ID, "input": "Test text", "encoding_format": "float"}
        response = client.post_user(url="/v1/embeddings", json=params)
        assert response.status_code == 200, response.text

    def test_embeddings_invalid_encoding_format(self, client: TestClient, setup):
        """Test the POST /embeddings endpoint with invalid encoding format."""
        MODEL_ID = setup
        params = {"model": MODEL_ID, "input": "Test text", "encoding_format": "invalid_format"}
        response = client.post_user(url="/v1/embeddings", json=params)
        assert response.status_code == 422, response.text

    def test_embeddings_wrong_model_type(self, client: TestClient, setup):
        """Test the POST /embeddings endpoint with wrong model type."""
        _ = setup
        # Get a non-embeddings model (e.g., language model)
        response = client.get_user(url="/v1/models")
        models = response.json()["data"]
        non_embeddings_model = [m for m in models if m["type"] != MODEL_TYPE__EMBEDDINGS][0]

        params = {"model": non_embeddings_model["id"], "input": "Test text"}
        response = client.post_user(url="/v1/embeddings", json=params)
        assert response.status_code == 422, response.text

    def test_embeddings_batch_input(self, client: TestClient, setup):
        """Test the POST /embeddings endpoint with batch input."""
        MODEL_ID = setup
        params = {"model": MODEL_ID, "input": ["Hello, this is a test.", "This is another test."]}
        response = client.post_user(url="/v1/embeddings", json=params)
        assert response.status_code == 200, response.text

        response_json = response.json()
        assert "data" in response_json
        assert len(response_json["data"]) == 2
        for item in response_json["data"]:
            assert "embedding" in item
            assert isinstance(item["embedding"], list)
            assert all(isinstance(x, float) for x in item["embedding"])

    def test_embeddings_empty_input(self, client: TestClient, setup):
        """Test the POST /embeddings endpoint with empty input."""
        MODEL_ID = setup
        params = {"model": MODEL_ID, "input": ""}
        response = client.post_user(url="/v1/embeddings", json=params)
        assert response.status_code == 422, response.text

    def test_embeddings_invalid_model(self, client: TestClient, setup):
        """Test the POST /embeddings endpoint with invalid model."""
        _ = setup
        params = {"model": "invalid_model_id", "input": "Hello, this is a test."}
        response = client.post_user(url="/v1/embeddings", json=params)
        assert response.status_code == 404, response.text

    def test_embeddings_missing_input(self, client: TestClient, setup):
        """Test the POST /embeddings endpoint with missing input."""
        MODEL_ID = setup
        params = {"model": MODEL_ID}
        response = client.post_user(url="/v1/embeddings", json=params)
        assert response.status_code == 422, response.text

    def test_embeddings_model_alias(self, client: TestClient, setup):
        """Test the POST /embeddings endpoint with a model alias."""
        MODEL_ID = setup

        aliases = {model.id: model.aliases for model in settings.models}
        aliases = aliases[MODEL_ID]
        input = "Hello, this is a test."

        params = {"model": aliases[0], "input": input}
        response = client.post_user(url="/v1/embeddings", json=params)
        assert response.status_code == 200, response.text

        response_alias = response.json()

        params = {"model": MODEL_ID, "input": input}
        response = client.post_user(url="/v1/embeddings", json=params)
        assert response.status_code == 200, response.text

        response_model = response.json()

        assert response_alias["data"][0]["embedding"] == response_model["data"][0]["embedding"]

    # TODO test vector size
