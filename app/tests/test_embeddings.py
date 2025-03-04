import pytest

from app.utils.settings import settings
from app.utils.variables import MODEL_TYPE__EMBEDDINGS


@pytest.fixture(scope="module")
def setup(args, test_client):
    test_client.headers = {"Authorization": f"Bearer {args["api_key_user"]}"}
    # Get an embeddings model
    response = test_client.get("/v1/models")
    assert response.status_code == 200, f"error: retrieve models ({response.status_code})"
    response_json = response.json()
    model = [model for model in response_json["data"] if model["type"] == MODEL_TYPE__EMBEDDINGS][0]
    MODEL_ID = model["id"]
    yield MODEL_ID


@pytest.mark.usefixtures("args", "setup", "test_client")
class TestEmbeddings:
    def test_embeddings_single_input(self, args, test_client, setup):
        """Test the POST /embeddings endpoint with a single input."""
        MODEL_ID = setup
        test_client.headers = {"Authorization": f"Bearer {args["api_key_user"]}"}
        params = {
            "model": MODEL_ID,
            "input": "Hello, this is a test.",
        }
        response = test_client.post("/v1/embeddings", json=params)
        assert response.status_code == 200, f"error: create embeddings ({response.status_code})"

        response_json = response.json()
        assert "data" in response_json
        assert len(response_json["data"]) == 1
        assert "embedding" in response_json["data"][0]
        assert isinstance(response_json["data"][0]["embedding"], list)
        assert all(isinstance(x, float) for x in response_json["data"][0]["embedding"])

    def test_embeddings_token_integers_input(self, args, test_client, setup):
        """Test the POST /embeddings endpoint with token integers input."""
        MODEL_ID = setup
        test_client.headers = {"Authorization": f"Bearer {args["api_key_user"]}"}
        params = {
            "model": MODEL_ID,
            "input": [1, 2, 3, 4, 5],  # List[int]
        }
        response = test_client.post("/v1/embeddings", json=params)
        assert response.status_code == 200, f"error: create embeddings ({response.status_code})"

    def test_embeddings_token_integers_batch_input(self, args, test_client, setup):
        """Test the POST /embeddings endpoint with batch of token integers input."""
        MODEL_ID = setup
        test_client.headers = {"Authorization": f"Bearer {args["api_key_user"]}"}
        params = {
            "model": MODEL_ID,
            "input": [[1, 2, 3], [4, 5, 6]],  # List[List[int]]
        }
        response = test_client.post("/v1/embeddings", json=params)
        assert response.status_code == 200, f"error: create embeddings ({response.status_code})"

    def test_embeddings_with_encoding_format(self, args, test_client, setup):
        """Test the POST /embeddings endpoint with encoding format."""
        MODEL_ID = setup
        test_client.headers = {"Authorization": f"Bearer {args["api_key_user"]}"}
        params = {
            "model": MODEL_ID,
            "input": "Test text",
            "encoding_format": "float",
        }
        response = test_client.post("/v1/embeddings", json=params)
        assert response.status_code == 200, f"error: create embeddings ({response.status_code})"

    def test_embeddings_invalid_encoding_format(self, args, test_client, setup):
        """Test the POST /embeddings endpoint with invalid encoding format."""
        MODEL_ID = setup
        test_client.headers = {"Authorization": f"Bearer {args["api_key_user"]}"}
        params = {
            "model": MODEL_ID,
            "input": "Test text",
            "encoding_format": "invalid_format",
        }
        response = test_client.post("/v1/embeddings", json=params)
        assert response.status_code == 422, f"error: invalid encoding format should return 422 ({response.status_code})"

    def test_embeddings_wrong_model_type(self, args, test_client):
        """Test the POST /embeddings endpoint with wrong model type."""
        test_client.headers = {"Authorization": f"Bearer {args["api_key_user"]}"}
        # Get a non-embeddings model (e.g., language model)
        response = test_client.get("/v1/models")
        models = response.json()["data"]
        non_embeddings_model = [m for m in models if m["type"] != MODEL_TYPE__EMBEDDINGS][0]

        params = {
            "model": non_embeddings_model["id"],
            "input": "Test text",
        }
        response = test_client.post("/v1/embeddings", json=params)
        assert response.status_code == 422, f"error: wrong model type should return 400 ({response.status_code})"

    def test_embeddings_batch_input(self, args, test_client, setup):
        """Test the POST /embeddings endpoint with batch input."""
        MODEL_ID = setup
        test_client.headers = {"Authorization": f"Bearer {args["api_key_user"]}"}
        params = {
            "model": MODEL_ID,
            "input": ["Hello, this is a test.", "This is another test."],
        }
        response = test_client.post("/v1/embeddings", json=params)
        assert response.status_code == 200, f"error: create embeddings ({response.status_code})"

        response_json = response.json()
        assert "data" in response_json
        assert len(response_json["data"]) == 2
        for item in response_json["data"]:
            assert "embedding" in item
            assert isinstance(item["embedding"], list)
            assert all(isinstance(x, float) for x in item["embedding"])

    def test_embeddings_empty_input(self, args, test_client, setup):
        """Test the POST /embeddings endpoint with empty input."""
        MODEL_ID = setup
        test_client.headers = {"Authorization": f"Bearer {args["api_key_user"]}"}
        params = {
            "model": MODEL_ID,
            "input": "",
        }
        response = test_client.post("/v1/embeddings", json=params)
        assert response.status_code == 422, f"error: empty input should return 422 ({response.status_code})"

    def test_embeddings_invalid_model(self, args, test_client):
        """Test the POST /embeddings endpoint with invalid model."""
        test_client.headers = {"Authorization": f"Bearer {args["api_key_user"]}"}
        params = {
            "model": "invalid_model_id",
            "input": "Hello, this is a test.",
        }
        response = test_client.post("/v1/embeddings", json=params)
        assert response.status_code == 404, f"error: invalid model should return 404 ({response.status_code})"

    def test_embeddings_missing_input(self, args, test_client, setup):
        """Test the POST /embeddings endpoint with missing input."""
        MODEL_ID = setup
        test_client.headers = {"Authorization": f"Bearer {args["api_key_user"]}"}
        params = {
            "model": MODEL_ID,
        }
        response = test_client.post("/v1/embeddings", json=params)
        assert response.status_code == 422, f"error: missing input should return 422 ({response.status_code})"

    def test_embeddings_model_alias(self, args, test_client, setup):
        """Test the POST /embeddings endpoint with a model alias."""
        MODEL_ID = setup
        test_client.headers = {"Authorization": f"Bearer {args["api_key_user"]}"}

        aliases = {model.id: model.aliases for model in settings.models}
        aliases = aliases[MODEL_ID]
        input = "Hello, this is a test."

        params = {"model": aliases[0], "input": input}
        response = test_client.post("/v1/embeddings", json=params)
        assert response.status_code == 200, f"error: create embeddings ({response.status_code})"

        response_alias = response.json()

        params = {"model": MODEL_ID, "input": input}
        response = test_client.post("/v1/embeddings", json=params)
        assert response.status_code == 200, f"error: create embeddings ({response.status_code})"

        response_model = response.json()

        assert response_alias["data"][0]["embedding"] == response_model["data"][0]["embedding"]
