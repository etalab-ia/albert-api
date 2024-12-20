from functools import partial
import json
import time
from typing import Any, List, Literal

from fastapi import HTTPException
from openai import OpenAI
import requests

from app.schemas.embeddings import Embeddings
from app.schemas.chat import ChatCompletion
from app.schemas.models import Model, Models
from app.schemas.rerank import Rerank
from app.schemas.settings import Settings
from app.utils.exceptions import ModelNotAvailableException, ModelNotFoundException
from app.utils.logging import logger
from app.utils.variables import AUDIO_MODEL_TYPE, DEFAULT_TIMEOUT, EMBEDDINGS_MODEL_TYPE, LANGUAGE_MODEL_TYPE, RERANK_MODEL_TYPE


def get_models_list(self, *args, **kwargs) -> Models:
    """
    Custom method to overwrite OpenAI's list method (client.models.list()). This method support
    embeddings API models deployed with HuggingFace Text Embeddings Inference (see: https://github.com/huggingface/text-embeddings-inference).
    """
    headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else None
    data = list()

    try:
        if self.type == LANGUAGE_MODEL_TYPE:
            endpoint = f"{self.base_url}models"
            response = requests.get(url=endpoint, headers=headers, timeout=DEFAULT_TIMEOUT).json()

            # Multiple models from one vLLM provider are not supported for now
            assert len(response["data"]) == 1, "Only one model per model API is supported."

            response = response["data"][0]

            self.id = response["id"]
            self.owned_by = response.get("owned_by", "")
            self.created = response.get("created", round(time.time()))
            self.max_context_length = response.get("max_model_len", None)

        elif self.type == EMBEDDINGS_MODEL_TYPE or self.type == RERANK_MODEL_TYPE:
            endpoint = str(self.base_url).replace("/v1/", "/info")
            response = requests.get(url=endpoint, headers=headers, timeout=DEFAULT_TIMEOUT).json()

            self.id = response["model_id"]
            self.owned_by = "huggingface-text-embeddings-inference"
            self.created = round(time.time())
            self.max_context_length = response.get("max_input_length", None)

        elif self.type == AUDIO_MODEL_TYPE:
            endpoint = f"{self.base_url}models"
            response = requests.get(url=endpoint, headers=headers, timeout=DEFAULT_TIMEOUT).json()
            response = response["data"][0]

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
        aliases=self.aliases,
        type=self.type,
        status=self.status,
    )

    return Models(data=[data])


def create_chat_completions(self, *args, **kwargs):
    """
    Custom method to overwrite OpenAI's create method to raise HTTPException from model API.
    """
    try:
        url = f"{self.base_url}chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        response = requests.post(url=url, headers=headers, json=kwargs)
        response.raise_for_status()
        data = response.json()

        return ChatCompletion(**data)

    except Exception as e:
        raise HTTPException(status_code=e.response.status_code, detail=json.loads(e.response.text)["message"])


# @TODO : useless ?
def create_embeddings(self, *args, **kwargs):
    """
    Custom method to overwrite OpenAI's create method to raise HTTPException from model API.
    """
    try:
        url = f"{self.base_url}embeddings"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        response = requests.post(url=url, headers=headers, json=kwargs)
        response.raise_for_status()
        data = response.json()

        return Embeddings(**data)

    except Exception as e:
        raise HTTPException(status_code=e.response.status_code, detail=json.loads(e.response.text)["message"])


class ModelClient(OpenAI):
    DEFAULT_TIMEOUT = 120

    def __init__(self, type=Literal[EMBEDDINGS_MODEL_TYPE, LANGUAGE_MODEL_TYPE, AUDIO_MODEL_TYPE, RERANK_MODEL_TYPE], *args, **kwargs) -> None:
        """
        ModelClient class extends AsyncOpenAI class to support custom methods.
        """
        super().__init__(timeout=DEFAULT_TIMEOUT, *args, **kwargs)
        self.type = type

        # set attributes for unavailable models
        self.id = ""
        self.owned_by = ""
        self.aliases = []
        self.created = round(number=time.time())
        self.max_context_length = None

        # set real attributes if model is available
        self.models.list = partial(get_models_list, self)
        response = self.models.list()

        if self.type == LANGUAGE_MODEL_TYPE:
            self.chat.completions.create = partial(create_chat_completions, self)

        if self.type == EMBEDDINGS_MODEL_TYPE:
            response = self.embeddings.create(model=self.id, input="hello world")
            self.vector_size = len(response.data[0].embedding)
            self.embeddings.create = partial(create_embeddings, self)

        if self.type == RERANK_MODEL_TYPE:

            class RerankClient(OpenAI):
                def __init__(self, model: str, *args, **kwargs) -> None:
                    super().__init__(*args, **kwargs)
                    self.model = model

                def create(self, prompt: str, input: list[str], model: str) -> List[Rerank]:
                    assert self.model == model, "Model not found."
                    json = {"query": prompt, "texts": input}
                    url = f"{str(self.base_url).replace("/v1/", "/rerank")}"
                    headers = {"Authorization": f"Bearer {self.api_key}"}

                    response = requests.post(url=url, headers=headers, json=json, timeout=self.timeout)
                    response.raise_for_status()
                    data = response.json()
                    data = [Rerank(**item) for item in data]

                    return data

            self.rerank = RerankClient(model=self.id, base_url=self.base_url, api_key=self.api_key, timeout=self.DEFAULT_TIMEOUT)


class ModelClients(dict):
    """
    Overwrite __getitem__ method to raise a 404 error if model is not found.
    """

    def __init__(self, settings: Settings) -> None:
        self.aliases = {alias: model_id for model_id, aliases in settings.models.aliases.items() for alias in aliases}

        for model_settings in settings.clients.models:
            model = ModelClient(
                base_url=model_settings.url,
                api_key=model_settings.key,
                type=model_settings.type,
            )
            if model.status == "unavailable":
                logger.error(msg=f"unavailable model API on {model_settings.url}, skipping.")
                continue
            try:
                logger.info(msg=f"Adding model API {model_settings.url} to the client...")
                self.__setitem__(key=model.id, value=model)
                logger.info(msg="done.")
            except Exception as e:
                logger.error(msg=e)

            model.aliases = settings.models.aliases.get(model.id, [])

        for alias in self.aliases.keys():
            assert alias not in self.keys(), "Alias is already used by another model."

        assert settings.internet.default_language_model in self.keys(), "Default internet language model not found."
        assert settings.internet.default_embeddings_model in self.keys(), "Default internet embeddings model not found."

    def __setitem__(self, key: str, value) -> None:
        if key in self.keys():
            raise ValueError(f"duplicated model ID {key}, skipping.")
        else:
            super().__setitem__(key, value)

    def __getitem__(self, key: str) -> Any:
        key = self.aliases.get(key, key)
        try:
            item = super().__getitem__(key)
            assert item.status == "available", "Model not available."
            return item
        except KeyError:
            raise ModelNotFoundException()
        except AssertionError as e:
            raise ModelNotAvailableException()
