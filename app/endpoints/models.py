from typing import Union

from fastapi import APIRouter, Path, Request, Security

from app.utils.exceptions import ModelNotFoundException
from app.helpers import RateLimit
from app.schemas.models import Model, Models
from app.schemas.users import AuthenticatedUser
from app.utils.lifespan import context

router = APIRouter()


@router.get(path="/models/{model:path}")
async def get_model(
    request: Request, model: str = Path(description="The name of the model to get."), user: AuthenticatedUser = Security(dependency=RateLimit())
) -> Model:
    """
    Get a model by name.
    """

    response = context.models.list(model=model, user=user)
    if len(response) == 0:
        raise ModelNotFoundException()

    return response[0]


@router.get(path="/models")
async def get_models(request: Request, user: AuthenticatedUser = Security(dependency=RateLimit())) -> Union[Models, Model]:
    """
    Lists the currently available models, and provides basic informations.
    """

    data = context.models.list(user=user)

    return Models(data=data)
