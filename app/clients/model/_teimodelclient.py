from functools import partial
import time
from urllib.parse import urljoin

from openai import AsyncOpenAI
import requests

from app.clients.model._basemodelclient import BaseModelClient
from app.helpers.rerank import TEIRerank
from app.schemas.models import Model, Models
from app.schemas.settings import ModelClient as ModelClientSettings


class TeiModelClient(AsyncOpenAI, BaseModelClient):
    ENDPOINT_TABLE = {
        "audio/transcriptions": None,
        "chat/completions": None,
        "embeddings": "v1/embeddings",
        "models": "info",
        "rerank": "rerank",
    }

    def __init__(self, settings: ModelClientSettings, *args, **kwargs) -> None:
        """
        ModelClient class extends OpenAI class to support custom methods.
        """
        super().__init__(**settings.args.model_dump())

        # overwrite OpenAI methods
        self.models.list = partial(_get_models_list, self)
        self.rerank = TEIRerank(client=self)

        self.model = settings.model
        self.max_context_length = self.models.list().data[0].max_context_length


########### Overwrite OpenAI methods ############


def _get_models_list(self, *args, **kwargs) -> Models:
    """
    Custom method to overwrite OpenAI's list method (self.models.list()) and make it synchronous for initialization.
    """
    endpoint = urljoin(base=str(self.base_url), url="info")
    headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else None

    response = requests.get(url=endpoint, headers=headers, timeout=self.timeout)
    assert response.status_code == 200, f"Failed to get models list ({response.status_code})."

    response = response.json()
    assert self.model == response["model_id"], f"Model not found ({self.model})."

    data = Model(
        id=self.model,
        created=response.get("created", round(time.time())),
        owned_by=response.get("owned_by", ""),
        max_context_length=response.get("max_input_length"),
    )

    return Models(data=[data])
