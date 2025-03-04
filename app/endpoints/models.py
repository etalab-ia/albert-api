from typing import Union

from fastapi import APIRouter, Path, Request, Security

from app.helpers import RateLimit
from app.schemas.models import Model, Models
from app.schemas.security import User
from app.utils.lifespan import models

router = APIRouter()


@router.get(path="/models/{model:path}")
async def get_model(request: Request, model: str = Path(description="The name of the model to get."), user: User = Security(RateLimit())) -> Model:
    """
    Get a model by name.
    """

    response = models.registry.list(model=model)[0]

    return response


@router.get(path="/models")
async def get_models(request: Request, user: User = Security(RateLimit())) -> Union[Models, Model]:
    """
    Lists the currently available models, and provides basic informations.
    """

    data = models.registry.list()

    return Models(data=data)
