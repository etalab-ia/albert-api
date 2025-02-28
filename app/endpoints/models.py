from typing import Optional, Union

from fastapi import APIRouter, Request, Security

from app.schemas.models import Model, Models
from app.schemas.security import User
from app.utils.lifespan import models
from app.utils.security import check_api_key

router = APIRouter()


@router.get(path="/models/{model:path}")
@router.get(path="/models")
async def get_models(request: Request, model: Optional[str] = None, user: User = Security(check_api_key)) -> Union[Models, Model]:
    """
    Lists the currently available models, and provides basic informations.
    """

    data = models.registry.list(model=model)
    response = data[0] if model else Models(data=data)

    return response
