import json
import logging
import os
import time
from uuid import uuid4

from coredis import ConnectionPool, Redis
from fastapi.testclient import TestClient
import pytest

from app.helpers._usagetokenizer import UsageTokenizer

from app.clients.model import BaseModelClient
from app.schemas.chat import ChatCompletion, ChatCompletionChunk
from app.schemas.models import ModelType
from app.utils.settings import settings
from app.utils.variables import ENDPOINT__CHAT_COMPLETIONS, ENDPOINT__COLLECTIONS, ENDPOINT__DOCUMENTS, ENDPOINT__FILES, ENDPOINT__MODELS


@pytest.fixture(scope="module")
def setup(client: TestClient, record_with_vcr):
    # Get a language model
    response = client.get_without_permissions(url=f"/v1{ENDPOINT__MODELS}")
    assert response.status_code == 200, response.text
    response_json = response.json()

    model = [model for model in response_json["data"] if model["type"] == ModelType.TEXT_GENERATION][0]
    MODEL_ID = model["id"]

    logging.info(msg=f"test model ID: {MODEL_ID}")

    # Create a collection
    response = client.post_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}", json={"name": f"test_collection_{uuid4()}"})
    assert response.status_code == 201, response.text
    COLLECTION_ID = response.json()["id"]

    # Upload the file to the collection
    file_path = "app/tests/integ/assets/json.json"
    with open(file_path, "rb") as file:
        files = {"file": (os.path.basename(file_path), file, "application/json")}
        data = {"request": '{"collection": "%s", "chunker": {"args": {"chunk_size": 1000}}}' % COLLECTION_ID}
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__FILES}", data=data, files=files)
        file.close()
    assert response.status_code == 201, response.text

    # Get document IDS
    response = client.get_without_permissions(url=f"/v1{ENDPOINT__DOCUMENTS}", params={"collection": COLLECTION_ID})
    DOCUMENT_IDS = [row["id"] for row in response.json()["data"]]

    yield MODEL_ID, DOCUMENT_IDS, COLLECTION_ID


@pytest.fixture(scope="module")
def tokenizer():
    tokenizer = UsageTokenizer(settings.general.tokenizer)
    tokenizer = tokenizer.tokenizer

    yield tokenizer


@pytest.mark.usefixtures("client", "setup", "tokenizer")
class TestChat:
    @pytest.mark.asyncio
    async def test_chat_completions_unstreamed_response(self, client: TestClient, setup):
        """Test the POST /chat/completions unstreamed response."""
        MODEL_ID, DOCUMENT_IDS, COLLECTION_ID = setup

        redis_connection_pool = ConnectionPool(**settings.databases.redis.args)
        await BaseModelClient.setup_metrics_storage(connection_pool=redis_connection_pool, model=MODEL_ID, api_url="https://albert.api.etalab.gouv.fr/")
        redis_time_to_first_token_ts_key = f"metrics_ts:time_to_first_token:{MODEL_ID}:https://albert.api.etalab.gouv.fr/"
        redis_latency_ts_key = f"metrics_ts:latency:{MODEL_ID}:https://albert.api.etalab.gouv.fr/"
        redis_client = Redis(connection_pool=redis_connection_pool)

        latency_samples_count_before = {
            k.decode(): v for k, v in (await redis_client.timeseries.info(redis_latency_ts_key)).items()
        }["totalSamples"]
        time_to_first_token_samples_count_before = {
            k.decode(): v for k, v in (await redis_client.timeseries.info(redis_time_to_first_token_ts_key)).items()
        }["totalSamples"]

        params = {"model": MODEL_ID, "messages": [{"role": "user", "content": "Hello, how are you?"}], "stream": False, "n": 1, "max_tokens": 10}
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__CHAT_COMPLETIONS}", json=params)
        assert response.status_code == 200, response.text

        ChatCompletion(**response.json())  # test output format

        time.sleep(1) # Wait for metrics to be indeed logged in redis (async task)
        latency_samples_count_after = {
            k.decode(): v for k, v in (await redis_client.timeseries.info(redis_latency_ts_key)).items()
        }["totalSamples"]
        time_to_first_token_samples_count_after = {
            k.decode(): v for k, v in (await redis_client.timeseries.info(redis_time_to_first_token_ts_key)).items()
        }["totalSamples"]

        assert latency_samples_count_after == latency_samples_count_before + 1, "Latency was not updated in redis"
        assert time_to_first_token_samples_count_after == time_to_first_token_samples_count_before, "Time to first token count in redis TS not consistent"

    @pytest.mark.asyncio
    async def test_chat_completions_streamed_response(self, client: TestClient, setup):
        """Test the POST /chat/completions streamed response."""
        MODEL_ID, DOCUMENT_IDS, COLLECTION_ID = setup
        params = {"model": MODEL_ID, "messages": [{"role": "user", "content": "Hello, how are you?"}], "stream": True, "n": 1, "max_tokens": 10}

        redis_connection_pool = ConnectionPool(**settings.databases.redis.args)
        await BaseModelClient.setup_metrics_storage(connection_pool=redis_connection_pool, model=MODEL_ID, api_url="https://albert.api.etalab.gouv.fr/")
        redis_time_to_first_token_ts_key = f"metrics_ts:time_to_first_token:{MODEL_ID}:https://albert.api.etalab.gouv.fr/"
        redis_latency_ts_key = f"metrics_ts:latency:{MODEL_ID}:https://albert.api.etalab.gouv.fr/"
        redis_client = Redis(connection_pool=redis_connection_pool)

        latency_samples_count_before = {
            k.decode(): v for k, v in (await redis_client.timeseries.info(redis_latency_ts_key)).items()
        }["totalSamples"]
        time_to_first_token_samples_count_before = {
            k.decode(): v for k, v in (await redis_client.timeseries.info(redis_time_to_first_token_ts_key)).items()
        }["totalSamples"]

        response = client.post_without_permissions(url=f"/v1{ENDPOINT__CHAT_COMPLETIONS}", json=params)
        assert response.status_code == 200, response.text

        for line in response.iter_lines():
            if line:
                chunk = line.split("data: ")[1]
                if chunk == "[DONE]":
                    break
                chunk = json.loads(chunk)
                ChatCompletionChunk(**chunk)  # test output format

        time.sleep(1) # Wait for metrics to be indeed logged in redis (async task)
        latency_samples_count_after = {
            k.decode(): v for k, v in (await redis_client.timeseries.info(redis_latency_ts_key)).items()
        }["totalSamples"]
        time_to_first_token_samples_count_after = {
            k.decode(): v for k, v in (await redis_client.timeseries.info(redis_time_to_first_token_ts_key)).items()
        }["totalSamples"]

        assert latency_samples_count_after == latency_samples_count_before + 1,\
            "Latency was not updated in redis"
        assert time_to_first_token_samples_count_after == time_to_first_token_samples_count_before + 1,\
            "Time to first token was not updated in redis"

    def test_chat_completions_unknown_params(self, client: TestClient, setup):
        """Test the POST /chat/completions unknown params."""
        MODEL_ID, DOCUMENT_IDS, COLLECTION_ID = setup
        params = {
            "model": MODEL_ID,
            "messages": [{"role": "user", "content": "Hello, how are you?"}],
            "stream": True,
            "n": 1,
            "max_tokens": 10,
            "min_tokens": 3,  # unknown param in ChatCompletionRequest schema
        }
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__CHAT_COMPLETIONS}", json=params)

        assert response.status_code == 200, response.text

    def test_chat_completions_forward_error(self, client: TestClient, setup):
        """Test the POST /chat/completions forward errors from the model backend. This test works only if the model backend is vLLM."""
        MODEL_ID, DOCUMENT_IDS, COLLECTION_ID = setup

        params = {
            "model": MODEL_ID,
            "messages": [{"role": "user", "content": "Hello, how are you?"}],
            "guided_regex": 10,  # this param must be a string (see  https://github.com/vllm-project/vllm/blob/86cbd2eee97a98df59c531c34d2aeff5a2b5765d/vllm/entrypoints/openai/protocol.py#L328)
            "stream": False,
            "n": 1,
            "max_tokens": 10,
        }
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__CHAT_COMPLETIONS}", json=params)

        assert response.status_code == 400, response.text

    def test_chat_completions_search_unstreamed_response(self, client: TestClient, setup):
        """Test the GET /chat/completions search unstreamed response."""
        MODEL_ID, DOCUMENT_IDS, COLLECTION_ID = setup

        params = {
            "model": MODEL_ID,
            "messages": [{"role": "user", "content": "Qui est Albert ?"}],
            "stream": False,
            "n": 1,
            "max_tokens": 10,
            "search": True,
            "search_args": {"collections": [COLLECTION_ID], "k": 3, "method": "semantic"},
        }
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__CHAT_COMPLETIONS}", json=params)

        assert response.status_code == 200, response.text

        response_json = response.json()
        ChatCompletion(**response_json)  # test output format
        assert response_json["search_results"][0]["chunk"]["metadata"]["document_id"] in DOCUMENT_IDS

    def test_chat_completions_search_multi_agents(self, client: TestClient, setup):
        """Test the GET /chat/completions search unstreamed response."""
        MODEL_ID, DOCUMENT_IDS, COLLECTION_ID = setup

        params = {
            "model": MODEL_ID,
            "messages": [{"role": "user", "content": "Qui est Albert ?"}],
            "stream": False,
            "n": 1,
            "max_tokens": 10,
            "search": True,
            "search_args": {"collections": [COLLECTION_ID], "k": 3, "method": "multiagent"},
        }
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__CHAT_COMPLETIONS}", json=params)

        assert response.status_code == 200, response.text

        response_json = response.json()
        ChatCompletion(**response_json)  # test output format
        assert response_json["search_results"][0]["chunk"]["metadata"]["document_id"] in DOCUMENT_IDS
        assert "choice" in response_json["search_results"][0]["chunk"]["metadata"]
        assert "choice_desc" in response_json["search_results"][0]["chunk"]["metadata"]

    def test_chat_completions_search_streamed_response(self, client: TestClient, setup):
        """Test the GET /chat/completions search streamed response."""
        MODEL_ID, DOCUMENT_IDS, COLLECTION_ID = setup
        params = {
            "model": MODEL_ID,
            "messages": [{"role": "user", "content": "Qui est Albert ?"}],
            "stream": True,
            "n": 1,
            "max_tokens": 10,
            "search": True,
            "search_args": {"collections": [COLLECTION_ID], "k": 3, "method": "semantic"},
        }
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__CHAT_COMPLETIONS}", json=params)
        assert response.status_code == 200, response.text

        i = 0
        chunks = list()
        for line in response.iter_lines():
            if line:
                line = line.lstrip("data: ")
                if line != "[DONE]":
                    chunk = json.loads(line)
                    chunk = ChatCompletionChunk(**chunk)
                    chunks.append(chunk)
                    continue
                # check that the last chunk has a search result
                assert chunks[i - 1].search_results[0].chunk.metadata["document_id"] in DOCUMENT_IDS
                break

    def test_chat_completions_search_no_args(self, client: TestClient, setup):
        """Test the GET /chat/completions search template not found."""
        MODEL_ID, DOCUMENT_IDS, COLLECTION_ID = setup
        params = {
            "model": MODEL_ID,
            "messages": [{"role": "user", "content": "Qui est Albert ?"}],
            "stream": False,
            "n": 1,
            "max_tokens": 10,
            "search": True,
        }
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__CHAT_COMPLETIONS}", json=params)
        assert response.status_code == 422, response.text

    def test_chat_completions_search_no_collections(self, client: TestClient, setup):
        """Test the GET /chat/completions search no collections."""
        MODEL_ID, DOCUMENT_IDS, COLLECTION_ID = setup
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
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__CHAT_COMPLETIONS}", json=params)
        assert response.status_code == 200, response.text

    def test_chat_completions_search_template(self, client: TestClient, setup):
        """Test the GET /chat/completions search template."""
        MODEL_ID, DOCUMENT_IDS, COLLECTION_ID = setup
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

        response = client.post_without_permissions(url=f"/v1{ENDPOINT__CHAT_COMPLETIONS}", json=params)
        assert response.status_code == 200, response.text

    def test_chat_completions_web_search(self, client: TestClient, setup):
        """Test the GET /chat/completions web search."""
        MODEL_ID, DOCUMENT_IDS, COLLECTION_ID = setup
        params = {
            "model": MODEL_ID,
            "messages": [{"role": "user", "content": "Qui est Ulrich Tan ?"}],
            "stream": False,
            "n": 1,
            "max_tokens": 10,
            "search": True,
            "search_args": {"k": 3, "method": "semantic", "web_search": True},
        }
        logging.info(params)
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__CHAT_COMPLETIONS}", json=params)
        assert response.status_code == 200, response.text

    def test_chat_completions_search_template_missing_placeholders(self, client: TestClient, setup):
        """Test the GET /chat/completions search template missing placeholders."""
        MODEL_ID, DOCUMENT_IDS, COLLECTION_ID = setup
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
                "template": "Ne réponds pas à la question {prompt}.",
            },
        }
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__CHAT_COMPLETIONS}", json=params)
        assert response.status_code == 422, response.text

    def test_chat_completions_search_wrong_collection(self, client: TestClient, setup):
        """Test the GET /chat/completions search wrong collection."""
        MODEL_ID, DOCUMENT_IDS, COLLECTION_ID = setup
        params = {
            "model": MODEL_ID,
            "messages": [{"role": "user", "content": "Qui est Albert ?"}],
            "stream": False,
            "n": 1,
            "max_tokens": 10,
            "search": True,
            "search_args": {"collections": [120], "k": 3, "method": "semantic"},
        }
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__CHAT_COMPLETIONS}", json=params)
        assert response.status_code == 404, response.text

    def test_chat_completions_usage(self, client: TestClient, setup, tokenizer):
        """Test the GET /chat/completions usage."""
        MODEL_ID, DOCUMENT_IDS, COLLECTION_ID = setup
        prompt = "Hi, write a story."
        params = {
            "model": MODEL_ID,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 10,
        }

        prompt_tokens = len(tokenizer.encode(prompt))
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__CHAT_COMPLETIONS}", json=params)
        assert response.status_code == 200, response.text

        response_json = response.json()

        assert response_json.get("usage") is not None, response.text
        assert response_json["usage"].get("prompt_tokens") is not None, response.text
        assert response_json["usage"]["prompt_tokens"] == prompt_tokens

        assert response_json["usage"].get("completion_tokens") is not None, response.text

        contents = [choice.get("message", {}).get("content", "") for choice in response_json.get("choices", [])]
        completion_tokens = sum([len(tokenizer.encode(content)) for content in contents])
        assert response_json["usage"]["completion_tokens"] == completion_tokens

        assert response_json["usage"].get("total_tokens") is not None, response.text
        assert response_json["usage"]["total_tokens"] == prompt_tokens + completion_tokens
