from typing import Union

from fastapi import APIRouter, Path, Request, Security

from app.helpers import Authorization
from app.schemas.models import Model, Models
from app.utils.lifespan import context

router = APIRouter()


@router.get(path="/models/{model:path}", dependencies=[Security(dependency=Authorization())])
async def get_model(request: Request, model: str = Path(description="The name of the model to get.")) -> Model:
    """
    Get a model by name and provide basic informations.
    """

    model = context.models.list(model=model)[0]

    return model


@router.get(path="/models")
async def get_models(request: Request, user: str = Security(dependency=Authorization())) -> Union[Models, Model]:
    """
    Lists the currently available models and provides basic informations.
    """

    data = context.models.list()

    return Models(data=data)
