from functools import partial
import time
from typing import Dict, List, Literal

from openai import OpenAI, AsyncOpenAI
import requests

from app.schemas.config import Config
from app.schemas.embeddings import Embeddings
from app.schemas.models import Model, Models
from app.utils.config import logger, DEFAULT_INTERNET_EMBEDDINGS_MODEL_URL, DEFAULT_INTERNET_LANGUAGE_MODEL_URL
from app.utils.exceptions import ContextLengthExceededException, ModelNotAvailableException, ModelNotFoundException
from app.utils.variables import EMBEDDINGS_MODEL_TYPE, LANGUAGE_MODEL_TYPE, AUDIO_MODEL_TYPE


def get_models_list(self, *args, **kwargs):
    """
    Custom method to overwrite OpenAI's list method (client.models.list()). This method support
    embeddings API models deployed with HuggingFace Text Embeddings Inference (see: https://github.com/huggingface/text-embeddings-inference).
    """
    headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else None
    data = list()

    try:
        if self.type == LANGUAGE_MODEL_TYPE:
            endpoint = f"{self.base_url}models"
            response = requests.get(url=endpoint, headers=headers, timeout=self.DEFAULT_TIMEOUT).json()

            # Multiple models from one vLLM provider are not supported for now
            assert len(response["data"]) == 1, "Only one model per model API is supported."

            response = response["data"][0]

            self.id = response["id"]
            self.owned_by = response.get("owned_by", "")
            self.created = response.get("created", round(time.time()))
            self.max_context_length = response.get("max_model_len", None)

        elif self.type == EMBEDDINGS_MODEL_TYPE:
            endpoint = str(self.base_url).replace("/v1/", "/info")
            response = requests.get(url=endpoint, headers=headers, timeout=self.DEFAULT_TIMEOUT).json()

            self.id = response["model_id"]
            self.owned_by = "huggingface-text-embeddings-inference"
            self.created = round(time.time())
            self.max_context_length = response.get("max_input_length", None)

        elif self.type == AUDIO_MODEL_TYPE:
            endpoint = f"{self.base_url}models/Systran/faster-whisper-large-v3"
            response = requests.get(url=endpoint, headers=headers, timeout=self.DEFAULT_TIMEOUT).json()

            self.id = response["id"]
            self.owned_by = response.get("owned_by", "")
            self.created = response.get("created", round(time.time()))
            self.max_context_length = None

        self.status = "available"

    except Exception:
        self.status = "unavailable"

    data = Model(
        id=self.id,
        object="model",
        owned_by=self.owned_by,
        created=self.created,
        max_context_length=self.max_context_length,
        type=self.type,
        status=self.status,
    )

    return Models(data=[data])


def check_context_length(self, messages: List[Dict[str, str]], add_special_tokens: bool = True):
    # TODO: remove this methode and use better context length handling
    headers = {"Authorization": f"Bearer {self.api_key}"}
    prompt = "\n".join([message["role"] + ": " + message["content"] for message in messages])

    if self.type == LANGUAGE_MODEL_TYPE:
        data = {"model": self.id, "prompt": prompt, "add_special_tokens": add_special_tokens}
    elif self.type == EMBEDDINGS_MODEL_TYPE:
        data = {"inputs": prompt, "add_special_tokens": add_special_tokens}

    response = requests.post(str(self.base_url).replace("/v1/", "/tokenize"), json=data, headers=headers)
    response.raise_for_status()
    response = response.json()

    if self.type == LANGUAGE_MODEL_TYPE:
        return response["count"] <= self.max_context_length
    elif self.type == EMBEDDINGS_MODEL_TYPE:
        return len(response[0]) <= self.max_context_length


def create_embeddings(self, *args, **kwargs):
    try:
        url = f"{self.base_url}embeddings"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        response = requests.post(url=url, headers=headers, json=kwargs)
        response.raise_for_status()
        data = response.json()
        return Embeddings(**data)
    except Exception as e:
        if "`inputs` must have less than" in e.response.text:
            raise ContextLengthExceededException()
        raise e


class ModelClient(OpenAI):
    DEFAULT_TIMEOUT = 60

    def __init__(self, type=Literal[EMBEDDINGS_MODEL_TYPE, LANGUAGE_MODEL_TYPE], *args, **kwargs):
        """
        ModelClient class extends OpenAI class to support custom methods.
        """
        super().__init__(timeout=self.DEFAULT_TIMEOUT, *args, **kwargs)
        self.type = type

        # set attributes for unavailable models
        self.id = ""
        self.owned_by = ""
        self.created = round(time.time())
        self.max_context_length = None

        # set real attributes if model is available
        self.models.list = partial(get_models_list, self)
        response = self.models.list()

        if self.type == EMBEDDINGS_MODEL_TYPE:
            response = self.embeddings.create(model=self.id, input="hello world")
            self.vector_size = len(response.data[0].embedding)
            self.embeddings.create = partial(create_embeddings, self)

        self.check_context_length = partial(check_context_length, self)


# TODO merge with ModelClient for all models and adapt endpoint to not use anymore the httpx async client
class AsyncModelClient(AsyncOpenAI):
    DEFAULT_TIMEOUT = 10

    def __init__(self, type=Literal[AUDIO_MODEL_TYPE], *args, **kwargs):
        """
        AsyncModelClient class extends AsyncOpenAI class to support custom methods.
        """
        timeout = 60 if type == AUDIO_MODEL_TYPE else self.DEFAULT_TIMEOUT
        super().__init__(timeout=timeout, *args, **kwargs)
        self.type = type

        # set attributes for unavailable models
        self.id = ""
        self.owned_by = ""
        self.created = round(time.time())
        self.max_context_length = None

        # set real attributes if model is available
        self.models.list = partial(get_models_list, self)
        response = self.models.list()

        if self.type == EMBEDDINGS_MODEL_TYPE:
            response = self.embeddings.create(model=self.id, input="hello world")
            self.vector_size = len(response.data[0].embedding)
            self.embeddings.create = partial(create_embeddings, self)

        self.check_context_length = partial(check_context_length, self)


class ModelClients(dict):
    """
    Overwrite __getitem__ method to raise a 404 error if model is not found.
    """

    def __init__(self, config: Config):
        for model_config in config.models:
            model_client_class = ModelClient if model_config.type != AUDIO_MODEL_TYPE else AsyncModelClient
            model = model_client_class(base_url=model_config.url, api_key=model_config.key, type=model_config.type)
            if model.status == "unavailable":
                logger.error(f"unavailable model API on {model_config.url}, skipping.")
                continue
            self.__setitem__(model.id, model)

            if model_config.url == DEFAULT_INTERNET_EMBEDDINGS_MODEL_URL:
                self.DEFAULT_INTERNET_EMBEDDINGS_MODEL_ID = model.id
            elif model_config.url == DEFAULT_INTERNET_LANGUAGE_MODEL_URL:
                self.DEFAULT_INTERNET_LANGUAGE_MODEL_ID = model.id

        assert "DEFAULT_INTERNET_EMBEDDINGS_MODEL_ID" in self.__dict__, "Default internet embeddings model is unavailable."
        assert "DEFAULT_INTERNET_LANGUAGE_MODEL_ID" in self.__dict__, "Default internet language model is unavailable."

    def __setitem__(self, key: str, value):
        if any(key == k for k in self.keys()):
            raise KeyError(f"Model id {key} is duplicated, not allowed.")
        super().__setitem__(key, value)

    def __getitem__(self, key: str):
        try:
            item = super().__getitem__(key)
            assert item.status == "available", "Model not available."
            return item
        except KeyError:
            raise ModelNotFoundException()
        except AssertionError as e:
            raise ModelNotAvailableException()
