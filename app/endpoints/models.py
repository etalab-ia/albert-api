import urllib
from typing import Union, Optional

from fastapi import APIRouter, Security

from app.schemas.models import Model, Models
from app.utils.lifespan import clients
from app.utils.security import check_api_key


router = APIRouter()

@router.get("/models/{model}")
@router.get("/models")
async def models(
    model: Optional[str] = None, user: str = Security(check_api_key)
) -> Union[Models, Model]:
    """
    Model API similar to OpenAI's API.
    See https://platform.openai.com/docs/api-reference/models/list for the API specification.
    """
    if model is not None:
        # support double encoding
        unquote_model = urllib.parse.unquote(urllib.parse.unquote(model))
        client = clients["models"][unquote_model]
        response = [row for row in client.models.list().data if row.id == unquote_model][0]
    else:
        response = {"object": "list", "data": []}
        for model_id, client in clients["models"].items():
            for row in client.models.list().data:
                row = dict(row)
                row["type"] = client.type
                response["data"].append(dict(row))
        response = Models(**response)

    return response
