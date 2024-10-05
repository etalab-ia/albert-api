from functools import partial
import time
from typing import Dict, List, Literal

from openai import OpenAI
import requests

from app.schemas.embeddings import Embeddings
from app.schemas.models import Model, Models
from app.utils.variables import EMBEDDINGS_MODEL_TYPE, LANGUAGE_MODEL_TYPE


def get_models_list(self, *args, **kwargs):
    """
    Custom method to overwrite OpenAI's list method (client.models.list()). This method support
    embeddings API models deployed with HuggingFace Text Embeddings Inference (see: https://github.com/huggingface/text-embeddings-inference).
    """
    headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else None
    data = list()

    if self.type == LANGUAGE_MODEL_TYPE:
        endpoint = f"{self.base_url}models"
        response = requests.get(url=endpoint, headers=headers, timeout=self.DEFAULT_TIMEOUT).json()
        assert len(response["data"]) == 1, "Only one model per model API is supported."
        response = response["data"][0]
        data.append(
            Model(
                id=response["id"],
                object="model",
                owned_by=response.get("owned_by", ""),
                created=response.get("created", round(time.time())),
                max_model_len=response.get("max_model_len", None),
                type=LANGUAGE_MODEL_TYPE,
            )
        )

    elif self.type == EMBEDDINGS_MODEL_TYPE:
        endpoint = str(self.base_url).replace("/v1/", "/info")
        response = requests.get(url=endpoint, headers=headers, timeout=self.DEFAULT_TIMEOUT).json()
        data.append(
            Model(
                id=response["model_id"],
                object="model",
                owned_by="huggingface-text-embeddings-inference",
                max_model_len=response.get("max_input_length", None),
                created=round(time.time()),
                type=EMBEDDINGS_MODEL_TYPE,
            )
        )

    return Models(data=data)


def check_context_length(self, model: str, messages: List[Dict[str, str]], add_special_tokens: bool = True):
    headers = {"Authorization": f"Bearer {self.api_key}"}
    prompt = "\n".join([message["role"] + ": " + message["content"] for message in messages])
    data = {"model": model, "prompt": prompt, "add_special_tokens": add_special_tokens}

    response = requests.post(str(self.base_url).replace("/v1/", "/tokenize"), json=data, headers=headers)
    response.raise_for_status()
    return response.json()["count"] <= response.json()["max_model_len"]


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
            raise AssertionError("Max input length exceeded.")
        raise e


class ModelClient(OpenAI):
    DEFAULT_TIMEOUT = 10

    def __init__(self, type=Literal[EMBEDDINGS_MODEL_TYPE, LANGUAGE_MODEL_TYPE], search_internet: bool = False, *args, **kwargs):
        """
        ModelClient class extends OpenAI class to support custom methods.
        """
        super().__init__(timeout=self.DEFAULT_TIMEOUT, *args, **kwargs)
        self.type = type
        self.search_internet = search_internet
        self.models.list = partial(get_models_list, self)
        response = self.models.list()
        assert len(response.data) == 1, "Only one model is allowed per client is allowed."
        model = response.data[0]
        self.id = model.id

        if self.type == EMBEDDINGS_MODEL_TYPE:
            response = self.embeddings.create(model=self.id, input="hello world")
            self.vector_size = len(response.data[0].embedding)
            self.embeddings.create = partial(create_embeddings, self)

        # @ TODO : extends to embeddings models
        if self.type == LANGUAGE_MODEL_TYPE:
            self.check_context_length = partial(check_context_length, self)
