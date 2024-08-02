import urllib
from typing import Union, Optional

from fastapi import APIRouter, Security

from app.schemas.models import Model, ModelResponse
from app.utils.lifespan import clients
from app.utils.security import check_api_key


router = APIRouter()


@router.get("/models/{model}")
@router.get("/models")
async def models(
    model: Optional[str] = None, api_key: str = Security(check_api_key)
) -> Union[ModelResponse, Model]:
    """
    Model API similar to OpenAI's API.
    See https://platform.openai.com/docs/api-reference/models/list for the API specification.
    """
    if model is not None:
        # support double encoding
        unquote_model = urllib.parse.unquote(urllib.parse.unquote(model))
        client = clients["models"][unquote_model]
        response = dict([row for row in client.models.list().data if row.id == unquote_model][0])
        response = Model(**response)
    else:
        base_urls = list()
        response = {"object": "list", "data": []}
        for model_id, client in clients["models"].items():
            if client.base_url not in base_urls:
                base_urls.append(str(client.base_url))
                for row in client.models.list().data:
                    response["data"].append(dict(row))
        response = ModelResponse(**response)

    return response
