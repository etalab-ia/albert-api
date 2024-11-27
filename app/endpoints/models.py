from typing import Optional, Union

from fastapi import APIRouter, Request, Security

from app.utils.settings import settings
from app.schemas.models import Model, Models
from app.schemas.security import User
from app.utils.lifespan import clients, limiter
from app.utils.security import check_api_key, check_rate_limit

router = APIRouter()


@router.get("/models/{model:path}")
@router.get("/models")
@limiter.limit(settings.default_rate_limit, key_func=lambda request: check_rate_limit(request=request))
async def models(request: Request, model: Optional[str] = None, user: User = Security(check_api_key)) -> Union[Models, Model]:
    """
    Model API similar to OpenAI's API.
    See https://platform.openai.com/docs/api-reference/models/list for the API specification.
    """
    if model is not None:
        client = clients.models[model]
        response = [row for row in client.models.list().data if row.id == model][0]
    else:
        response = {"object": "list", "data": []}
        for model_id, client in clients.models.items():
            for row in client.models.list().data:
                row = dict(row)
                row["type"] = client.type
                response["data"].append(dict(row))
        response = Models(**response)

    return response
