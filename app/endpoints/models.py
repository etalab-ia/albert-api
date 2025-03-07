from typing import Union

from fastapi import APIRouter, Path, Request, Security

from app.helpers import Authorization
from app.schemas.core.auth import AuthenticatedUser
from app.schemas.models import Model, Models
from app.utils.exceptions import ModelNotFoundException
from app.utils.lifespan import context

router = APIRouter()


@router.get(path="/models/{model:path}")
async def get_model(
    request: Request,
    model: str = Path(description="The name of the model to get."),
    user: AuthenticatedUser = Security(dependency=Authorization()),
) -> Model:
    """
    Get a model by name and provide basic informations.
    """

    data = context.models.list(model=model)
    if len(data) == 0:
        raise ModelNotFoundException()

    model = data[0]
    if user.limits[model.id].rpd == 0 or user.limits[model.id].rpd == 0:
        raise ModelNotFoundException()

    return model


@router.get(path="/models")
async def get_models(request: Request, user: AuthenticatedUser = Security(dependency=Authorization())) -> Union[Models, Model]:
    """
    Lists the currently available models and provides basic informations.
    """

    data = context.models.list()
    for i, model in enumerate(data):
        if user.limits[model.id].rpd == 0 or user.limits[model.id].rpd == 0:
            data.pop(i)

    return Models(data=data)
