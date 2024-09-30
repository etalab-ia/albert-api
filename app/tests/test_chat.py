import json
import logging

import pytest

from app.schemas.chat import ChatCompletion, ChatCompletionChunk
from app.utils.variables import LANGUAGE_MODEL_TYPE


@pytest.mark.usefixtures("args", "session")
class TestChat:
    def test_chat_completions_unstreamed_response(self, args, session):
        """Test the GET /chat/completions response status code."""
        # retrieve model
        response = session.get(f"{args['base_url']}/models")
        assert response.status_code == 200, f"error: retrieve models ({response.status_code})"
        response_json = response.json()
        model = [model["id"] for model in response_json["data"] if model["type"] == LANGUAGE_MODEL_TYPE][0]
        logging.debug(f"model: {model}")

        params = {
            "model": model,
            "messages": [{"role": "user", "content": "Hello, how are you?"}],
            "stream": False,
            "n": 1,
            "max_tokens": 10,
        }
        response = session.post(f"{args['base_url']}/chat/completions", json=params)
        assert response.status_code == 200, f"error: retrieve chat completions ({response.status_code})"

    def test_chat_completions_unstreamed_response_schemas(self, args, session):
        """Test the GET /chat/completions response schemas."""
        # retrieve model
        response = session.get(f"{args['base_url']}/models")
        assert response.status_code == 200, f"error: retrieve models ({response.status_code})"
        response_json = response.json()
        model = [model["id"] for model in response_json["data"] if model["type"] == LANGUAGE_MODEL_TYPE][0]
        logging.debug(f"model: {model}")

        params = {
            "model": model,
            "messages": [{"role": "user", "content": "Hello, how are you?"}],
            "stream": False,
            "n": 1,
            "max_tokens": 10,
        }
        response = session.post(f"{args['base_url']}/chat/completions", json=params)

        response_json = response.json()
        chat_completion = ChatCompletion(**response_json)

        assert isinstance(chat_completion, ChatCompletion)

    def test_chat_completions_streamed_response(self, args, session):
        """Test the GET /chat/completions response status code."""
        # retrieve model
        response = session.get(f"{args['base_url']}/models")
        assert response.status_code == 200, f"error: retrieve models ({response.status_code})"
        response_json = response.json()
        model = [model["id"] for model in response_json["data"] if model["type"] == LANGUAGE_MODEL_TYPE][0]
        logging.debug(f"model: {model}")

        params = {
            "model": model,
            "messages": [{"role": "user", "content": "Hello, how are you?"}],
            "stream": True,
            "n": 1,
            "max_tokens": 10,
        }
        response = session.post(f"{args['base_url']}/chat/completions", json=params)
        assert response.status_code == 200, f"error: retrieve chat completions ({response.status_code})"

    def test_chat_completions_streamed_response_schemas(self, args, session):
        """Test the GET /chat/completions response schemas."""
        # retrieve model
        response = session.get(f"{args['base_url']}/models")
        assert response.status_code == 200, f"error: retrieve models ({response.status_code})"
        response_json = response.json()
        model = [model["id"] for model in response_json["data"] if model["type"] == LANGUAGE_MODEL_TYPE][0]
        logging.debug(f"model: {model}")

        params = {
            "model": model,
            "messages": [{"role": "user", "content": "Hello, how are you?"}],
            "stream": True,
            "n": 1,
            "max_tokens": 100,
        }
        response = session.post(f"{args['base_url']}/chat/completions", json=params)

        chunks = []
        for line in response.iter_lines():
            if line:
                chunk = line.decode("utf-8").split("data: ")[1]
                if chunk == "[DONE]":
                    break
                chunk = json.loads(chunk)
                chat_completion_chunk = ChatCompletionChunk(**chunk)
                assert isinstance(chat_completion_chunk, ChatCompletionChunk), f"error: retrieve chat completions chunk {chunk}"

    def test_chat_completions_unknown_params(self, args, session):
        """Test the GET /chat/completions response status code."""
        # retrieve model
        response = session.get(f"{args['base_url']}/models")
        assert response.status_code == 200, f"error: retrieve models ({response.status_code})"
        response_json = response.json()
        model = [model["id"] for model in response_json["data"] if model["type"] == LANGUAGE_MODEL_TYPE][0]
        logging.debug(f"model: {model}")

        params = {
            "model": model,
            "messages": [{"role": "user", "content": "Hello, how are you?"}],
            "stream": True,
            "n": 1,
            "max_tokens": 10,
            "min_tokens": 3,  # unknown param in ChatCompletionRequest schema
        }
        response = session.post(f"{args['base_url']}/chat/completions", json=params)
        assert response.status_code == 200, f"error: retrieve chat completions ({response.status_code})"
