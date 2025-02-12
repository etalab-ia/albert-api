from typing import Optional, Union

from fastapi import APIRouter, Request, Security

from app.schemas.models import Model, Models
from app.schemas.security import User
from app.utils.lifespan import clients
from app.utils.security import check_api_key

router = APIRouter()


@router.get(path="/models/{model:path}")
@router.get(path="/models")
async def models(request: Request, model: Optional[str] = None, user: User = Security(check_api_key)) -> Union[Models, Model]:
    """
    Model API similar to OpenAI's API.
    See https://platform.openai.com/docs/api-reference/models/list for the API specification.
    """

    data = clients.models.list(model=model)
    response = data[0] if model else Models(data=data)

    return response
