import json
import logging

import pytest

from app.schemas.chat import ChatCompletion, ChatCompletionChunk
from app.utils.variables import LANGUAGE_MODEL_TYPE


@pytest.fixture(scope="module")
def setup(args, session_user):
    # retrieve model
    response = session_user.get(f"{args['base_url']}/models")
    assert response.status_code == 200, f"error: retrieve models ({response.status_code})"
    response_json = response.json()
    model = [model for model in response_json["data"] if model["type"] == LANGUAGE_MODEL_TYPE][0]
    MODEL_ID = model["id"]
    MAX_CONTEXT_LENGTH = model["max_context_length"]
    logging.info(f"test model ID: {MODEL_ID}")
    logging.info(f"test max context length: {MAX_CONTEXT_LENGTH}")

    yield MODEL_ID, MAX_CONTEXT_LENGTH


@pytest.mark.usefixtures("args", "session_user", "setup")
class TestChat:
    def test_chat_completions_unstreamed_response(self, args, session_user, setup):
        """Test the GET /chat/completions response status code."""
        MODEL_ID, _ = setup
        params = {
            "model": MODEL_ID,
            "messages": [{"role": "user", "content": "Hello, how are you?"}],
            "stream": False,
            "n": 1,
            "max_tokens": 10,
        }
        response = session_user.post(f"{args['base_url']}/chat/completions", json=params)
        assert response.status_code == 200, f"error: retrieve chat completions ({response.status_code})"

        response_json = response.json()
        chat_completion = ChatCompletion(**response_json)
        assert isinstance(chat_completion, ChatCompletion)

    def test_chat_completions_streamed_response(self, args, session_user, setup):
        """Test the GET /chat/completions response status code."""
        MODEL_ID, _ = setup
        params = {
            "model": MODEL_ID,
            "messages": [{"role": "user", "content": "Hello, how are you?"}],
            "stream": True,
            "n": 1,
            "max_tokens": 10,
        }
        response = session_user.post(f"{args['base_url']}/chat/completions", json=params)
        assert response.status_code == 200, f"error: retrieve chat completions ({response.status_code})"

        for line in response.iter_lines():
            if line:
                chunk = line.decode("utf-8").split("data: ")[1]
                if chunk == "[DONE]":
                    break
                chunk = json.loads(chunk)
                chat_completion_chunk = ChatCompletionChunk(**chunk)
                assert isinstance(chat_completion_chunk, ChatCompletionChunk), f"error: retrieve chat completions chunk {chunk}"

    def test_chat_completions_unknown_params(self, args, session_user, setup):
        """Test the GET /chat/completions response status code."""
        MODEL_ID, _ = setup
        params = {
            "model": MODEL_ID,
            "messages": [{"role": "user", "content": "Hello, how are you?"}],
            "stream": True,
            "n": 1,
            "max_tokens": 10,
            "min_tokens": 3,  # unknown param in ChatCompletionRequest schema
        }
        response = session_user.post(f"{args['base_url']}/chat/completions", json=params)
        assert response.status_code == 200, f"error: retrieve chat completions ({response.status_code})"

    def test_chat_completions_max_tokens_too_large(self, args, session_user, setup):
        MODEL_ID, MAX_CONTEXT_LENGTH = setup

        prompt = "test"
        params = {
            "model": MODEL_ID,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
            "n": 1,
            "max_tokens": MAX_CONTEXT_LENGTH + 100,
        }
        response = session_user.post(f"{args['base_url']}/chat/completions", json=params)
        assert response.status_code == 422, f"error: retrieve chat completions ({response.status_code})"

    def test_chat_completions_context_too_large(self, args, session_user, setup):
        MODEL_ID, MAX_CONTEXT_LENGTH = setup

        prompt = "test" * (MAX_CONTEXT_LENGTH + 100)
        params = {
            "model": MODEL_ID,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
            "n": 1,
            "max_tokens": 10,
        }
        response = session_user.post(f"{args['base_url']}/chat/completions", json=params)
        assert response.status_code == 413, f"error: retrieve chat completions ({response.status_code})"
