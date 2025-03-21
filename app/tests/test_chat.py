import json
import logging
import os
import uuid

import pytest

from app.schemas.chat import ChatCompletion, ChatCompletionChunk
from app.utils.variables import MODEL_TYPE__EMBEDDINGS, MODEL_TYPE__LANGUAGE


@pytest.fixture(scope="module")
def setup(args, test_client):
    test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}
    # get a language model
    response = test_client.get("/v1/models")
    assert response.status_code == 200, f"error: retrieve models ({response.status_code})"
    response_json = response.json()
    model = [model for model in response_json["data"] if model["type"] == MODEL_TYPE__LANGUAGE][0]
    MODEL_ID = model["id"]
    MAX_CONTEXT_LENGTH = model["max_context_length"]
    logging.info(f"test model ID: {MODEL_ID}")
    logging.info(f"test max context length: {MAX_CONTEXT_LENGTH}")

    # create a collection
    embeddings_model_id = [model["id"] for model in response_json["data"] if model["type"] == MODEL_TYPE__EMBEDDINGS][0]
    logging.info(f"test embeddings model ID: {embeddings_model_id}")
    response = test_client.post("/v1/collections", json={"name": "pytest-private", "model": embeddings_model_id})
    assert response.status_code == 201, f"error: create collection ({response.status_code})"
    COLLECTION_ID = response.json()["id"]

    # Upload the file to the collection
    file_path = "app/tests/assets/json.json"
    files = {"file": (os.path.basename(file_path), open(file_path, "rb"), "application/json")}
    data = {"request": '{"collection": "%s", "chunker": {"args": {"chunk_size": 1000}}}' % COLLECTION_ID}

    response = test_client.post("/v1/files", data=data, files=files)

    # Get document IDS
    response = test_client.get(f"/v1/documents/{COLLECTION_ID}")
    DOCUMENT_IDS = [response.json()["data"][0]["id"], response.json()["data"][1]["id"]]

    yield MODEL_ID, MAX_CONTEXT_LENGTH, DOCUMENT_IDS, COLLECTION_ID


@pytest.mark.usefixtures("args", "setup", "test_client")
class TestChat:
    def test_chat_completions_unstreamed_response(self, args, test_client, setup):
        """Test the POST /chat/completions unstreamed response."""
        MODEL_ID, _, _, _ = setup
        test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}
        params = {
            "model": MODEL_ID,
            "messages": [{"role": "user", "content": "Hello, how are you?"}],
            "stream": False,
            "n": 1,
            "max_tokens": 10,
        }
        response = test_client.post("/v1/chat/completions", json=params)
        assert response.status_code == 200, f"error: retrieve chat completions ({response.status_code})"

        response_json = response.json()
        chat_completion = ChatCompletion(**response_json)
        assert isinstance(chat_completion, ChatCompletion)

    def test_chat_completions_streamed_response(self, args, test_client, setup):
        """Test the POST /chat/completions streamed response."""
        MODEL_ID, _, _, _ = setup
        test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}
        params = {
            "model": MODEL_ID,
            "messages": [{"role": "user", "content": "Hello, how are you?"}],
            "stream": True,
            "n": 1,
            "max_tokens": 10,
        }
        response = test_client.post("/v1/chat/completions", json=params)
        assert response.status_code == 200, f"error: retrieve chat completions ({response.status_code})"

        for line in response.iter_lines():
            if line:
                chunk = line.split("data: ")[1]
                if chunk == "[DONE]":
                    break
                chunk = json.loads(chunk)
                chat_completion_chunk = ChatCompletionChunk(**chunk)
                assert isinstance(chat_completion_chunk, ChatCompletionChunk), f"error: retrieve chat completions chunk {chunk}"

    def test_chat_completions_unknown_params(self, args, test_client, setup):
        """Test the POST /chat/completions unknown params."""
        MODEL_ID, _, _, _ = setup
        test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}
        params = {
            "model": MODEL_ID,
            "messages": [{"role": "user", "content": "Hello, how are you?"}],
            "stream": True,
            "n": 1,
            "max_tokens": 10,
            "min_tokens": 3,  # unknown param in ChatCompletionRequest schema
        }
        response = test_client.post("/v1/chat/completions", json=params)

        assert response.status_code == 200, f"error: retrieve chat completions ({response.status_code})"

    def test_chat_completions_context_too_large(self, args, test_client, setup):
        MODEL_ID, MAX_CONTEXT_LENGTH, _, _ = setup
        test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}
        prompt = "test" * (MAX_CONTEXT_LENGTH + 100)
        params = {
            "model": MODEL_ID,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "n": 1,
            "max_tokens": 10,
        }
        response = test_client.post("/v1/chat/completions", json=params)
        assert response.status_code == 400, f"error: retrieve chat completions ({response.status_code})"

    def test_chat_completions_streamed_context_too_large(self, args, test_client, setup):
        MODEL_ID, MAX_CONTEXT_LENGTH, _, _ = setup
        test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}
        prompt = "test " * (MAX_CONTEXT_LENGTH + 1000)
        params = {
            "model": MODEL_ID,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
            "n": 1,
            "max_tokens": 10,
        }
        response = test_client.post("/v1/chat/completions", json=params)
        assert response.status_code == 400, f"error: retrieve chat completions ({response.status_code})"

    def test_chat_completions_search_unstreamed_response(self, args, test_client, setup):
        """Test the GET /chat/completions search unstreamed response."""
        MODEL_ID, _, DOCUMENT_IDS, COLLECTION_ID = setup
        test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}
        params = {
            "model": MODEL_ID,
            "messages": [{"role": "user", "content": "Qui est Albert ?"}],
            "stream": False,
            "n": 1,
            "max_tokens": 10,
            "search": True,
            "search_args": {
                "collections": [COLLECTION_ID],
                "k": 3,
                "method": "semantic",
                "rff_k": 1,
            },
        }
        response = test_client.post("/v1/chat/completions", json=params)

        assert response.status_code == 200, f"error: retrieve chat completions ({response.status_code}, {response.json()})"

        response_json = response.json()
        chat_completion = ChatCompletion(**response_json)
        assert chat_completion.search_results[0].chunk.metadata.document_id in DOCUMENT_IDS

    def test_chat_completions_search_streamed_response(self, args, test_client, setup):
        """Test the GET /chat/completions search streamed response."""
        MODEL_ID, _, DOCUMENT_IDS, COLLECTION_ID = setup
        test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}
        params = {
            "model": MODEL_ID,
            "messages": [{"role": "user", "content": "Qui est Albert ?"}],
            "stream": True,
            "n": 1,
            "max_tokens": 10,
            "search": True,
            "search_args": {
                "collections": [COLLECTION_ID],
                "k": 3,
                "method": "semantic",
                "rff_k": 1,
            },
        }

        response = test_client.post("/v1/chat/completions", json=params)
        assert response.status_code == 200, f"error: retrieve chat completions ({response.status_code})"

        i = 0
        for line in response.iter_lines():
            if line:
                chunk = line.split("data: ")[1]
                if chunk == "[DONE]":
                    break
                chunk = json.loads(chunk)
                chat_completion_chunk = ChatCompletionChunk(**chunk)
                if i == 0:
                    assert chat_completion_chunk.search_results[0].chunk.metadata.document_id in DOCUMENT_IDS
                i = 1

    def test_chat_completions_search_no_args(self, args, test_client, setup):
        """Test the GET /chat/completions search template not found."""
        MODEL_ID, _, _, _ = setup
        test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}
        params = {
            "model": MODEL_ID,
            "messages": [{"role": "user", "content": "Qui est Albert ?"}],
            "stream": False,
            "n": 1,
            "max_tokens": 10,
            "search": True,
        }
        response = test_client.post("/v1/chat/completions", json=params)
        assert response.status_code == 422, f"error: retrieve chat completions ({response.status_code})"

    def test_chat_completions_search_no_collections(self, args, test_client, setup):
        """Test the GET /chat/completions search no collections."""
        MODEL_ID, _, _, _ = setup
        test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}
        params = {
            "model": MODEL_ID,
            "messages": [{"role": "user", "content": "Qui est Albert ?"}],
            "stream": False,
            "n": 1,
            "max_tokens": 10,
            "search": True,
            "search_args": {
                "k": 3,
                "method": "semantic",
                "rff_k": 1,
            },
        }
        response = test_client.post("/v1/chat/completions", json=params)
        assert response.status_code == 422, f"error: retrieve chat completions ({response.status_code})"

    def test_chat_completions_search_template(self, args, test_client, setup):
        """Test the GET /chat/completions search template."""
        MODEL_ID, _, _, COLLECTION_ID = setup
        test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}
        params = {
            "model": MODEL_ID,
            "messages": [{"role": "user", "content": "Qui est Albert ?"}],
            "stream": False,
            "n": 1,
            "max_tokens": 10,
            "search": True,
            "search_args": {
                "collections": [COLLECTION_ID],
                "k": 3,
                "method": "semantic",
                "rff_k": 1,
                "template": "Ne réponds pas à la question {prompt} à l'aide des documents ci-dessous : {chunks}",
            },
        }

        response = test_client.post("/v1/chat/completions", json=params)
        assert response.status_code == 200, f"error: retrieve chat completions ({response.status_code})"

    def test_chat_completions_search_internet(self, args, test_client, setup):
        """Test the GET /chat/completions search internet."""
        MODEL_ID, _, _, COLLECTION_ID = setup
        test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}
        params = {
            "model": MODEL_ID,
            "messages": [{"role": "user", "content": "Qui est Ulrich Tan ?"}],
            "stream": False,
            "n": 1,
            "max_tokens": 10,
            "search": True,
            "search_args": {
                "collections": ["internet"],
                "k": 3,
                "method": "semantic",
                "rff_k": 1,
            },
        }
        response = test_client.post("/v1/chat/completions", json=params)
        assert response.status_code == 200, f"error: retrieve chat completions ({response.status_code})"

    def test_chat_completions_search_template_missing_placeholders(self, args, test_client, setup):
        """Test the GET /chat/completions search template missing placeholders."""
        MODEL_ID, _, _, COLLECTION_ID = setup
        test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}
        params = {
            "model": MODEL_ID,
            "messages": [{"role": "user", "content": "Qui est Albert ?"}],
            "stream": False,
            "n": 1,
            "max_tokens": 10,
            "search": True,
            "search_args": {
                "collections": [COLLECTION_ID],
                "k": 3,
                "method": "semantic",
                "rff_k": 1,
                "template": "Ne réponds pas à la question {prompt}.",
            },
        }
        response = test_client.post("/v1/chat/completions", json=params)
        assert response.status_code == 422, f"error: retrieve chat completions ({response.status_code})"

    def test_chat_completions_search_wrong_collection(self, args, test_client, setup):
        """Test the GET /chat/completions search wrong collection."""
        MODEL_ID, _, _, COLLECTION_ID = setup
        test_client.headers = {"Authorization": f"Bearer {args['api_key_user']}"}
        params = {
            "model": MODEL_ID,
            "messages": [{"role": "user", "content": "Qui est Albert ?"}],
            "stream": False,
            "n": 1,
            "max_tokens": 10,
            "search": True,
            "search_args": {
                "collections": [str(uuid.uuid4())],
                "k": 3,
                "method": "semantic",
                "rff_k": 1,
            },
        }
        response = test_client.post("/v1/chat/completions", json=params)
        assert response.status_code == 404, f"error: retrieve chat completions ({response.status_code})"
